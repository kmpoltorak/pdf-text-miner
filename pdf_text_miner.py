"""Search for a literal phrase in the text layer of a PDF file.

Search semantics:

* The phrase is matched literally (no regular expressions, no word boundaries).
* Whitespace is normalized the same way in the page text and in the phrase:
  every run of whitespace (spaces, tabs, line breaks) becomes a single space.
* Case-insensitive search compares ``str.casefold()`` forms of both texts.
* Each page is searched separately, so a phrase split across two pages is not
  found. Matches are counted without overlap (``"aa"`` occurs twice in
  ``"aaaa"``).
* Page numbers are 1-based and always refer to the physical page, including
  pages that have no extractable text.
"""

from __future__ import annotations

import argparse
import errno
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, errors

__version__ = "1.0.0"

DEFAULT_OUTPUT_FILE = "results.txt"
NO_MATCHES_MESSAGE = "No matches found."

# Stable exit codes. 1-3 keep the meaning they had in earlier versions.
EXIT_OK = 0  # search finished, whether or not anything was found
EXIT_EMPTY_FILE = 1  # the input file is empty (0 bytes)
EXIT_INVALID_PDF = 2  # the input is not a readable PDF (corrupted, not a PDF)
EXIT_NOT_FOUND = 3  # the input path does not exist or is a directory
EXIT_ENCRYPTED = 4  # the PDF is encrypted and cannot be opened without a password
EXIT_IO_ERROR = 5  # reading the input or writing the output failed (e.g. permissions)
EXIT_USAGE = 6  # invalid command-line arguments


@dataclass(frozen=True)
class PageMatch:
    """Number of matches found on a single page (``page`` is 1-based)."""

    page: int
    count: int


def normalize_whitespace(text: str) -> str:
    """Collapse every run of whitespace into one space and trim both ends."""
    return " ".join(text.split())


def find_matches(filename: str | os.PathLike[str], text: str, ignore_case: bool = False) -> list[PageMatch]:
    """Return one ``PageMatch`` per page that contains ``text``, in page order.

    Raises:
        ValueError: ``text`` is empty or contains only whitespace.
        FileNotFoundError: ``filename`` does not exist.
        IsADirectoryError: ``filename`` is a directory.
        OSError: the file cannot be read (e.g. permission denied).
        pypdf.errors.PyPdfError: the file is not a valid PDF or is encrypted.
    """
    needle = normalize_whitespace(text)
    if not needle:
        raise ValueError("search text must not be empty or whitespace only")
    if ignore_case:
        needle = needle.casefold()

    path = Path(filename)
    # Checked explicitly because opening a directory raises PermissionError on
    # Windows, which would be reported as a misleading permission problem.
    if path.is_dir():
        raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(path))

    matches: list[PageMatch] = []
    # pypdf reads lazily, so all extraction must happen while the file is open.
    with open(path, "rb") as stream:
        reader = PdfReader(stream)
        for page_number, page in enumerate(reader.pages, start=1):
            # Pages without a text layer (e.g. scans) yield "" and simply never match.
            haystack = normalize_whitespace(page.extract_text() or "")
            if ignore_case:
                haystack = haystack.casefold()
            count = haystack.count(needle)
            if count:
                matches.append(PageMatch(page_number, count))
    return matches


def format_match(match: PageMatch) -> str:
    """Render a match as the line printed by the CLI and returned by ``search_in_pdf``."""
    return f"Searched text exists {match.count} times on page {match.page}."


