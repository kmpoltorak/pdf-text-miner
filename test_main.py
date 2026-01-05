from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

import main


def _write_pdf(path: Path, text: str):
	"""Write a single-page PDF containing `text` to `path` using ReportLab."""
	path.parent.mkdir(parents=True, exist_ok=True)
	c = canvas.Canvas(str(path))
	c.setFont("Helvetica", 12)
	for i, line in enumerate(text.splitlines()):
		c.drawString(72, 800 - i * 14, line)
	c.showPage()
	c.save()


def test_search_in_pdf_with_real_pdf(tmp_path):
	pdf_path = tmp_path / "lorem-ipsu.pdf"
	# put the search term twice
	content = "lorem ipsum lorem ipsum"
	_write_pdf(pdf_path, content)

	results = main.search_in_pdf(str(pdf_path), "lorem", ignore_case=True)
	assert results == ["Searched text exists 2 times on page 1."]


def test_search_ignore_case(tmp_path):
	pdf_path = tmp_path / "lorem-ipsu.pdf"
	_write_pdf(pdf_path, "Hello World")
	results = main.search_in_pdf(str(pdf_path), "hello", ignore_case=True)
	assert results == ["Searched text exists 1 times on page 1."]


def test_file_not_found():
	with pytest.raises(FileNotFoundError):
		main.search_in_pdf("nonexistent-lorem.pdf", "x")
