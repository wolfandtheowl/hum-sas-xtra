#!/usr/bin/env python3
"""
extract_partners.py
===================

Extract the "Partners details" section of Arts Council England National Lottery
Project Grants (NLPG) application PDFs into one CSV per PDF.

Usage
-----
    python3 extract_partners.py                      # all PDFs in ./data -> ./exports
    python3 extract_partners.py data/some.pdf        # one PDF
    python3 extract_partners.py --data DIR --out DIR # custom folders
    python3 extract_partners.py --dump               # also write the cleaned text to exports/_debug/
    python3 extract_partners.py --no-archive         # leave PDFs in ./data
    python3 extract_partners.py --redo               # also reprocess ./data/processed/

Already-processed PDFs
----------------------
A PDF that extracts cleanly is moved to `<data>/processed/` afterwards, so the
next plain run only picks up new drops in `<data>`.  A PDF that raised any
warning is left in place for a human to look at.  `--no-archive` disables the
move; `--redo` re-runs everything, including what is already in `processed/`.
Naming a PDF explicitly on the command line always processes it, wherever it
lives.

Requirements
------------
* Python 3.9+ (standard library only)
* `pdftotext` from poppler: on the PATH, or unzipped into ./vendor/poppler/
  (macOS: `brew install poppler`)  -- see README.md

How it works (see plan/01_approach.md for the long version)
----------------------------------------------------------
1. `pdftotext -layout` turns the PDF into text, one page per form-feed.
2. Each page's running header ("Applicant: ..." / "Project: ..." + wrapped
   lines) and footer ("Application submission   Page N   dd/mm/yyyy") are
   stripped so that partner blocks split across pages become contiguous.
3. The project name is read from the page-1 header, ignoring the
   right-justified NLPG reference.  Applicant name / type come from the
   "Applicant details" page; the project start date from the "Your project"
   page.
4. The partner list is parsed from the first "Partners details" heading
   onwards.  Every block is a run of labelled fields
   (Name / Main contact / Email address / Role in project / Confirmed or
   expected).  Unlabelled lines are continuations of the previous field.
   The "Up to 2000 characters" hint that older PDF versions print beside the
   Role text is removed.
5. Sanity checks run on every file (block count == "Confirmed or expected"
   count, every block has a Name, etc.) and are printed to the console.
6. A clean PDF is archived into `<data>/processed/`; one that warned stays put.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

CSV_HEADER = ["Bid", "Name", "Rep (if org)", "Email", "Role/Bio", "Type", "Art Form", "Sector"]

# Field labels exactly as pdftotext renders them in the "Partners details" blocks.
FIELD_LABELS = {
    "Name": "name",
    "Main contact (if organisation)": "contact",
    "Email address": "email",
    "Role in project": "role",
    "Confirmed or expected": "confirmed",
}
FIELD_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(k) for k in FIELD_LABELS) + r"):\s?(.*)$"
)

PARTNERS_HEADING_RE = re.compile(r"^\s*Partners details\s*$")
FOOTER_RE = re.compile(r"^\s*Application submission\s+Page\s+\d+\s+\d{2}/\d{2}/\d{4}\s*$")
CHAR_HINT_RE = re.compile(r"^\s*Up to \d[\d,]* characters\s?")
NLPG_RE = re.compile(r"\bNLPG-\S*")
START_DATE_RE = re.compile(r"^\s*Project start date:\s*(\d{2})/(\d{2})/(\d{4})\s*$")
APPLICANT_NAME_RE = re.compile(r"^\s*Applicant name:\s*(.+?)\s*$")
APPLICANT_TYPE_RE = re.compile(r"^\s*Applicant type:\s*(.+?)\s*$")

# Words we don't want a truncated project title to end on.
TRAILING_STOPWORDS = {
    "a", "an", "and", "&", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "with", "-", "–", "—", "/",
}
MAX_TITLE_WORDS_BEFORE_TRIM = 10   # "more than 10 words" -> trim
TRIMMED_TITLE_WORDS = 8            # "... cut it down to 8 max"


# ----------------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------------

@dataclass
class Partner:
    name: str = ""
    contact: str = ""
    email: str = ""
    role: str = ""
    confirmed: str = ""
    # Which fields were present as labels (used by sanity checks).
    seen: set = field(default_factory=set)


@dataclass
class Meta:
    project_title_full: str
    project_title: str          # possibly truncated for the CSV "Bid" column
    applicant_name: str
    applicant_type: str
    start_year: str
    start_month: str
    n_pages: int
    header_mismatch_pages: list


# ----------------------------------------------------------------------------
# Step 1 - PDF -> text
# ----------------------------------------------------------------------------

# Poppler may be vendored inside this repo (vendor/poppler/...), which keeps a
# Windows install self-contained instead of littering C:\. Any bin directory
# below vendor/poppler is searched, so the layout of the unzipped release does
# not matter.
VENDOR_DIR = Path(__file__).resolve().parent / "vendor" / "poppler"

PDFTOTEXT_MISSING_MSG = """\
ERROR: `pdftotext` was not found.