def search_in_pdf(filename: str, text: str, ignore_case: bool = False) -> list[str]:
    """Backward-compatible wrapper around ``find_matches`` returning formatted lines."""
    return [format_match(match) for match in find_matches(filename, text, ignore_case)]


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that exits with ``EXIT_USAGE``.

    argparse exits with 2 by default, which already means "invalid PDF" here.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        description="Search for a literal phrase in the text of a PDF file, page by page.",
        epilog=(
            "Wrap multi-word phrases in quotes. "
            f"Exit codes: {EXIT_OK} success (also when nothing is found), "
            f"{EXIT_EMPTY_FILE} empty file, {EXIT_INVALID_PDF} invalid PDF, "
            f"{EXIT_NOT_FOUND} file not found, {EXIT_ENCRYPTED} encrypted PDF, "
            f"{EXIT_IO_ERROR} read/write error, {EXIT_USAGE} invalid arguments."
        ),
    )
    parser.add_argument("-f", "--filename", required=True, help="path to the PDF file")
    parser.add_argument("-t", "--text", required=True, help="phrase to search for")
    parser.add_argument(
        "-c",
        "--ignore-case",
        "--capitalisation",
        dest="ignore_case",
        action="store_true",
        help="ignore letter case (--capitalisation is kept as an alias)",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store_true",
        help=f"write results to {DEFAULT_OUTPUT_FILE} instead of printing them",
    )
    parser.add_argument(
        "--output-path",
        metavar="PATH",
        help="write results to PATH instead of printing them (implies -o)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _is_same_file(first: str, second: str) -> bool:
    """True when both paths exist and point to the same file (symlinks included)."""
    return os.path.exists(first) and os.path.exists(second) and os.path.samefile(first, second)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return its exit code; ``argv`` defaults to ``sys.argv[1:]``."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # --help, --version and usage errors; turn them into a return value.
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE

    # pypdf logs recoverable parsing problems as warnings; in the CLI they would only
    # clutter stderr next to our own message. Library users keep pypdf's defaults.
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    def fail(code: int, message: str) -> int:
        print(f"{parser.prog}: error: {message}", file=sys.stderr)
        return code

    # `is not None` so that an explicit but empty --output-path fails instead of being ignored.
    if args.output_path is not None:
        output_path = args.output_path
    else:
        output_path = DEFAULT_OUTPUT_FILE if args.output else None
    if output_path is not None and _is_same_file(output_path, args.filename):
        return fail(EXIT_USAGE, f"output file would overwrite the input PDF: {output_path}")

    try:
        matches = find_matches(args.filename, args.text, ignore_case=args.ignore_case)
    except ValueError as exc:
        return fail(EXIT_USAGE, str(exc))
    except FileNotFoundError:
        return fail(EXIT_NOT_FOUND, f"file not found: {args.filename}")
    except IsADirectoryError:
        return fail(EXIT_NOT_FOUND, f"not a file: {args.filename}")
    except OSError as exc:
        return fail(EXIT_IO_ERROR, f"cannot read {args.filename}: {exc.strerror or exc}")
    # Order matters: both subclass PdfReadError, which is handled after them.
    except errors.EmptyFileError:
        return fail(EXIT_EMPTY_FILE, f"file is empty: {args.filename}")
    except errors.FileNotDecryptedError:
        return fail(EXIT_ENCRYPTED, f"PDF is password-protected: {args.filename}")
    except errors.DependencyError as exc:
        # AES-encrypted PDFs need an extra crypto package: pip install "pypdf[crypto]".
        return fail(EXIT_ENCRYPTED, f"cannot decrypt {args.filename}: {exc}")
    except errors.PdfReadError as exc:
        return fail(EXIT_INVALID_PDF, f"cannot read PDF {args.filename}: {exc}")

    lines = [format_match(match) for match in matches] or [NO_MATCHES_MESSAGE]

    if output_path is None:
        print("\n".join(lines))
        return EXIT_OK

    # Always write the file, even with no matches, so a previous run's results never linger.
    try:
        with open(output_path, "w", encoding="utf-8") as output:
            output.write("\n".join(lines) + "\n")
    except OSError as exc:
        return fail(EXIT_IO_ERROR, f"cannot write {output_path}: {exc.strerror or exc}")
    print(f"Results saved to {output_path}.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
