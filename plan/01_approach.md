# 01 – Approach: extracting the Partners section from NLPG application PDFs

Date: 2026-09-07
Brief: [initial-prompt.md](initial-prompt.md)
Script: [extract_partners.py](../extract_partners.py)

## What the PDFs look like

All three PDFs in `./data` are Arts Council England *National Lottery Project Grants*
application printouts (iText-generated, 91–143 pages). They share one layout:

* **Running header on every page** – line 1 `Applicant: <name>` with the applicant
  number right-justified; line 2 `Project: <title>` with the funder reference
  `NLPG-…` right-justified. Two wrinkles:
  * A long project title wraps onto extra *left-justified* lines (SAS Stella PDF).
  * A long NLPG reference wraps onto an extra *right-justified / indented* line
    (BOP Jazz PDF: `NLPG-00613834-LON-UN-` / `0000005654`).
* **Running footer on every page** – `Application submission   Page N   dd/mm/yyyy`.
* **Page 2** – `Applicant name:` and `Applicant type: Individual|Organisation`.
* **Page 4** – `Project start date: dd/mm/yyyy`.
* **Partners** – first a *summary table* (Name / Main contact / Email / Role /
  Confirmed) where long values are cut with `...` — this is the "bird's-eye view"
  the brief says to ignore. It is followed by one `Partners details` block per
  partner with the full fields:

  ```
  Partners details
      Name: …
      Main contact (if organisation): …
      Email address: …
      Role in project: … (multi-line, up to 2000 chars)
      Confirmed or expected: Confirmed
  ```

* Blocks are split arbitrarily by page breaks: the `Partners details` heading can
  sit at the bottom of one page with the fields on the next; the Role text can
  run over a page boundary; even `Name:` can be separated from its
  `Main contact` line.
* Older PDFs (2023) print a hint label `Up to 2000 characters` in the label column
  on the *second* line of the Role text. In layout-mode text this appears as a
  prefix of that line and must be stripped.
* `Name:` and `Email address:` also occur in other sections of the form
  (applicant address, venues, etc.), so parsing must be anchored to the first
  `Partners details` heading.
* Long `Name:` values wrap onto a second line (e.g. *Imperial Society of Teachers
  of Dancing, Brighton*; *Arts Section, Place, Arts & Economy, Warwick District
  Council*).
* One applicant literally typed `Role in project:` at the start of their role
  text, giving `Role in project: Role in project: Connecting…` in the PDF.

## Tooling decision

`pdftotext -layout` (poppler) rather than a Python PDF library:

* Already installed here, deterministic, and the layout mode keeps the
  label/value column structure so that "left-justified continuation" vs
  "right-justified NLPG wrap" can be told apart by indentation.
* No third-party Python packages needed, so the script is standard-library only
  (Python 3.9+). The only dependency is `pdftotext` on the PATH
  (`brew install poppler`).

## Pipeline (one PDF → one CSV)

1. **PDF → pages.** `pdftotext -layout` output split on form feeds.
2. **Strip headers/footers per page.** Header = from the `Applicant:` line to the
   first blank line (this swallows wrapped title / NLPG lines). Footer = the
   `Application submission … Page N …` line and anything after it. Remaining body
   lines from all pages are concatenated, so blocks split by page breaks become
   contiguous again. The header of every page is compared with page 1's; any
   difference is reported (none in the three files).
3. **Metadata.**
   * *Project title* – text after `Project:` on page 1's header, with the `NLPG-…`
     token removed, plus any continuation line that starts in column 0.
     Indented continuation lines are the NLPG wrap and are ignored.
   * *Bid column* – the title, trimmed to 8 words if it has more than 10 "real"
     words (tokens with a letter/digit; a lone `-` does not count). A trailing
     connector such as *in / of / the / -* is dropped so the trimmed title does
     not end on a dangling word.
   * *Applicant name / type* – `Applicant name:` and `Applicant type:` lines.
   * *Start date* – `Project start date: dd/mm/yyyy` → `YYYY-MM`.
4. **Partners.** From the first `Partners details` heading: each heading starts a
   new block; a line matching one of the five labels starts a field; any other
   non-blank line is a continuation of the current field (after removing a
   leading `Up to N characters` hint). A duplicate label inside one block is
   treated as text, and a leading literal `Role in project:` inside the role
   value is removed. Continuations are joined with a space, except: email
   continuations are joined with nothing; a line ending in `-` (word-hyphen) is
   joined with nothing so `award-` + `winning` → `award-winning`. The section ends
   at the first non-blank, non-heading line after a `Confirmed or expected:`.
5. **CSV.** Header exactly as `exports/example.csv`
   (`Bid,Name,Rep (if org),Email,Role/Bio,Type,Art Form,Sector`); Type / Art
   Form / Sector left empty for the assistant. UTF-8, minimal quoting, `\n`
   line endings. The blank second row in example.csv was treated as an accident
   and not reproduced.
6. **Filename.** `YYYY-MM-{First}-{Surname}-{first-3-title-words}.csv`
   * Organisation → first two words of the applicant name.
   * Individual → first and last word of the name, capitalised
     (`stella carr` → `Stella-Carr`); single-word names have no surname part.
   * Title words are the first three tokens containing a letter/digit, with
     non-alphanumerics collapsed to `-`.
7. **Sanity checks** printed per file and reflected in the exit code:
   block count == number of `Confirmed or expected:` lines in the section, every
   block has a Name, Role and Confirmed field, emails look like emails, no
   character-hint leak.

## Decisions worth knowing about

* The Guildford file is named `2023-01 …` (its submission date) but its
  *Project start date* is 04/07/2022, so per the brief its CSV is `2022-07-…`.
* Text is reproduced as typed by the applicant, including typos
  (`guildfrod.gov.uk`, `Gloustershire`) and missing spaces after full stops
  where the applicant's paragraph breaks were collapsed by the form
  (`festival.Griffin and Jones`). Inserting spaces automatically would also
  break `JTA.UK` and `C.R.E.A.M`, so nothing is "corrected".
* The `Confirmed or expected` value is parsed (it marks the end of a block) but
  not exported, as instructed.
