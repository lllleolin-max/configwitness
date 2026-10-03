"""CLI must refuse output paths that already exist, including input aliases."""
import contextlib
import io
from pathlib import Path
import tempfile
from configwitness.cli import main as cli


def main():
    fixture = Path(__file__).resolve().parents[2] / "examples" / "failover.json"
    original = fixture.read_bytes()
    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "input.json"; input_path.write_bytes(original)
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli(["repair", str(input_path), "--output", str(input_path)])
        assert input_path.read_bytes() == original, "repair clobbered its original source file"
        assert code == 2, "existing output must report an input/I/O error"
        proposed = Path(td) / "proposal.json"
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli(["repair", str(input_path), "--output", str(proposed)]) == 0
        before = proposed.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli(["repair", str(input_path), "--output", str(proposed)]) == 2
        assert proposed.read_bytes() == before
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli(["apply", str(input_path), str(proposed), "--output", str(input_path)]) == 2
        assert input_path.read_bytes() == original
        repaired = Path(td) / "actual.json"
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli(["apply", str(input_path), str(proposed), "--output", str(repaired)]) == 0
            assert cli(["validate", str(repaired)]) == 0
    print("output-preservation PASS: input and existing proposal untouched; fresh proposal and actual rollout succeed")


if __name__ == "__main__": main()
