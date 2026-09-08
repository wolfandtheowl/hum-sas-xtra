# 02 – Verification log

Date: 2026-09-07

## Run summary

| PDF | Applicant | Start | Partners | Output |
|---|---|---|---|---|
| 2023-01 Guildford OLD.pdf | Guildford Fringe Theatre Company LTD (Org) | 2022-07 | 24 | `2022-07-Guildford-Fringe-Guildford-Fringe-Festival.csv` |
| 2023-03-01 BOP Jazz Theatre JAR23 - SUCCESS.pdf | BOP Productions (Org) | 2023-05 | 57 | `2023-05-BOP-Productions-Jazz-Arts-ReWIRED.csv` |
| 2025-07-01 SAS Stella Cultivating Mother FAIL.pdf | stella carr (Individual) | 2025-08 | 32 | `2025-08-Stella-Carr-Cultivating-the-Mother.csv` |

Script exit code 0, zero warnings, no page-header mismatches.

## Manual checks against the rendered PDF pages

Pages were rendered to PNG with `pdftoppm` and read by eye (independent of the
text extraction path) and compared field-by-field with the CSV rows:

* **SAS Stella, pages 68–69** – entries 1–4 (*Stella Carr (as artist)*, *Stella
  Carr (as producer & community organiser)*, *Hill Close Garden Trust / Chris
  Wainwright*, *The Hoskins Houses Trust / Sarah Hoskins*). Names, blank reps
  for the individual entries, emails and the full role text match. Block 3 has
  its heading at the foot of page 68 and its fields on page 69 – handled.
* **SAS Stella, page 2 and page 4** – `Applicant name: stella carr`,
  `Applicant type: Individual`, `Project start date: 27/08/2025` → `2025-08`.
* **Guildford, page 56** – entries 1–3 (*The Star Inn / Pip Ellis*, *The
  Guildhall / Stephen Benbough*, *Guildford Arts / Philippa Sampson-Bancroft*).
  The `Up to 2000 characters` hint shown beside the second role line is not in
  the CSV; the wrapped role "Host for Opera on the Balcony & PR & outreach /
  support for the festival" is joined correctly. Entry 3's Role continues on
  page 57 – handled.
* **BOP Jazz, pages 63–64** – entries 1–2 (*BOP Jazz Theatre Company / Dollie
  Henry MBE* and */ Paul Jenkins*). Entry 1's 1,810-character role text runs
  over the page break with `Confirmed or expected` on page 64; the text is
  complete and in order. `co-` + `authored` was joined as `co-authored`.

## Automated cross-checks

* **Summary table vs detail blocks** – for each PDF the number of rows in the
  bird's-eye summary table equals the number of CSV rows (24 / 57 / 32), and every
  summary-table name (minus its `...`) is a prefix of the CSV name at the same
  position. No mismatches.
* **Field regexes** – all 113 emails match a basic `x@y.z` pattern; every
  block has Name, Role and Confirmed fields; no `Up to 2000 characters` or
  `Role in project` text leaked into any role value.
* **Columns F–H** – empty in every row; every row has exactly 8 columns.

## Known quirks in the source data (left as-is on purpose)

* Missing spaces after full stops where the applicant's paragraph breaks were
  collapsed by the form renderer, e.g. `…during the festival.Griffin and Jones…`
  (Guildford #7, #9, #10, #11, #15, #17, #18). These are present in the PDF text
  itself, not created by the join logic.
* Applicant typos are preserved (`guildfrod.gov.uk`, `kisa@prideinsurrey.org`,
  `Abewystweth`, `Gloustershire`).
* Guildford lists *Project director* as the "main contact" for two individuals
  (Nick and Charlotte Wyschna) – copied verbatim into the Rep column because that
  is what the applicant entered.
* BOP #28 has the placeholder email `missing@gmail.com` as typed by the applicant.
* SAS #25 (*Warwickshire Gardens Trust*) had `Role in project:` typed into the
  role text; the duplicate label was removed and the role starts at
  `Connecting CM into…`.

## Archiving (added 2026-09-08)

Processed PDFs now move to `./data/processed/`. Cases exercised end to end:

| Case | Expected | Result |
|---|---|---|
| First run, 3 clean PDFs | all extracted, all archived | 3 CSVs, `data/` empty |
| Second plain run | nothing to do, message points at `--redo` | exit 1 with that message |
| `--redo` | reprocesses the archive, no second move | `already archived` on each |
| Same filename dropped again | suffixed, original kept | `… OLD (2).pdf` created |
| `--no-archive` | file stays in `data/` | `keeper.pdf` untouched |
| Truncated PDF (partners cut mid-block) | warns, **not** archived | 3 warnings, file left in `data/` |
| Non-existent path given | clean error, no traceback | `ERROR: file(s) not found:` |

The truncated-PDF case is the important one: it was built by cutting the SAS
application at page 69 with `pdfseparate`/`pdfunite`, which strips the last
block's `Confirmed or expected` line. The block-count check caught it, so the
file was left in `data/` rather than being recorded as finished.

After these tests the three CSVs were regenerated from the archive and
re-checked: 24 / 57 / 32 rows (113 total), correct header, 8 columns per row,
columns F–H empty — identical to the pre-archiving output.

## How to re-verify after a change

```bash
python3 extract_partners.py --dump          # writes exports/_debug/<pdf>.cleaned.txt
pdftoppm -r 80 -png -f 68 -l 69 "data/<pdf>" /tmp/page   # render pages to eyeball
```

Delete `exports/_debug/` afterwards so only CSVs remain in `exports/`.
