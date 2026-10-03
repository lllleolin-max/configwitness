"""JSON stdout, explicit action statuses, bounded search and reviewed output files."""
import argparse
import json
from pathlib import Path
from .model import InputError, load, read_json
from .engine import validate, trace, solve, repair, conflict, apply_edits
from .checker import check_proposal


def main(argv=None):
    parser = argparse.ArgumentParser(prog="configwitness")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("validate", "trace", "solve", "repair", "conflict", "check", "apply"):
        p = sub.add_parser(action)
        p.add_argument("input")
        if action in ("solve", "repair", "conflict"):
            p.add_argument("--max-states", type=int, default=100_000)
        if action == "trace":
            p.add_argument("env")
            p.add_argument("field")
        if action in ("check", "apply"):
            p.add_argument("proposal")
        if action in ("repair", "apply"):
            p.add_argument("--output", required=True)
        if action == "repair":
            p.add_argument("--max-repairs", type=int, default=20)
    a = parser.parse_args(argv)
    try:
        p = load(a.input)
        if a.action == "validate":
            result = validate(p)
        elif a.action == "trace":
            result = trace(p, a.env, a.field)
        elif a.action == "solve":
            result = solve(p, a.max_states)
        elif a.action == "conflict":
            result = conflict(p, a.max_states)
        elif a.action == "repair":
            result = repair(p, a.max_states, a.max_repairs)
            if result["repairs"]:
                checked = check_proposal(p, result["repairs"][0])
                if not checked["accepted"]:
                    raise InputError("internal repair rejected by independent checker")
                Path(a.output).write_text(json.dumps(result["repairs"][0], indent=2) + "\n", encoding="utf-8")
                result["proposal_written"] = True
            else:
                result["proposal_written"] = False
        else:
            proposed = read_json(a.proposal)
            result = check_proposal(p, proposed)
            if a.action == "apply" and result["accepted"]:
                changed = apply_edits(p, proposed["edits"])
                Path(a.output).write_text(json.dumps(changed.data, indent=2) + "\n", encoding="utf-8")
                result["rollout_written"] = True
        print(json.dumps(result, sort_keys=True, indent=2))
        if result.get("status") == "UNKNOWN":
            return 3
        if result.get("status") in ("INVALID", "UNSAT") or result.get("accepted") is False:
            return 1
        return 0
    except (InputError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
