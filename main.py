"""Compatibility entry point so ``python main.py ...`` and ``import main`` keep working.

The implementation lives in ``pdf_text_miner``; install the package to get the
``pdf-text-miner`` command instead.
"""

import sys

from pdf_text_miner import PageMatch, find_matches, format_match, main, search_in_pdf

__all__ = ["PageMatch", "find_matches", "format_match", "main", "search_in_pdf"]

if __name__ == "__main__":
    sys.exit(main())
