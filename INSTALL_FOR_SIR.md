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

Then, once, from this project's folder:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install numpy fastembed onnxruntime pdfplumber
```

To check all of that landed:

```
.venv\Scripts\python.exe corpus-lab\bin\setup_folder.py doctor
```

It prints one line per check. Every line should say PASS. If the embedding-model line says
the model is not cached, the **first** run will download it (about 130 MB), so that one run
needs an internet connection.

---

## The one command

```
.venv\Scripts\python.exe corpus-lab\bin\setup_folder.py install --folder "D:\Research\Fiscal"
```

Point `--folder` at the folder you want to ask questions about. It does five things and
prints how long each took:

1. reads every readable page of every file into a searchable index;
2. works out which files are editions of which publication;
3. builds a table-caption index so it can find a specific table;
4. turns those captions into vectors, which is what lets it match *"development spending"*
   to a table actually headed *"Public Sector Development Programme"*;
5. writes two small files into your folder — `CLAUDE.md` and `.claude\settings.json` —
   which is how Claude Code knows to use any of this.

**How long, measured on the 15,000-file test folder** (1.2 million pages):

| stage | time |
|---|---|
| reading the pages | 13 minutes with 12 workers |
| publication vectors | about 28 minutes |
| caption vectors | about 14 minutes |
| **total, 15,000 files** | **about an hour** |

Budget roughly **8 GB of disk** for a folder that size. A 500-file folder was measured end to end at **2 minutes 21 seconds** (26s to read the pages, 71s for the publication vectors, 43s for the caption vectors). If it is interrupted, run the identical command again — each stage checks for
its own output and picks up where it stopped.

It **will refuse** to run on a folder that already has a `CLAUDE.md`, so it can never
quietly overwrite something of yours.

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

Measured on a test folder of 15,000 files, on 17 questions with known answers:

| | claude-sonnet-5 | claude-opus-5 |
|---|---|---|
| pointed at a page that really prints the figure | **13 of 17** | **14 of 17** |
| gave the right number | 5 of 17 | 5 of 17 |
| correctly said "not here" when it wasn't | 3 of 3 | 2 of 3 |
| quoted a file it had not actually opened | 1 | 7 |
| typical time per question | 1m 39s | 1m 58s |

Read those honestly, because the two rows disagree with each other. It is good at finding
**where** a figure lives and much weaker at **reading it off correctly** — on questions that
track a number across a decade it found the right pages nearly every time and still got the
total wrong. Treat it as something that takes you to the page, not something that does your
arithmetic.

The last row is the one to watch in practice. Sonnet quoted a file it had not opened once in
twenty questions; Opus did it seven times. Opus writes the more fluent answer and is the looser
about where its numbers came from, so if you are checking its work, check the Sources lines
first.

Honest about the limits: the test folder is **synthetic**. The documents look and are shaped
like Pakistani fiscal publications, and the figures in them were generated, not published.
It is a fair test of *finding* things and of *not inventing* things. It is not evidence about
any real figure.

---

## When you are done

To take the two files back out of your folder (the index is kept, so a later reinstall is
instant):

```
.venv\Scripts\python.exe corpus-lab\bin\setup_folder.py uninstall --folder "D:\Research\Fiscal"
```

Add `--purge` if you also want the index deleted.
