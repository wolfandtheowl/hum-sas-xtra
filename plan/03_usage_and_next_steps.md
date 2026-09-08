# 03 – Usage and next steps

## Running it

```bash
# prerequisites (once)
brew install poppler            # provides pdftotext / pdftoppm

# all NEW PDFs in ./data -> one CSV each in ./exports, then archived
python3 extract_partners.py

# one specific PDF, or custom folders
python3 extract_partners.py "data/2023-01 Guildford OLD.pdf"
python3 extract_partners.py --data /path/to/pdfs --out /path/to/csvs

# keep the cleaned text for debugging
python3 extract_partners.py --dump      # -> exports/_debug/*.cleaned.txt

# leave PDFs where they are / reprocess the archive
python3 extract_partners.py --no-archive
python3 extract_partners.py --redo
```

## Which PDFs count as "already done"

The script does not keep a database or compare timestamps. Instead the folder
*is* the state:

* `./data/` holds PDFs **still to do**.
* `./data/processed/` holds PDFs **already extracted**, and a plain run skips it.

After a PDF extracts with **zero warnings** it is moved into
`./data/processed/`. So the normal workflow is: drop new applications into
`./data`, run the script, and only the new ones are picked up.

Deliberate details:

* **A PDF that raised any warning is not moved.** It stays in `./data` with
  `NOT archived (warnings above)` on the console, so a bad parse cannot quietly
  be marked as finished. Fix the cause, run again, and it archives itself.
* **Nothing is overwritten.** If a file of the same name is already in
  `processed/`, the incoming one becomes `name (2).pdf`, `name (3).pdf`, and so
  on. That keeps genuinely re-sent applications distinguishable rather than
  clobbering the earlier copy.
* **A plain run with an empty `./data`** exits with a message telling you how
  many PDFs are already in `processed/` and that `--redo` will reprocess them.
* **Naming a PDF explicitly on the command line always processes it**, wherever
  it lives, including inside `processed/`.
* **`--redo`** adds `processed/` back into the batch; those files are recognised
  as already archived and are not moved again.
* **`--no-archive`** turns the move off entirely, for a dry run or when you want
  to keep the input folder untouched.

Because the output filename is derived from the PDF's own contents, re-running a
PDF simply rewrites the same CSV. Re-processing is therefore always safe.

Console output per PDF: full project title, the (possibly trimmed) Bid value,
applicant, start month, partner count, the output path, and any warnings. The
exit code is non-zero if any warning was raised, so it is safe to run in a batch
and grep for `WARNING`.

Re-running overwrites the CSV for that PDF (same deterministic filename).

## Adding new PDFs

Drop them into `./data` and run the script; already-processed files sit in
`./data/processed/` and are skipped. The parser is anchored on the form's own
labels, so new applications from the same NLPG form should work without
changes. If the funder changes the form, the places to look first are
the constants at the top of `extract_partners.py`:

* `FIELD_LABELS` – the five field labels inside a partner block.
* `PARTNERS_HEADING_RE`, `FOOTER_RE`, `CHAR_HINT_RE`, `NLPG_RE`.
* `START_DATE_RE`, `APPLICANT_NAME_RE`, `APPLICANT_TYPE_RE`.

A warning such as *"N partner blocks but M 'Confirmed or expected:' lines"* means
a block was not delimited as expected — run with `--dump` and look at the
cleaned text around the partners section.

## Possible follow-ups (not done, not asked for)

* Combine all per-PDF CSVs into one master sheet (trivial `cat` minus headers,
  or a `--merge` flag).
* Pre-fill column F *Type* with `Individual` when *Rep (if org)* is empty, if
  that matches how the assistant classifies entries.
* Normalise applicant-supplied text (capitalise emails consistently, add missing
  spaces after full stops) — deliberately not done so the CSV stays faithful to
  the submitted application.
