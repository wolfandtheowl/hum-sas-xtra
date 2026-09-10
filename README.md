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

If you get "command not found", install it:

**Windows (Git Bash)**

1. Go to <https://github.com/oschwartz10612/poppler-windows/releases>
2. Download the newest `Release-xx.xx.x-0.zip`.
3. Unzip it to `C:\poppler`.
4. Confirm the folder `C:\poppler\Library\bin` exists and contains `pdftotext.exe`.
5. Tell Git Bash where it is:

```bash
echo 'export PATH="$PATH:/c/poppler/Library/bin"' >> ~/.bashrc
source ~/.bashrc
```

6. Verify:

```bash
pdftotext -v
```

> Note the path style: `C:\poppler\Library\bin` becomes `/c/poppler/Library/bin`
> in Git Bash. Forward slashes, and `/c/` instead of `C:`.

**macOS**

```bash
brew install poppler
```

**Debian / Ubuntu**

```bash
sudo apt install poppler-utils
```

Do not continue until `pdftotext -v` prints a version.

---

## 2. Folder layout

```
.
├── extract_partners.py   the program
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
Poppler is not installed, or not on your PATH. Go back to §1.2.
On Windows, remember `source ~/.bashrc` (or just close and reopen Git Bash).

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
pdftotext -v                      # 1. confirm Poppler is installed
python3 --version                 # 2. confirm Python is installed
cp /path/to/*.pdf data/           # 3. add PDFs
python3 extract_partners.py       # 4. run
ls exports/                       # 5. collect CSVs
```
