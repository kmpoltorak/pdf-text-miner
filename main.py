#!/usr/bin/python

import argparse
import os
import sys

from PyPDF2 import PdfReader, errors


def main():
    """ A script that reads PDF and searches inside provided text. For sentences use double quotes after -t. """

    # Parse arguments from CLI
    parser = argparse.ArgumentParser(description="Search text in PDF file")
    parser.add_argument('-f', '--filename', help="provide PDF filename (with directory if different)", required=True)
    parser.add_argument('-t', '--text', help="provide text to search in PDF file", required=True)
    parser.add_argument('-o', '--output', action='store_true', help="save script output to results.txt file")
    parser.add_argument('-c', '--capitalisation', action='store_true', help="skips letter capitalization for non-specific search")
    args = parser.parse_args()

    # Check if the provided pdf file exists
    if not os.path.exists(args.filename):
        print("File not found in provided directory.")
        sys.exit()

    try:
        # Read PDF file if posible and check amount of pages
        reader = PdfReader(args.filename)
        total_pages = len(reader.pages)
        page_counter = 0
        results = []
        # Check provided text in file page by page
        while page_counter < total_pages:
            page = reader.pages[page_counter]
            # Load full text from given page
            page_text = page.extract_text()
            # Rewrite given page text to one line
            page_text = " ".join(line.strip() for line in page_text.splitlines())
            # Skip letter capitalisation if -c argument was provided
            if args.capitalisation:
                args.text = args.text.lower()
                page_text = page_text.lower()
            # Verify given page is there given text and if yes what is thew occurrence
            if args.text in page_text:
                text_occurence = page_text.count(args.text)
                results.append(f"Searched text exist {text_occurence} times on page {page_counter+1}.")
            page_counter += 1

        if not results:
            # Print info in CLI if there was no results
            print("There is no provided text inside PDF file.")
        elif results and args.output:
            # Save results to file if there was -o argument provided
            with open("results.txt", "w", encoding="utf-8") as file:
                file.write('\n'.join(_ for _ in results) + "\n")
            file.close()
        else:
            # Print results in CLI
            for _ in results:
                print(_)

    except errors.EmptyFileError:
        print("Provided file is empty")
    except errors.PdfReadError:
        print("Can't read PDF file")

# Run the script
if __name__ == "__main__":
    main()
