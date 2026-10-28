"""Kept for convenience. Same as:  raglab download"""

import sys

from raglab.cli import main

if __name__ == "__main__":
    sys.exit(main(["download", *sys.argv[1:]]))
