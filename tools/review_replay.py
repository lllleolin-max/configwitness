"""Reproduce all actual before-failure/after-pass claims without editing checkout."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROUNDS = [
    ("input_boundary", "5dca550e9d742db892f0ba7e0de49774b3dd554f", "d7dd29b549998de62a347ed76795df9dd81c124e", "duplicate JSON field accepted"),
    ("deep_inheritance", "d7dd29b549998de62a347ed76795df9dd81c124e", "d3b4b5906e93eba52ef31259a088c124bedfabc5", "RecursionError"),
    ("output_preservation", "d3b4b5906e93eba52ef31259a088c124bedfabc5", "01f168166df56a9a67374ff0accb90c99f8b8377", "repair clobbered its original source file"),
    ("local_baseline_progress", "01f168166df56a9a67374ff0accb90c99f8b8377", "d691c12a8ad093c6f08d0ea9c4fc2ca977e3da4d", "greedy stalled while two independent unary violations were fixable"),
    ("parser_limits", "d691c12a8ad093c6f08d0ea9c4fc2ca977e3da4d", "fc071ad15c17967c1ca5b64066f9afc994ae4f81", "RecursionError"),
]


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as td:
        for name, before, after, signal in ROUNDS:
            for state, sha in (("before", before), ("after", after)):
                folder = Path(td) / (name + "-" + state); folder.mkdir()
                archive = folder / "source.zip"
                subprocess.run(["git", "archive", "--format=zip", "--output", str(archive), sha, "src"], cwd=root, check=True, capture_output=True)
                with zipfile.ZipFile(archive) as z:
                    z.extractall(folder)
                env = dict(os.environ, PYTHONPATH=str(folder / "src"))
                result = subprocess.run([sys.executable, str(root / "tools" / "probes" / (name + ".py"))], env=env, cwd=root, text=True, capture_output=True, check=False)
                if state == "before":
                    assert result.returncode != 0 and signal in result.stderr, (name, state, result.stdout, result.stderr)
                    print(name, sha, "expected FAIL:", signal)
                else:
                    assert result.returncode == 0, (name, state, result.stdout, result.stderr)
                    print(name, sha, "PASS")


if __name__ == "__main__": main()
