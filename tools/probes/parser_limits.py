"""Runtime JSON limits must produce documented errors rather than tracebacks."""
from pathlib import Path
import sys
import tempfile
from configwitness import InputError
from configwitness.model import read_json


def main():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "input.json"
        cases = ["[" * 2000 + "0" + "]" * 2000]
        if sys.get_int_max_str_digits():
            cases.append('{"x":' + "9" * (sys.get_int_max_str_digits() + 1) + "}")
        for raw in cases:
            p.write_text(raw, encoding="utf-8")
            try:
                read_json(p)
            except InputError:
                pass
            else:
                raise AssertionError("JSON runtime resource limit not reported as InputError")
    print("parser-limits PASS: excessive nesting and runtime integer limit report InputError")


if __name__ == "__main__": main()
