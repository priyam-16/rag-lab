"""Ask a question from the terminal.

Usage:  python scripts/ask.py "What is the output floor under Basel III?" [--model anthropic/claude-sonnet-4-5]
"""

import argparse

from raglab.config import load_config
from raglab.pipeline import RAGPipeline

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--model", default=None)
    ap.add_argument("--top-k", type=int, default=None)
    args = ap.parse_args()

    ans = RAGPipeline(load_config(args.config)).ask(args.question, args.top_k, args.model)
    print(f"\n{ans.answer}\n")
    print("Sources:")
    for i, rc in enumerate(ans.citations, start=1):
        print(f"  [{i}] {rc.chunk.title} - p.{rc.chunk.page}  (score {rc.score:.3f})")
    cost = f"${ans.cost_usd:.5f}" if ans.cost_usd is not None else "n/a"
    print(f"\nmodel={ans.model}  timings={ans.timings_ms}  tokens={ans.usage}  cost={cost}")
