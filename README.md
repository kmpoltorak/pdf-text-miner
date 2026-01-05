![CI](https://github.com/kmpoltorak/pdf-text-miner/actions/workflows/pytest.yml/badge.svg)

# pdf-text-miner

A small utility to search for text inside PDF files.

## Prerequisites

- Python 3.8+ (3.11+ recommended)

Install dependencies:

```bash
pip3 install -r requirements.txt
```

## Usage

Basic CLI:

```bash
python3 main.py -f example.pdf -t "Test text"
```

Save output to `results.txt`:

```bash
python3 main.py -f example.pdf -t "Test text" -o
```

Use `python3 main.py -h` for help.

## Running tests locally

Tests live at the repository root in `test_main.py`. The tests generate a small `lorem-ipsu.pdf` using ReportLab during runtime so no external PDF is required.

```bash
pip3 install -r requirements.txt
pytest -q
```

## Continuous Integration

A GitHub Actions workflow is provided at `.github/workflows/pytest.yml` which runs the test suite on push and pull requests. The badge at the top links to the workflow run status.
