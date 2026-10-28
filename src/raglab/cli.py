"""raglab command-line interface — one command, several subcommands.

    raglab download                                   fetch the default corpus into data/raw
    raglab ingest   --config configs/default.yaml     parse -> chunk -> embed -> index
    raglab ask      "question" [--model M] [--top-k K]
    raglab serve    [--port 8000] [--reload]

pyproject.toml has `[project.scripts] raglab = "raglab.cli:main"`, so installing the
project creates a `raglab` launcher (raglab.exe on Windows) that calls main() below.

Exit codes: 0 = success, 1 = failure (schedulers such as Control-M rely on this).
"""

from __future__ import annotations

import argparse
import logging
import sys

DEFAULT_CONFIG = "configs/default.yaml"
log = logging.getLogger("raglab")


# ---------- one small function per subcommand ----------


def cmd_download(args: argparse.Namespace) -> None:
    from raglab.ingest.download import download_corpus

    missing = download_corpus()
    if missing and args.strict:
        raise RuntimeError(f"{len(missing)} document(s) must be saved manually: {missing}")


def cmd_ingest(args: argparse.Namespace) -> None:
    from raglab.config import load_config
    from raglab.pipeline import ingest

    stats = ingest(load_config(args.config))
    log.info("ingest done: %s", stats)


def cmd_ask(args: argparse.Namespace) -> None:
    from raglab.config import load_config
    from raglab.pipeline import RAGPipeline

    pipe = RAGPipeline(load_config(args.config))
    try:
        ans = pipe.ask(args.question, args.top_k, args.model)
    finally:
        pipe.close()
    print(f"\n{ans.answer}\n\nSources:")
    for i, rc in enumerate(ans.citations, start=1):
        print(f"  [{i}] {rc.chunk.title} - p.{rc.chunk.page}  (score {rc.score:.3f})")
    cost = f"${ans.cost_usd:.5f}" if ans.cost_usd is not None else "n/a"
    print(f"\nmodel={ans.model}  timings={ans.timings_ms}  tokens={ans.usage}  cost={cost}")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=args.reload)


# ---------- the parser: reads the words you typed and picks a function ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raglab", description="RAG Lab pipeline")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("download", help="download the default corpus into data/raw")
    p.add_argument("--strict", action="store_true", help="fail if any document needs manual save")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("ingest", help="parse, chunk, embed and index all PDFs")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("ask", help="ask one question")
    p.add_argument("question")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--model", default=None, help="override generation.model, e.g. anthropic/...")
    p.add_argument("--top-k", type=int, default=None)
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("serve", help="start the FastAPI server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev)")
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
    except Exception:
        log.exception("raglab %s failed", args.command)
        return 1


if __name__ == "__main__":  # also allows: python -m raglab.cli ingest
    sys.exit(main())