This program cannot read PDFs without it. Install Poppler, then re-run.

  Windows (Git Bash)
      Keep it inside this project - nothing is installed system-wide:
        1. Download "Release-xx.xx.x-0.zip" from
           https://github.com/oschwartz10612/poppler-windows/releases
        2. Unzip it into:  {vendor}
           so that a "bin" folder containing pdftotext.exe sits somewhere below.
        3. Re-run this program. It finds it automatically - no PATH editing.

  macOS          : brew install poppler
  Debian/Ubuntu  : sudo apt install poppler-utils

Check a system-wide install with:  pdftotext -v
"""


def find_pdftotext() -> str | None:
    """
    Locate the `pdftotext` binary.

    A copy vendored inside this repo wins over a system-wide one, so a machine
    without admin rights (or without Homebrew) can run entirely self-contained.
    """
    names = ("pdftotext.exe", "pdftotext")
    if VENDOR_DIR.is_dir():
        for name in names:
            # Any depth: vendor/poppler/bin, vendor/poppler/Library/bin, etc.
            for cand in sorted(VENDOR_DIR.rglob(name)):
                if cand.is_file():
                    return str(cand)
    return shutil.which("pdftotext")


def require_pdftotext() -> str:
    """Abort immediately unless a usable `pdftotext` binary is available."""
    exe = find_pdftotext()
    if exe is None:
        sys.exit(PDFTOTEXT_MISSING_MSG.format(vendor=VENDOR_DIR))
    try:
        subprocess.run([exe, "-v"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        sys.exit(PDFTOTEXT_MISSING_MSG.format(vendor=VENDOR_DIR))
    return exe


def pdf_to_pages(pdf: Path) -> list[list[str]]:
    """Return the PDF as a list of pages, each a list of lines (layout mode)."""
    exe = require_pdftotext()
    # Capture raw bytes and decode them ourselves. `text=True` would decode with
    # the OS default codec, which on Windows is cp1252 and cannot represent the
    # UTF-8 that `-enc UTF-8` produces (UnicodeDecodeError on any curly quote,
    # dash or accent). errors="replace" keeps one odd glyph from killing a run.
    result = subprocess.run(
        [exe, "-layout", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True, check=True,
    )
    text = result.stdout.decode("utf-8", errors="replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()  # pdftotext ends with a trailing form feed
    return [p.splitlines() for p in pages]


# ----------------------------------------------------------------------------
# Step 2 - strip running headers / footers
# ----------------------------------------------------------------------------

def split_header(page: list[str]) -> tuple[list[str], list[str]]:
    """
    Split a page into (header_lines, body_lines).

    The header is: a line starting with 'Applicant:', a line starting with
    'Project:', then any further non-blank lines (the wrapped project title
    and/or wrapped NLPG reference) up to the first blank line.
    """
    if not page or not page[0].lstrip().startswith("Applicant:"):
        return [], page
    i = 0
    while i < len(page) and page[i].strip():
        i += 1
    return page[:i], page[i:]


def strip_footer(body: list[str]) -> list[str]:
    for i, line in enumerate(body):
        if FOOTER_RE.match(line):
            return body[:i]
    return body


def clean_pages(pages: list[list[str]]) -> tuple[list[str], list[str], list[int]]:
    """
    Returns (page1_header, all_body_lines_concatenated, pages_whose_header_differs).
    """
    ref_header: list[str] | None = None
    mismatches: list[int] = []
    body_all: list[str] = []
    for n, page in enumerate(pages, start=1):
        header, body = split_header(page)
        if ref_header is None and header:
            ref_header = header
        elif header and [h.split() for h in header] != [h.split() for h in ref_header]:
            mismatches.append(n)
        body_all.extend(strip_footer(body))
    return ref_header or [], body_all, mismatches


# ----------------------------------------------------------------------------
# Step 3 - metadata (project title, applicant, start date)
# ----------------------------------------------------------------------------

def project_title_from_header(header: list[str]) -> str:
    """
    The header looks like one of:

        Project: Short title                                   NLPG-00553885
        Project: Longer title - words words words              NLPG-00613834-LON-UN-
                                                                     0000005654
        Project: Very long title that wraps onto the next line NLPG-00801163-V2-UN-20250630
        rest of the very long title, left-justified
        and more, left-justified

    Rule: take everything after 'Project:' with the NLPG token removed, then
    append continuation lines that are LEFT-justified (column 0).  Indented
    continuation lines belong to the right-justified NLPG reference.
    """
    parts: list[str] = []
    started = False
    for line in header:
        if not started:
            if line.lstrip().startswith("Project:"):
                started = True
                text = line.lstrip()[len("Project:"):]
                parts.append(NLPG_RE.sub("", text).strip())
            continue
        if line and not line[0].isspace():
            parts.append(NLPG_RE.sub("", line).strip())
        # indented continuation -> NLPG reference wrap -> ignore
    return " ".join(p for p in parts if p).strip()


def truncate_title(title: str) -> str:
    """Trim titles with more than 10 'real' words down to 8 words."""
    tokens = title.split()
    real = [t for t in tokens if re.search(r"[A-Za-z0-9]", t)]
    if len(real) <= MAX_TITLE_WORDS_BEFORE_TRIM:
        return title
    kept: list[str] = []
    count = 0
    for t in tokens:
        if re.search(r"[A-Za-z0-9]", t):
            if count == TRIMMED_TITLE_WORDS:
                break
            count += 1
        kept.append(t)
    # Don't end on a dangling connector / punctuation.
    while kept and (kept[-1].lower() in TRAILING_STOPWORDS or not re.search(r"[A-Za-z0-9]", kept[-1])):
        kept.pop()
    return " ".join(kept).rstrip(" ,;:-–—/")


def find_first(lines: list[str], regex: re.Pattern) -> re.Match | None:
    for line in lines:
        m = regex.match(line)
        if m:
            return m
    return None


def extract_meta(pdf: Path, header: list[str], body: list[str], n_pages: int, mismatches: list[int]) -> Meta:
    full = project_title_from_header(header)
    m_name = find_first(body, APPLICANT_NAME_RE)
    m_type = find_first(body, APPLICANT_TYPE_RE)
    m_date = find_first(body, START_DATE_RE)
    problems = []
    if not full:
        problems.append("project title not found in page header")
    if not m_name:
        problems.append("'Applicant name:' not found")
    if not m_date:
        problems.append("'Project start date:' not found")
    if problems:
        sys.exit(f"ERROR in {pdf.name}: " + "; ".join(problems))
    return Meta(
        project_title_full=full,
        project_title=truncate_title(full),
        applicant_name=m_name.group(1),
        applicant_type=(m_type.group(1) if m_type else "Unknown"),
        start_year=m_date.group(3),
        start_month=m_date.group(2),
        n_pages=n_pages,
        header_mismatch_pages=mismatches,
    )


# ----------------------------------------------------------------------------
# Step 4 - partners
# ----------------------------------------------------------------------------

def join_continuation(field_name: str, current: str, extra: str) -> str:
    """Join a wrapped line onto the field's existing text."""
    extra = extra.strip()
    if not extra:
        return current
    if not current:
        return extra
    if field_name == "email":
        return current + extra                       # emails never contain spaces
    if current.endswith("-") and not current.endswith(" -"):
        return current + extra                       # 'award-\nwinning' -> 'award-winning'
    return current + " " + extra


