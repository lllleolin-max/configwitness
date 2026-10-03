"""Run after ordinary installation: python tools/contrast.py."""
import json
from pathlib import Path
from configwitness import load, repair, validate, check_proposal
from configwitness.baselines import per_environment, greedy_local


def main():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for file in ("failover.json", "already-good.json", "no-finite-repair.json"):
        p = load(root / "examples" / file)
        exact = repair(p)
        independent = per_environment(p)
        greedy = greedy_local(p)
        if exact["repairs"]:
            assert check_proposal(p, exact["repairs"][0])["accepted"]
        rows.append({"fixture": file, "current": validate(p)["status"],
                     "universe_assignments": exact["states"], "fleet_status": exact["status"],
                     "fleet_cost": exact["cost"], "fleet_valid": bool(exact["repairs"]),
                     "per_environment_cost": independent["cost"],
                     "per_environment_fleet_valid": independent.get("actual_rollout") == "VALID",
                     "greedy_cost": greedy["proposal"]["cost"], "greedy_fleet_valid": greedy["actual_rollout"] == "VALID"})
    assert rows[0]["fleet_cost"] == 2 and not rows[0]["per_environment_fleet_valid"] and not rows[0]["greedy_fleet_valid"]
    assert rows[1]["fleet_valid"] and rows[1]["per_environment_fleet_valid"] and rows[1]["greedy_fleet_valid"]
    assert rows[2]["fleet_status"] == "UNSAT"
    print(json.dumps({"synthetic": True, "incumbents_executed": False, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
