![CI](https://github.com/kmpoltorak/pdf-text-miner/actions/workflows/pytest.yml/badge.svg)

# pdf-text-miner

A small command-line tool that searches a PDF for a phrase and reports how many
times it occurs on each page. It works on the PDF's text layer, so it is for
born-digital PDFs, not scans.

```console
$ pdf-text-miner -f lorem-ipsum.pdf -t "lorem" -c
Searched text exists 7 times on page 1.
```

- A phrase that wraps onto the next line is still found: whitespace is normalized the same way in the PDF and in the phrase.
- Every failure exits with its own code and a one-line message on stderr: empty file, not a PDF, missing file, encrypted, I/O error, bad arguments.
- Results are written to a temporary file and renamed into place, so a failed write leaves the previous file unchanged.
- The tool refuses to write results over the input PDF.

## Install

Requires Python 3.10 or newer.

```bash
pip install git+https://github.com/kmpoltorak/pdf-text-miner.git
```

This installs the `pdf-text-miner` command on your `PATH`. From a checkout,
`pip install .` does the same, or run `python main.py ...` with only `pypdf`
installed.

## Quick start

```bash
pdf-text-miner -f example.pdf -t "Test text"                  # case-sensitive
pdf-text-miner -f example.pdf -t "test text" -c               # ignore case
pdf-text-miner -f example.pdf -t "Test text" -o               # save to results.txt
pdf-text-miner -f example.pdf -t "Test text" --output-path matches.txt
```

## Usage

```text
pdf-text-miner -f FILE -t TEXT [-c] [-o | --output-path PATH]
```

| Option | Meaning |
|---|---|
| `-f`, `--filename FILE` | PDF to search (required) |
| `-t`, `--text TEXT` | phrase to search for (required); quote phrases with spaces |
| `-c`, `--ignore-case` | compare case-folded text (`"STRASSE"` matches `"Straße"`); `--capitalisation` is an older alias |
| `-o`, `--output` | write results to `results.txt` in the current directory |
| `--output-path PATH` | write results to `PATH` (implies `-o`) |
| `--version` | print the version |

Matching:

- Literal: no regular expressions and no whole-word matching (`"cat"` matches `"concatenate"`).
- Each page is searched separately; matches are counted without overlap (`"aa"` occurs twice in `"aaaa"`).
- Page numbers are physical pages starting at 1, including pages without text.

Output files are UTF-8, in the same format as the printed output, and always
overwritten, and the command prints `Results saved to PATH.` With no matches the
file contains `No matches found.` A symbolic link
keeps pointing at the replaced file and an existing file keeps its permissions.

| Exit code | Meaning |
|---|---|
| 0 | search finished, also with no matches |
| 1 | input file is empty |
| 2 | input is not a readable PDF (corrupted, not a PDF, malformed page content) |
| 3 | input does not exist or is not a file |
| 4 | PDF is encrypted and needs a password |
| 5 | reading the input or writing the results failed |
| 6 | invalid arguments (missing option, empty phrase, output path equal to the input) |

Invalid arguments exited with 2 (the argparse default) in older versions.

### From Python

```python
from pdf_text_miner import find_matches

for match in find_matches("example.pdf", "Test text", ignore_case=True):
    print(match.page, match.count)
```

`find_matches` raises `ValueError` for an empty phrase and
`pypdf.errors.PyPdfError` for problems with the document (built-in errors on
malformed page content are re-raised as `PdfReadError`). `search_in_pdf()`
still returns the formatted lines. `main(argv)` runs the CLI in-process and
returns its exit code; it sets the `pypdf` logger to `ERROR` while it runs.

## Limitations

- Only the text layer is searched. Scans need OCR first (for example [OCRmyPDF](https://ocrmypdf.readthedocs.io/)).
- Layout (columns, tables, rotated text, unusual fonts) can change the order or spacing of the text [pypdf](https://pypdf.readthedocs.io/) extracts, so a phrase that looks continuous may not be found.
- A phrase split across two pages is not found.
- PDFs with a user password are not supported. Owner-password-only files work; AES-encrypted ones need `pip install "pypdf[crypto]"`.
- A hard link to the output file is not updated, because the file is replaced.

## Development

```bash
pip install -e ".[dev]"
pytest -q               # tests
ruff check .            # lint
ruff format --check .   # formatting
```

The tests generate small PDFs with ReportLab in temporary directories and run
the CLI in-process. CI runs Ruff and the tests on Python 3.10 to 3.14, then
builds the wheel, installs it into a clean virtual environment and runs the
installed command outside the source directory.

Built with an AI coding assistant. I wrote the spec and reviewed every change.

## License

MIT, see [LICENSE](LICENSE).
