import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

import main
import pdf_text_miner as ptm

REPO_ROOT = Path(__file__).resolve().parent


def _write_pages(path: Path, pages: list[str]) -> None:
    """Write a PDF with one page per item in `pages`; an empty string gives a page without text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    c.setFont("Helvetica", 12)
    for text in pages:
        for i, line in enumerate(text.splitlines()):
            c.drawString(72, 800 - i * 14, line)
        c.showPage()
    c.save()


def _write_pdf(path: Path, text: str):
    """Write a single-page PDF containing `text` to `path` using ReportLab."""
    _write_pages(path, [text])


def _encrypt(source: Path, target: Path, user_password: str) -> None:
    # RC4 works without optional crypto packages, which keeps the test dependencies small.
    writer = PdfWriter(clone_from=source)
    writer.encrypt(user_password=user_password, owner_password="owner", algorithm="RC4-128")
    writer.write(target)


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    """Call the CLI in-process and return (exit code, stdout, stderr)."""
    code = ptm.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    path = tmp_path / "sample.pdf"
    _write_pages(path, ["Hello world, hello again", "", "nothing here", "HELLO"])
    return path


# --- existing tests ---------------------------------------------------------


def test_search_in_pdf_with_real_pdf(tmp_path):
    pdf_path = tmp_path / "lorem-ipsum.pdf"
    # put the search term twice
    content = "lorem ipsum lorem ipsum"
    _write_pdf(pdf_path, content)

    results = main.search_in_pdf(str(pdf_path), "lorem", ignore_case=True)
    assert results == ["Searched text exists 2 times on page 1."]


def test_search_ignore_case(tmp_path):
    pdf_path = tmp_path / "lorem-ipsum.pdf"
    _write_pdf(pdf_path, "Hello World")
    results = main.search_in_pdf(str(pdf_path), "hello", ignore_case=True)
    assert results == ["Searched text exists 1 times on page 1."]


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        main.search_in_pdf("nonexistent-lorem.pdf", "x")


# --- search -----------------------------------------------------------------


def test_multiple_pages_keep_page_numbers_across_pages_without_text(sample_pdf):
    # Page 2 has no text at all; page 4 must still be reported as page 4.
    assert ptm.find_matches(sample_pdf, "hello", ignore_case=True) == [
        ptm.PageMatch(page=1, count=2),
        ptm.PageMatch(page=4, count=1),
    ]


def test_search_is_case_sensitive_by_default(sample_pdf):
    assert ptm.find_matches(sample_pdf, "hello") == [ptm.PageMatch(page=1, count=1)]


def test_no_matches_returns_empty_list(sample_pdf):
    assert ptm.find_matches(sample_pdf, "absent") == []
    assert main.search_in_pdf(str(sample_pdf), "absent") == []


def test_ignore_case_uses_casefold(tmp_path):
    pdf_path = tmp_path / "german.pdf"
    _write_pdf(pdf_path, "Straße")
    # lower() would turn "STRASSE" into "strasse", which never equals "straße".
    assert ptm.find_matches(pdf_path, "STRASSE", ignore_case=True) == [ptm.PageMatch(1, 1)]
    assert ptm.find_matches(pdf_path, "STRASSE") == []


def test_whitespace_is_normalized_in_pdf_text_and_phrase(tmp_path):
    pdf_path = tmp_path / "spaces.pdf"
    _write_pdf(pdf_path, "lorem    ipsum\ndolor")
    assert ptm.find_matches(pdf_path, "lorem ipsum") == [ptm.PageMatch(1, 1)]
    # Line breaks in the PDF and tabs/newlines in the phrase both count as one space.
    assert ptm.find_matches(pdf_path, "  ipsum\t\n dolor ") == [ptm.PageMatch(1, 1)]


def test_matches_are_literal_and_non_overlapping(tmp_path):
    pdf_path = tmp_path / "literal.pdf"
    _write_pdf(pdf_path, "aaaa abc")
    assert ptm.find_matches(pdf_path, "aa") == [ptm.PageMatch(1, 2)]
    assert ptm.find_matches(pdf_path, "a.c") == []


def test_phrase_split_across_pages_is_not_found(tmp_path):
    pdf_path = tmp_path / "split.pdf"
    _write_pages(pdf_path, ["lorem", "ipsum"])
    assert ptm.find_matches(pdf_path, "lorem ipsum") == []


@pytest.mark.parametrize("phrase", ["", " ", "\t\n"])
def test_empty_or_whitespace_phrase_is_rejected(sample_pdf, phrase):
    with pytest.raises(ValueError):
        ptm.find_matches(sample_pdf, phrase)


def test_directory_is_rejected(tmp_path):
    with pytest.raises(IsADirectoryError):
        ptm.find_matches(tmp_path, "x")


# --- CLI: output and exit codes ---------------------------------------------


def test_cli_prints_results(capsys, sample_pdf):
    code, out, err = _run(capsys, "-f", str(sample_pdf), "-t", "hello", "-c")
    assert code == ptm.EXIT_OK
    assert out == "Searched text exists 2 times on page 1.\nSearched text exists 1 times on page 4.\n"
    assert err == ""


def test_cli_ignore_case_long_aliases(capsys, sample_pdf):
    for flag in ("--ignore-case", "--capitalisation"):
        code, out, _ = _run(capsys, "-f", str(sample_pdf), "-t", "HELLO", flag)
        assert code == ptm.EXIT_OK
        assert "on page 1." in out


def test_cli_no_matches(capsys, sample_pdf):
    code, out, err = _run(capsys, "-f", str(sample_pdf), "-t", "absent")
    assert (code, out, err) == (ptm.EXIT_OK, f"{ptm.NO_MATCHES_MESSAGE}\n", "")


@pytest.mark.parametrize(
    "argv",
    [
        ["-t", "x"],  # missing -f
        ["-f", "doc.pdf"],  # missing -t
        ["-f", "doc.pdf", "-t", "   "],  # whitespace-only phrase
        ["-f", "doc.pdf", "-t", "x", "--unknown"],
    ],
)
def test_cli_invalid_arguments(capsys, tmp_path, argv):
    _write_pdf(tmp_path / "doc.pdf", "x")
    argv = [str(tmp_path / a) if a == "doc.pdf" else a for a in argv]
    code, out, err = _run(capsys, *argv)
    assert code == ptm.EXIT_USAGE
    assert out == ""
    assert "error:" in err


def test_cli_help_returns_zero(capsys):
    code, out, _ = _run(capsys, "--help")
    assert code == ptm.EXIT_OK
    assert "--output-path" in out


def test_cli_missing_file(capsys, tmp_path):
    code, out, err = _run(capsys, "-f", str(tmp_path / "missing.pdf"), "-t", "x")
    assert (code, out) == (ptm.EXIT_NOT_FOUND, "")
    assert "file not found" in err


def test_cli_directory_instead_of_file(capsys, tmp_path):
    code, _, err = _run(capsys, "-f", str(tmp_path), "-t", "x")
    assert code == ptm.EXIT_NOT_FOUND
    assert "not a file" in err


def test_cli_empty_file(capsys, tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    code, _, err = _run(capsys, "-f", str(empty), "-t", "x")
    assert code == ptm.EXIT_EMPTY_FILE
    assert "empty" in err


@pytest.mark.parametrize("content", [b"this is not a PDF", b"%PDF-1.4\n%garbage without xref"])
def test_cli_corrupted_pdf(capsys, tmp_path, content):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(content)
    code, out, err = _run(capsys, "-f", str(broken), "-t", "x")
    assert (code, out) == (ptm.EXIT_INVALID_PDF, "")
    assert "cannot read PDF" in err
    assert "Traceback" not in err


def test_cli_password_protected_pdf(capsys, tmp_path, sample_pdf):
    encrypted = tmp_path / "encrypted.pdf"
    _encrypt(sample_pdf, encrypted, user_password="secret")
    code, _, err = _run(capsys, "-f", str(encrypted), "-t", "hello")
    assert code == ptm.EXIT_ENCRYPTED
    assert "password" in err


def test_encrypted_pdf_with_empty_user_password_is_searchable(tmp_path, sample_pdf):
    # Owner-only protection (no user password) does not prevent reading.
    encrypted = tmp_path / "encrypted.pdf"
    _encrypt(sample_pdf, encrypted, user_password="")
    assert ptm.find_matches(encrypted, "HELLO") == [ptm.PageMatch(4, 1)]


def test_cli_input_permission_denied(capsys, monkeypatch, sample_pdf):
    def deny(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    # Mocked: chmod-based tests are unreliable on Windows and when running as root.
    monkeypatch.setattr(ptm, "open", deny, raising=False)
    code, _, err = _run(capsys, "-f", str(sample_pdf), "-t", "x")
    assert code == ptm.EXIT_IO_ERROR
    assert "Permission denied" in err


def test_cli_does_not_mask_unexpected_errors(monkeypatch, sample_pdf):
    def boom(*args, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(ptm, "find_matches", boom)
    with pytest.raises(RuntimeError):
        ptm.main(["-f", str(sample_pdf), "-t", "x"])


# --- CLI: writing results ---------------------------------------------------


def test_cli_output_flag_writes_results_txt(capsys, monkeypatch, tmp_path, sample_pdf):
    monkeypatch.chdir(tmp_path)
    code, out, err = _run(capsys, "-f", str(sample_pdf), "-t", "hello", "-o")
    assert (code, err) == (ptm.EXIT_OK, "")
    assert out == "Results saved to results.txt.\n"
    assert (tmp_path / "results.txt").read_text(encoding="utf-8") == (
        "Searched text exists 1 times on page 1.\n"
    )


def test_cli_output_path(capsys, tmp_path, sample_pdf):
    target = tmp_path / "custom.txt"
    code, _, _ = _run(capsys, "-f", str(sample_pdf), "-t", "HELLO", "--output-path", str(target))
    assert code == ptm.EXIT_OK
    assert target.read_text(encoding="utf-8") == "Searched text exists 1 times on page 4.\n"


def test_cli_output_without_matches_replaces_stale_results(capsys, tmp_path, sample_pdf):
    target = tmp_path / "results.txt"
    target.write_text("Searched text exists 9 times on page 9.\n", encoding="utf-8")
    code, _, _ = _run(capsys, "-f", str(sample_pdf), "-t", "absent", "--output-path", str(target))
    assert code == ptm.EXIT_OK
    assert target.read_text(encoding="utf-8") == f"{ptm.NO_MATCHES_MESSAGE}\n"


def test_cli_refuses_to_overwrite_input_pdf(capsys, monkeypatch, tmp_path, sample_pdf):
    original = sample_pdf.read_bytes()
    monkeypatch.chdir(tmp_path)
    # A different spelling of the same path must be detected too.
    for output in (str(sample_pdf), f"./{sample_pdf.name}"):
        code, out, err = _run(capsys, "-f", str(sample_pdf), "-t", "hello", "--output-path", output)
        assert (code, out) == (ptm.EXIT_USAGE, "")
        assert "overwrite the input PDF" in err
    assert sample_pdf.read_bytes() == original


def test_cli_output_flag_refuses_input_named_results_txt(capsys, monkeypatch, tmp_path, sample_pdf):
    monkeypatch.chdir(tmp_path)
    renamed = tmp_path / "results.txt"
    sample_pdf.rename(renamed)
    original = renamed.read_bytes()
    code, _, _ = _run(capsys, "-f", "results.txt", "-t", "hello", "-o")
    assert code == ptm.EXIT_USAGE
    assert renamed.read_bytes() == original


def test_cli_output_path_is_directory(capsys, tmp_path, sample_pdf):
    code, out, err = _run(capsys, "-f", str(sample_pdf), "-t", "hello", "--output-path", str(tmp_path))
    assert (code, out) == (ptm.EXIT_IO_ERROR, "")
    assert "cannot write" in err


def test_cli_empty_output_path_is_not_ignored(capsys, sample_pdf):
    code, out, err = _run(capsys, "-f", str(sample_pdf), "-t", "hello", "--output-path", "")
    assert (code, out) == (ptm.EXIT_IO_ERROR, "")
    assert "cannot write" in err


def test_cli_output_permission_denied(capsys, monkeypatch, tmp_path, sample_pdf):
    real_open = open

    def deny_writes(file, mode="r", *args, **kwargs):
        if "w" in mode:
            raise PermissionError(13, "Permission denied")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ptm, "open", deny_writes, raising=False)
    code, _, err = _run(capsys, "-f", str(sample_pdf), "-t", "hello", "-o")
    assert code == ptm.EXIT_IO_ERROR
    assert "Permission denied" in err


# --- entry points -------------------------------------------------------------


def test_python_main_py_entry_point(sample_pdf):
    """`python main.py` keeps working and reports errors on stderr without a traceback."""
    ok = subprocess.run(
        [sys.executable, "main.py", "-f", str(sample_pdf), "-t", "hello"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert (ok.returncode, ok.stdout) == (0, "Searched text exists 1 times on page 1.\n")

    missing = subprocess.run(
        [sys.executable, "main.py", "-f", "missing.pdf", "-t", "x"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert (missing.returncode, missing.stdout) == (ptm.EXIT_NOT_FOUND, "")
    assert "file not found" in missing.stderr
    assert "Traceback" not in missing.stderr


def test_python_main_py_corrupted_pdf_prints_single_error_line(tmp_path):
    # Runs in a subprocess because pytest captures log records that would otherwise reach stderr.
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a PDF")
    result = subprocess.run(
        [sys.executable, "main.py", "-f", str(broken), "-t", "x"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == ptm.EXIT_INVALID_PDF
    assert result.stderr.count("\n") == 1, result.stderr
