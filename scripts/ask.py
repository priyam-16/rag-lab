"""Kept for convenience. Same as:  raglab ask "question" [--model ...] [--top-k 5]"""

import sys

from raglab.cli import main

if __name__ == "__main__":
    sys.exit(main(["ask", *sys.argv[1:]]))
