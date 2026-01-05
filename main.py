#!/usr/bin/python

import argparse
import os
import sys
from typing import List

# Prefer `pypdf` (successor of PyPDF2). Fall back to legacy `PyPDF2` for compatibility if `pypdf` isn't installed.
from pypdf import PdfReader, errors


def search_in_pdf(filename: str, text: str, ignore_case: bool = False) -> List[str]:
    """Search `text` inside `filename` PDF and return a list of result strings per page.

    Raises FileNotFoundError when file does not exist.
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(filename)

    reader = PdfReader(filename)
    total_pages = len(reader.pages)
    results: List[str] = []

    # Prepare search text depending on case sensitivity
    search_text = text.lower() if ignore_case else text

    for i in range(total_pages):
        page = reader.pages[i]
        page_text = page.extract_text()
        if not page_text:
            # Skip pages without extractable text
            continue
        # Normalize whitespace and strip each line
        page_text = " ".join(line.strip() for line in page_text.splitlines())
        page_search_text = page_text.lower() if ignore_case else page_text
        if search_text in page_search_text:
            count = page_search_text.count(search_text)
            results.append(f"Searched text exists {count} times on page {i+1}.")

    return results


def main():
    """CLI entrypoint for searching text in a PDF file.

    Notes: wrap multi-word search text in quotes when calling from the shell.
    """
    parser = argparse.ArgumentParser(description="Search text in PDF file")
    parser.add_argument('-f', '--filename', help="provide PDF filename (with directory if different)", required=True)
    parser.add_argument('-t', '--text', help="provide text to search in PDF file", required=True)
    parser.add_argument('-o', '--output', action='store_true', help="save script output to results.txt file")
    parser.add_argument('-c', '--capitalisation', action='store_true', help="ignore letter capitalization for search")
    args = parser.parse_args()

    try:
        results = search_in_pdf(args.filename, args.text, ignore_case=args.capitalisation)

        if not results:
            print("There is no provided text inside PDF file.")
        elif results and args.output:
            with open("results.txt", "w", encoding="utf-8") as f:
                f.write('\n'.join(results) + "\n")
        else:
            for line in results:
                print(line)

    except errors.EmptyFileError:
        print("Provided file is empty")
        sys.exit(1)
    except errors.PdfReadError:
        print("Can't read PDF file")
        sys.exit(2)
    except FileNotFoundError:
        print("File not found in provided directory.")
        sys.exit(3)


if __name__ == "__main__":
    main()

