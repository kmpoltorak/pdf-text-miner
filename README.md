![CI](https://github.com/kmpoltorak/pdf-text-miner/actions/workflows/pytest.yml/badge.svg)

# pdf-text-miner

A small command-line tool that searches for a phrase in a PDF file and reports how many
times it occurs on each page.

```console
$ pdf-text-miner -f report.pdf -t "net revenue" --ignore-case
Searched text exists 2 times on page 1.
Searched text exists 1 times on page 7.
```

## Installation

Requires Python 3.10 or newer.

```bash
pip install git+https://github.com/kmpoltorak/pdf-text-miner.git
```

This installs the `pdf-text-miner` command, which is used in all examples below. It is a
command on your `PATH`, not a Python file: run it as `pdf-text-miner ...`, not as
`python pdf-text-miner.py ...`.

From a local checkout you have two options:

```bash
# Install the command from the checkout (inside a virtual environment)
pip install .
pdf-text-miner -f example.pdf -t "Test text"

# Or run the script directly without installing it; only pypdf is needed
pip install pypdf
python main.py -f example.pdf -t "Test text"
```

## Usage

```text
pdf-text-miner -f FILE -t TEXT [-c] [-o | --output-path PATH]
```

| Option | Description |
| --- | --- |
| `-f`, `--filename FILE` | PDF file to search (required). |
| `-t`, `--text TEXT` | Phrase to search for (required). Quote phrases that contain spaces. |
| `-c`, `--ignore-case` | Ignore letter case. `--capitalisation` is accepted as an older alias. |
| `-o`, `--output` | Write results to `results.txt` in the current directory instead of printing them. |
| `--output-path PATH` | Write results to `PATH` instead of printing them (implies `-o`). |
| `--version` | Print the version and exit. |
| `-h`, `--help` | Show help and exit. |

Examples:

```bash
# Case-sensitive search (default)
pdf-text-miner -f example.pdf -t "Test text"

# Case-insensitive search
pdf-text-miner -f example.pdf -t "test text" -c

# Save results to results.txt
pdf-text-miner -f example.pdf -t "Test text" -o

# Save results to a chosen file
pdf-text-miner -f example.pdf -t "Test text" --output-path matches.txt
```

### How matching works

- The phrase is matched **literally**: no regular expressions and no whole-word matching
  (`"cat"` also matches `"concatenate"`).
- Whitespace is normalized the same way in the PDF text and in the phrase: runs of spaces,
  tabs and line breaks count as a single space, so a phrase that wraps onto the next line
  is still found.
- `--ignore-case` compares case-folded text (`"STRASSE"` matches `"Straße"`).
- Each page is searched **separately**. A phrase split across two pages is not found.
- Matches are counted without overlap: `"aa"` occurs twice in `"aaaa"`.
- Page numbers are the physical page numbers starting at 1, including pages without text.

### Exporting results

With `-o` or `--output-path`, the results are written to the file as UTF-8 text in the
same format as the printed output, and the command prints `Results saved to PATH.`
The file is always overwritten. If nothing is found, it contains `No matches found.`,
so results from an earlier run never remain. The tool refuses to write the results over
the input PDF.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Search finished (also when no matches were found). |
| 1 | The input file is empty. |
| 2 | The input file is not a readable PDF (corrupted or not a PDF). |
| 3 | The input file does not exist or is not a file (e.g. a directory). |
| 4 | The PDF is encrypted and needs a password. |
| 5 | Reading the input or writing the results failed (e.g. permission denied). |
| 6 | Invalid arguments (missing option, empty phrase, output path equal to the input). |

Errors are printed to stderr as a single line. Codes 1–3 keep their meaning from earlier
versions. Invalid arguments used to exit with 2 (the argparse default) and now exit with 6.

## Limitations

- Only the PDF's text layer is searched. Scanned documents and images of text have no
  text layer and need OCR (for example [OCRmyPDF](https://ocrmypdf.readthedocs.io/)) first.
- Text is extracted with [pypdf](https://pypdf.readthedocs.io/). The PDF layout (columns,
  tables, rotated text, unusual fonts) can change the order of the extracted text or the
  spacing between words, so a phrase that looks continuous on screen may not be found.
- PDFs protected with a user password are not supported. Files with only an owner password
  (restricting printing or copying) can be searched. AES-encrypted files need
  `pip install "pypdf[crypto]"`.

## Using it from Python

```python
from pdf_text_miner import find_matches

for match in find_matches("example.pdf", "Test text", ignore_case=True):
    print(match.page, match.count)
```

`search_in_pdf(filename, text, ignore_case=False)` still returns the formatted lines
(`"Searched text exists N times on page P."`) for backward compatibility.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest -q               # tests generate small PDFs with ReportLab in temporary directories
ruff check .            # lint
ruff format --check .   # formatting (run `ruff format .` to fix)
```

Runtime dependencies are listed in `[project.dependencies]` of `pyproject.toml`. The
development tools (pytest, ReportLab, Ruff) are in the `dev` extra.

## Continuous Integration

The GitHub Actions workflow in `.github/workflows/pytest.yml` runs Ruff (lint and format
check) and the test suite on Python 3.10–3.14 for every push and pull request.

## License

[MIT](LICENSE)
