"""Portable regression: run against a chosen installed/source package version."""
import copy
import json
from pathlib import Path
import tempfile
from configwitness import InputError, Problem, load


def main():
    root = Path(__file__).resolve().parents[2]
    raw = (root / "examples" / "failover.json").read_text(encoding="utf-8")
    # Duplicate nested value is ambiguous even when both values are correctly typed.
    ambiguous = raw.replace('"replicas": 4', '"replicas": 999, "replicas": 4')
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ambiguous.json"; p.write_text(ambiguous, encoding="utf-8")
        try:
            load(p)
        except InputError:
            pass
        else:
            raise AssertionError("duplicate JSON field accepted: last value silently won")
    base = json.loads(raw)
    for edit in (lambda d: d["layers"][0].update(parents=[[]]),
                 lambda d: d["environments"][0].update(layer=[]),
                 lambda d: d["constraints"][0].update(envs=[{}]),
                 lambda d: d["edits"][0].update(field=[]),
                 lambda d: d["protected"][0].update(layer=[])):
        d = copy.deepcopy(base); edit(d)
        try:
            Problem(d)
        except InputError:
            pass
        else:
            raise AssertionError("malformed JSON value accepted")
    print("input-boundary PASS: duplicate keys rejected; five malformed identifier shapes raise InputError")


if __name__ == "__main__": main()
