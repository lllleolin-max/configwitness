"""Portable actual-console workflow; generated files live in a temporary directory."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    executable = shutil.which("configwitness")
    assert executable, "install the normal wheel before running workflow"
    source = Path(__file__).resolve().parents[1] / "examples" / "failover.json"
    with tempfile.TemporaryDirectory() as td:
        proposal, rollout = Path(td) / "proposal.json", Path(td) / "rollout.json"
        def run(args, code):
            result = subprocess.run([executable, *map(str, args)], text=True, capture_output=True, check=False)
            assert result.returncode == code, (args, result.returncode, result.stdout, result.stderr)
            return json.loads(result.stdout)
        assert run(["validate", source], 1)["status"] == "INVALID"
        t = run(["trace", source, "prod-west", "replicas"], 0)
        assert t["winner"]["layer"] == "standby"
        assert run(["solve", source], 0)["status"] == "SAT"
        r = run(["repair", source, "--output", proposal], 0)
        assert r["status"] == "OPTIMAL" and r["cost"] == 2
        assert run(["check", source, proposal], 0)["accepted"]
        assert run(["apply", source, proposal, "--output", rollout], 0)["rollout_written"]
        assert run(["validate", rollout], 0)["status"] == "VALID"
        adverse = source.with_name("no-finite-repair.json")
        assert run(["conflict", adverse], 1)["minimal"]
        assert run(["solve", source, "--max-states", 0], 3)["status"] == "UNKNOWN"
        print("console workflow: INVALID -> traced standby -> OPTIMAL cost=2 -> independently checked -> actual rollout VALID; conflict and UNKNOWN verified")


if __name__ == "__main__":
    main()