def parse_partners(body: list[str]) -> tuple[list[Partner], list[str]]:
    """
    Parse the 'Partners details' blocks.  Returns (partners, warnings).
    """
    warnings: list[str] = []
    partners: list[Partner] = []

    # Locate the first heading; everything before it is the rest of the form
    # (which also contains unrelated 'Name:' / 'Email address:' fields).
    try:
        start = next(i for i, l in enumerate(body) if PARTNERS_HEADING_RE.match(l))
    except StopIteration:
        return [], ["no 'Partners details' heading found"]

    current: Partner | None = None
    current_field: str | None = None
    in_section = True

    for line in body[start:]:
        if not in_section:
            break
        if PARTNERS_HEADING_RE.match(line):
            # A heading always starts a new block.  (The heading may sit at the
            # bottom of one page with the fields on the next; that is fine
            # because page headers/footers are already gone.)
            current = Partner()
            partners.append(current)
            current_field = None
            continue
        if not line.strip():
            continue
        if current is None:
            continue

        m = FIELD_RE.match(line)
        if m:
            label, value = FIELD_LABELS[m.group(1)], m.group(2).strip()
            if label in current.seen:
                # Same label twice inside one block: the applicant typed the
                # label text into the value (seen in the wild).  Treat as a
                # continuation of the current field.
                setattr(current, current_field, join_continuation(current_field, getattr(current, current_field), line.strip()))
                continue
            current.seen.add(label)
            current_field = label
            # Applicant literally typed "Role in project:" at the start of the value.
            if label == "role":
                value = re.sub(r"^Role in project:\s*", "", value)
            setattr(current, label, value)
            if label == "confirmed":
                # Last field of a block.  If the next non-blank line is not a
                # new heading, the section has ended.
                current_field = None
            continue

        # Unlabelled line.
        stripped = CHAR_HINT_RE.sub("", line) if CHAR_HINT_RE.match(line) else line
        if current_field is None:
            # Something after 'Confirmed or expected:' that is not a heading
            # -> we have left the partners section.
            in_section = False
            continue
        setattr(current, current_field, join_continuation(current_field, getattr(current, current_field), stripped))

    # Sanity checks -----------------------------------------------------------
    n_confirmed = sum(1 for l in body[start:] if l.strip().startswith("Confirmed or expected:"))
    if len(partners) != n_confirmed:
        warnings.append(f"{len(partners)} partner blocks but {n_confirmed} 'Confirmed or expected:' lines in the section")
    for i, p in enumerate(partners, start=1):
        if not p.name:
            warnings.append(f"partner #{i}: empty Name")
        if "role" not in p.seen:
            warnings.append(f"partner #{i} ({p.name}): no 'Role in project' field")
        if "confirmed" not in p.seen:
            warnings.append(f"partner #{i} ({p.name}): no 'Confirmed or expected' field (block may be truncated)")
        if p.email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", p.email):
            warnings.append(f"partner #{i} ({p.name}): email looks odd: {p.email!r}")
        if "Up to 2000 characters" in p.role:
            warnings.append(f"partner #{i} ({p.name}): character hint leaked into role text")
    return partners, warnings


