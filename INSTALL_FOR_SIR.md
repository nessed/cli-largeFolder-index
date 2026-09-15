# Asking questions of a folder full of documents

This turns a folder of PDFs, spreadsheets and scanned reports into something you can ask
questions of in plain English — and that answers with the file, the page, and the line it
read the figure off. If it cannot find something, it says so instead of guessing.

It runs entirely on your own machine. Nothing is uploaded anywhere.

---

## What you install once

Three things, each a normal Windows installer:

1. **Python 3.11** — <https://www.python.org/downloads/>. Tick *"Add Python to PATH"*.
2. **Git for Windows** — <https://git-scm.com/download/win>. This is only here because it
   quietly includes `pdftotext.exe`, which is what reads the PDFs.
3. **Claude Code** — the terminal app, with a Claude Max subscription.

Then, once, from the package folder:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements-portable.txt
.venv\Scripts\python.exe bin\setup_folder.py doctor
```

`requirements-portable.txt` pins all 36 packages at the exact versions every number below
was measured with. `doctor` prints one line per check; every line should say PASS. If the
embedding-model line says the model is not cached, the **first** run will download it
(about 130 MB), so that one run needs an internet connection.

**What you are installing is a self-contained package** — `retrieval-portable-<commit>` —
not this development folder. It carries `bin/`, the pinned requirements, `INSTALL.md`, and
a `PACKAGE_MANIFEST.json` listing every file with its sha256 and the commit it was built
from. It was tested by installing it twice from scratch in two throwaway directories with
no connection to the lab, and once more with every file read recorded: **891 reads traced,
none of them touching the development folder.**

---

## The one command

```
.venv\Scripts\python.exe bin\setup_folder.py install --folder "D:\Research\Fiscal" --artefacts .\artefacts --seed-env
```

Point `--folder` at the folder you want to ask questions about. `--artefacts` is where the
index goes — keep it inside the package folder and everything stays in one place.
`--seed-env` fixes two settings that otherwise vary between runs, so two installs of the
same folder are comparable.

It does five things and prints how long each took:

1. reads every readable page of every file into a searchable index;
2. works out which files are editions of which publication;
3. builds a table-caption index so it can find a specific table;
4. turns those captions into vectors, which is what lets it match *"development spending"*
   to a table actually headed *"Public Sector Development Programme"*;
5. writes two small files into your folder — `CLAUDE.md` and `.claude\settings.json` —
   which is how Claude Code knows to use any of this.

It **builds the same shelf that was measured.** There is a second, experimental shelf
builder behind `--builder v2`; it failed its acceptance gate on 2026-09-15, so it prints a
warning and stamps `builder: v2 (experimental)` into the build manifest. You will never get
it by accident.

**How long, measured:**

| folder | time |
|---|---|
| 500 files | **1 minute 58 seconds** |
| 2,000 files | **6 minutes 15 seconds** |
| 15,000 files (1.2 million pages) | about an hour |

Budget roughly 8 GB of disk for a 15,000-file folder. If it is interrupted, run the
identical command again — each stage checks for its own output and picks up where it
stopped. It **will refuse** to run on a folder that already has a `CLAUDE.md`, so it can
never quietly overwrite something of yours.

### What it writes down about the build

Three files land in the artefacts directory, and they exist so that you never have to take
any of this on trust:

- **`build_manifest.json`** — every version, count and hash: which commit, which builder,
  which Python and package versions, the embedding model and the checksum of its weights,
  how many files were read and how many of each status, how many families, captions and
  vectors came out, and how long each stage took.
- **`BUILD_REPORT.md`** — the same thing in one page of plain English, including a section
  naming the three things that are *not* identical between two builds of the same folder
  (timestamps, the order the filesystem hands over files, and the last bits of the vector
  arithmetic) and what to compare instead.
- **`canonical_export.json`** — the logical content of the index, sorted, with timestamps
  stripped. Two installs of the same folder produce the same content here.

To check an install:

```
.venv\Scripts\python.exe bin\c_selftest.py --db .\artefacts\pages.db --shelf .\artefacts\shelf\shelf.db --expect-pages 0
```

18 checks. All should pass.

---

## Asking it something

```
cd "D:\Research\Fiscal"
claude --model claude-opus-5
```

Then just type the question, the way you would say it out loud:

> how does sindh's annual development programme look over the last decade or so

You do not need to name the file, the table, or the year. That is the whole point — working
out *which publication would print this* is the job it is doing for you.

---

## What a good answer looks like

Every figure comes with where it came from, and the answer ends with a `Sources` block:

```
Development expenditure rose from Rs 1,200 billion in 2014-15 to Rs 4,321 billion
in 2023-24 ...

