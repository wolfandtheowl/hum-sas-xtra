# Partner Extractor

Reads Arts Council England **NLPG application PDFs** and writes one **CSV per PDF**,
listing every partner in the "Partners details" section.

---

## 1. What you need first

Two things must be installed. Check both before anything else.

### 1.1 Python 3.9 or newer

Open **Git Bash** (Windows) or **Terminal** (macOS) and run:

```bash
python3 --version
```

Expect something like `Python 3.11.5`.

If it is missing, install from <https://www.python.org/downloads/>.
**Windows: tick "Add python.exe to PATH" during setup.**

> If `python3` is not recognised on Windows, try `python --version` instead,
> and use `python` in place of `python3` in every command below.

### 1.2 Poppler (provides `pdftotext`)

This is the part that is most often missing. The program **cannot read PDFs
without it** and will refuse to start.

Check:

```bash
pdftotext -v
```

Expect something like `pdftotext version 24.02.0`.

If you get "command not found", install it using the section for your system
below. On Windows the copy lives inside this project and is **not** on your
PATH, so `pdftotext -v` will keep saying "command not found" — that is normal.
Confirm it instead by simply running the program (§3).

**Windows (Git Bash)** — keep it inside this project, install nothing system-wide

1. Go to <https://github.com/oschwartz10612/poppler-windows/releases>
2. Download the newest `Release-xx.xx.x-0.zip`.
3. Unzip it into a `vendor/poppler` folder **inside this project**, so you end up
   with something like:

```
<this project>/vendor/poppler/poppler-24.08.0/Library/bin/pdftotext.exe
```

4. That is all. Re-run the program — it finds `pdftotext.exe` automatically.

> **No PATH editing, no `.bashrc`, nothing written to `C:\`.** The exact folder
> name inside `vendor/poppler` does not matter; any `bin` folder below it is
> found. `vendor/` is git-ignored, so these binaries are never committed.

If you prefer, create the folder first:

```bash
mkdir -p vendor/poppler
```

then unzip into it.

**macOS**

```bash
brew install poppler
```

**Debian / Ubuntu**

```bash
sudo apt install poppler-utils
```

Do not continue until either `pdftotext -v` prints a version (macOS / Linux),
or `vendor/poppler/.../bin/pdftotext.exe` exists (Windows).

---

## 2. Folder layout

```
.
├── extract_partners.py   the program
├── vendor/poppler/       Windows only: unzipped Poppler (git-ignored)
├── data/                 PUT YOUR PDFs HERE
│   └── processed/        finished PDFs are moved here automatically
└── exports/              your finished CSVs appear here
```

`data/processed/` and `exports/` are created automatically. You must create
`data/` yourself if it is not there:

```bash
mkdir -p data
```

---

## 3. Running it

Open Git Bash / Terminal **in this folder**.

> On Windows: open the project folder in File Explorer, right-click the empty
> space, and choose **"Open Git Bash here"**.

### Step 1 — Put PDFs in `data/`

Copy your application PDFs into the `data` folder. Filenames do not matter.

### Step 2 — Run

```bash
python3 extract_partners.py
```

### Step 3 — Collect your CSVs

Look in `exports/`. Files are named automatically:

```
2023-05-BOP-Productions-Jazz-Arts-ReWIRED.csv
└─ start date ─┘└─ applicant ─┘└─ project ─┘
```

---

## 4. Reading the output

After each PDF you will see a summary:

```
=== my-application.pdf (58 pages)
  Project (full) : Jazz Arts ReWIRED
  Applicant      : BOP Productions [Organisation]
  Start          : 2023-05
  Partners       : 12
  -> exports/2023-05-BOP-Productions-Jazz-Arts-ReWIRED.csv
  archived -> data/processed/my-application.pdf
```

The last line ends with either:

| Line | Meaning | Action |
|---|---|---|
| `archived -> ...` | Clean. PDF moved to `data/processed/`. | None. |
| `NOT archived (warnings above)` | Something looked wrong. PDF stayed in `data/`. | **Check it — see §6.** |

The final line is a total:

```
Done. 5 PDF(s) processed, 0 warning(s).
```

**Aim for 0 warnings.**

### CSV columns

| Bid | Name | Rep (if org) | Email | Role/Bio | Type | Art Form | Sector |
|---|---|---|---|---|---|---|---|

The last three are left blank deliberately, for you to fill in.

---

## 5. Everyday commands

| Command | What it does |
|---|---|
| `python3 extract_partners.py` | Process every new PDF in `data/`. |
| `python3 extract_partners.py data/one.pdf` | Process a single named PDF. |
| `python3 extract_partners.py --redo` | Also re-process everything in `data/processed/`. |
| `python3 extract_partners.py --no-archive` | Leave PDFs in `data/` instead of moving them. |
| `python3 extract_partners.py --dump` | Also write the extracted text to `exports/_debug/`. |

Running it twice is safe: a PDF already moved to `processed/` is skipped, and
CSVs are simply rewritten.

---

## 6. Troubleshooting

**`ERROR: pdftotext was not found`**
Go back to §1.2. On Windows, check that a `bin` folder containing
`pdftotext.exe` really does sit somewhere below `vendor/poppler/` — the most
common mistake is unzipping one level too deep, leaving
`vendor/poppler/Release-24.08.0/poppler-24.08.0/...` when you only meant one
`vendor/poppler/poppler-24.08.0/...`. The error message prints the exact folder
being searched.

**`No new PDFs in data. N already in data/processed`**
Everything is done already. Add new PDFs to `data/`, or use `--redo`.

**`WARNING: N partner blocks but M 'Confirmed or expected:' lines`**
The partner list was cut short — the CSV is probably **missing partners**.
Open the CSV and compare against the PDF before using it. This is the one
warning worth taking seriously.

**`WARNING: partner #N: empty Name` / `email looks odd`**
Usually the applicant typed something unexpected into the form. Check that row
in the CSV and correct it by hand.

**Accents look wrong, or everything lands in column A, when opened in Excel**
The CSV file itself is correct — this is Excel's import setting.
Use **Data ▸ From Text/CSV**, choose **65001: Unicode (UTF-8)** and **Comma**
as the delimiter, rather than double-clicking the file.

**Nothing happens / `command not found: python3`**
Try `python` instead of `python3`.

---

## 7. Quick reference

```bash
pdftotext -v                      # 1. confirm Poppler (macOS/Linux; on
                                  #    Windows just check vendor/poppler/)
python3 --version                 # 2. confirm Python is installed
cp /path/to/*.pdf data/           # 3. add PDFs
python3 extract_partners.py       # 4. run
ls exports/                       # 5. collect CSVs
```
