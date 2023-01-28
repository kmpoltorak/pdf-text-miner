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
    args = parser.parse_args()

    # Check if the provided pdf file exists
    if not os.path.exists(args.filename):
        print("File not found in provided directory.")
        sys.exit()
    
    try:
        reader = PdfReader(args.filename)
        total_pages = len(reader.pages)
        page_counter = 0
        results = []
        while page_counter < total_pages:
            page = reader.pages[page_counter]
            page_text = page.extract_text()
            page_text = " ".join(line.strip() for line in page_text.splitlines())
            if args.text in page_text:
                text_occurence = page_text.count(args.text)
                results.append(f"Searched text exist {text_occurence} times on page {page_counter+1}.")
            page_counter += 1

        if results and args.output:
            with open("results.txt", "w", encoding="utf-8") as file:
                file.write('\n'.join(_ for _ in results) + "\n")
            file.close()
        else:
            for _ in results:
                print(_)

    except errors.EmptyFileError:
        print("Provided file is empty")
    except errors.PdfReadError:
        print("Can't PDF read file")

# Run the script
if __name__ == "__main__":
    main()