Sources
Rs 4,321 billion | Sources/Federal/.../Economic Survey 2023-24.pdf | p239 | "Development Expenditure ... 4,321"
```

If it gives you a number with no source line, something is wrong — tell us, because there
is a check in place that is supposed to stop exactly that.

It will also tell you when figures **disagree between documents**, which they often do: the
same fiscal year gets reprinted, revised, in the next edition. A good answer names which
edition and which vintage (provisional, revised, final) each figure came from rather than
silently picking one.

## What an honest "not here" looks like

> This folder holds the national wheat production figure but not a provincial breakdown for
> Punjab in 2015-16. The editions held are ... No supporting page was opened.
>
> Sources: none — no supporting page was opened.

That is a correct answer, not a failure. Refusing honestly when the folder does not hold
something is the behaviour this was built around, and it is the part that works best:
**11 of 11** on document-level absence questions and **4 of 4** on specific identifiers.

---

## The two things it cannot see

Be aware of both, because they are invisible unless you look.

1. **Scanned pages with no text layer.** A photocopied report is a picture to this tool. In
   the test folder that is **1,211 files** it cannot read a word of.
2. **Files that failed to open at all** — 32 in the test folder — and **120** of a file type
   it does not handle.

Every search prints a `COVERAGE` line with those counts, so you can always see what was and
was not searchable:

```
COVERAGE indexed=13634 image_only_no_text=1211 failed=32 unsupported=120 pages=1206260
```

If an answer seems to be missing an obvious document, that line is the first place to look.

---

## How well does it actually work?

Measured on a test folder of 15,000 files, on 17 questions with known answers.

**These numbers were re-derived on 2026-09-16 from the same recorded sessions, after the
scoring program itself was found to have three faults.** Where a figure has changed, the
old one is shown so you can see which way it moved.

| | claude-sonnet-5 | claude-opus-5 |
|---|---|---|
| pointed at a page that really prints the figure | **13 of 17** | **14 of 17** |
| gave the right number, of the questions that have one | **5 of 5** | **5 of 5** |
| carried every year's value on a whole-table question | **4 of 7** | **4 of 7** |
| correctly said "not here" when it wasn't | 3 of 3 | 2 of 3 |
| quoted a file it had not actually opened | **1** *(was 1)* | **4** *(was 7)* |
| typical time per question | 1m 39s | 1m 58s |

Two rows moved, and both were the scorer's fault rather than the system's:

- **"gave the right number" was published as 5 of 17 for both models.** 12 of the 17
  questions have no single number in the answer key at all — they ask for a series across a
  decade, or across several documents. They could never have been marked right. On the five
  questions that do have one number, both models got all five. **The sentence "reads the
  number wrong on 12 of 17" was wrong and is withdrawn.**
- **"quoted a file it had not opened" was published as 7 for Opus.** Three of those seven
  were files merely *named in passing* in the prose, with no page and no figure attached;
  two more were pages the model *had* opened, inside a shell loop the scorer could not read.
  The corrected count is 4, and **none of the four was an invented figure** — they are pages
  cited from a table listing without opening the page itself.

The third fault affected both models: when the built-in citation check challenged an answer,
only the model's short reply was recorded, not the answer itself. Nine Sonnet sessions and
five Opus sessions were being scored on a fragment.

**The row to watch in practice is still the last one.** Both models sometimes cite a page
from a search result without opening it. Whether the gap between 1 and 4 means anything is
**not yet known** — until the same battery has been run several times, nobody can say how
much that number moves on its own. Check the Sources lines.

Read the first two rows together and honestly: this is good at finding **where** a figure
lives, and weaker at assembling one answer out of several places. On questions that track
one table across a decade it carried every year's value; on questions needing one figure
each from three different publications, both models managed one of three or none.

Honest about the limits: the test folder is **synthetic**. The documents look and are shaped
like Pakistani fiscal publications, and the figures in them were generated, not published.
It is a fair test of *finding* things and of *not inventing* things. It is not evidence about
any real figure.

**Genuine real-world cross-folder generalisation remains untested.** The package has been
installed against two different folders, but both come from the same generator; a folder
built by different rules, of the kind you would actually point it at, has never been tried.
That is the next experiment, and it has not been run.

---

## When you are done

To take the two files back out of your folder (the index is kept, so a later reinstall is
instant):

```
.venv\Scripts\python.exe bin\setup_folder.py uninstall --folder "D:\Research\Fiscal"
```

Add `--purge --artefacts .\artefacts` if you also want the index deleted.
