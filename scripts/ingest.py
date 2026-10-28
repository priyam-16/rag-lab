"""Kept for convenience. Same as:  raglab ingest [--config configs/default.yaml]"""

import sys

from raglab.cli import main

if __name__ == "__main__":
    sys.exit(main(["ingest", *sys.argv[1:]]))