# ----------------------------------------------------------------------------
# Step 5 - output
# ----------------------------------------------------------------------------

def slug(text: str) -> str:
    """Filename-safe token: keep letters/digits, join with hyphens."""
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-")


def applicant_slug(name: str, applicant_type: str) -> str:
    words = [w for w in re.split(r"\s+", name.strip()) if re.search(r"[A-Za-z0-9]", w)]
    if applicant_type.lower().startswith("org"):
        chosen = words[:2]
    elif len(words) == 1:
        chosen = words
    else:
        chosen = [words[0], words[-1]]        # first name + surname
    chosen = [w if w.isupper() else w[:1].upper() + w[1:] for w in chosen]  # 'stella carr' -> Stella Carr
    return "-".join(slug(w) for w in chosen)


def output_filename(meta: Meta) -> str:
    words = [w for w in meta.project_title_full.split() if re.search(r"[A-Za-z0-9]", w)][:3]
    return f"{meta.start_year}-{meta.start_month}-{applicant_slug(meta.applicant_name, meta.applicant_type)}-{'-'.join(slug(w) for w in words)}.csv"


def write_csv(path: Path, meta: Meta, partners: list[Partner]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(CSV_HEADER)
        for p in partners:
            w.writerow([meta.project_title, p.name, p.contact, p.email, p.role, "", "", ""])


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

ARCHIVE_DIRNAME = "processed"


def archive(pdf: Path, archive_dir: Path) -> Path:
    """
    Move a successfully processed PDF into <data>/processed/.

    If a file of that name is already there, the incoming one is suffixed
    ' (2)', ' (3)', ... so nothing is ever silently overwritten.  A PDF that is
    already inside the archive directory is left alone.
    """
    if pdf.parent.resolve() == archive_dir.resolve():
        return pdf
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / pdf.name
    n = 2
    while target.exists():
        target = archive_dir / f"{pdf.stem} ({n}){pdf.suffix}"
        n += 1
    shutil.move(str(pdf), str(target))
    return target


def process(pdf: Path, out_dir: Path, dump: bool, archive_dir: Path | None) -> int:
    pages = pdf_to_pages(pdf)
    header, body, mismatches = clean_pages(pages)
    meta = extract_meta(pdf, header, body, len(pages), mismatches)
    partners, warnings = parse_partners(body)

    if dump:
        dbg = out_dir / "_debug"
        dbg.mkdir(parents=True, exist_ok=True)
        (dbg / (pdf.stem + ".cleaned.txt")).write_text("\n".join(body), encoding="utf-8")

    out_path = out_dir / output_filename(meta)
    write_csv(out_path, meta, partners)

    print(f"\n=== {pdf.name} ({meta.n_pages} pages)")
    print(f"  Project (full) : {meta.project_title_full}")
    if meta.project_title != meta.project_title_full:
        print(f"  Project (Bid)  : {meta.project_title}")
    print(f"  Applicant      : {meta.applicant_name} [{meta.applicant_type}]")
    print(f"  Start          : {meta.start_year}-{meta.start_month}")
    print(f"  Partners       : {len(partners)}")
    print(f"  -> {out_path}")
    if meta.header_mismatch_pages:
        print(f"  NOTE: page header differs on pages {meta.header_mismatch_pages}")
    for w in warnings:
        print(f"  WARNING: {w}")

    if archive_dir is not None:
        if warnings:
            print(f"  NOT archived (warnings above); still at {pdf}")
        else:
            moved = archive(pdf, archive_dir)
            print(f"  already archived" if moved == pdf else f"  archived -> {moved}")
    return len(warnings)


def main() -> None:
    # A legacy Windows console defaults to cp1252 and raises UnicodeEncodeError
    # when a project title contains anything outside it (e.g. "Māori", "Łódź").
    # Never let a console limitation abort an otherwise good extraction.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    require_pdftotext()   # hard stop before any other work
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="*", type=Path, help="specific PDF(s); default: every *.pdf in --data")
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("exports"))
    ap.add_argument("--dump", action="store_true", help="write cleaned text to <out>/_debug/ for inspection")
    ap.add_argument("--no-archive", dest="archive", action="store_false",
                    help=f"do not move processed PDFs into <data>/{ARCHIVE_DIRNAME}/")
    ap.add_argument("--redo", action="store_true",
                    help=f"also reprocess PDFs already sitting in <data>/{ARCHIVE_DIRNAME}/")
    args = ap.parse_args()

    archive_dir = args.data / ARCHIVE_DIRNAME

    if args.pdfs:
        pdfs = args.pdfs
        missing = [p for p in pdfs if not p.is_file()]
        if missing:
            sys.exit("ERROR: file(s) not found: " + ", ".join(str(m) for m in missing))
    else:
        pdfs = sorted(args.data.glob("*.pdf"))
        n_archived = 0
        if args.redo:
            archived = sorted(archive_dir.glob("*.pdf"))
            n_archived = len(archived)
            pdfs += archived
        if not pdfs:
            already = len(list(archive_dir.glob("*.pdf"))) if archive_dir.is_dir() else 0
            if already and not args.redo:
                sys.exit(
                    f"No new PDFs in {args.data}. "
                    f"{already} already in {archive_dir} — use --redo to reprocess them."
                )
            sys.exit(f"No PDFs found in {args.data}")
        if n_archived:
            print(f"--redo: including {n_archived} PDF(s) from {archive_dir}")

    args.out.mkdir(parents=True, exist_ok=True)

    total_warnings = 0
    for pdf in pdfs:
        total_warnings += process(pdf, args.out, args.dump, archive_dir if args.archive else None)
    print(f"\nDone. {len(pdfs)} PDF(s) processed, {total_warnings} warning(s).")
    sys.exit(1 if total_warnings else 0)


if __name__ == "__main__":
    main()
