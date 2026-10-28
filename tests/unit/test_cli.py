"""CLI wiring: subcommands parse, exit codes are what schedulers expect."""

import pytest

from raglab import cli


def test_parser_knows_all_subcommands():
    p = cli.build_parser()
    for argv in (["download"], ["ingest"], ["ask", "q"], ["serve"]):
        assert p.parse_args(argv).command == argv[0]


def test_ask_options_parse():
    args = cli.build_parser().parse_args(["ask", "what?", "--model", "x/y", "--top-k", "3"])
    assert (args.question, args.model, args.top_k) == ("what?", "x/y", 3)


def test_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as e:
        cli.main(["nope"])
    assert e.value.code != 0


def test_failure_returns_exit_code_1(monkeypatch):
    def boom(_args):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(cli, "cmd_ingest", boom)
    assert cli.main(["ingest"]) == 1


def test_success_returns_exit_code_0(monkeypatch):
    monkeypatch.setattr(cli, "cmd_ingest", lambda _args: None)
    assert cli.main(["ingest"]) == 0
