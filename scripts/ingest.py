"""Parse -> chunk -> embed -> index every PDF in data/raw.

Usage:  python scripts/ingest.py [--config configs/default.yaml]
"""

import argparse

from raglab.config import load_config
from raglab.pipeline import ingest

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    print(f"Ingesting with config '{cfg.name}' ...")
    print(ingest(cfg))
