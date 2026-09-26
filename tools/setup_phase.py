"""Prepare this machine to run one phase of the team Bob run.

    python tools/setup_phase.py 3

Each team member runs one phase in their own IBM Bob session, often on their
own machine. Phases hand work to each other through bob-output/ (committed
to the team repo). This script:
  1. checks that the files your phase needs from earlier phases are present,
  2. rebuilds demo-repo/ from scratch (it's git-ignored, so never shared),
  3. re-applies earlier phases' changes to it (e.g. the antibody tests),
  4. checks the demo repo's tests pass, so your phase starts from a known state.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# phase -> (files it needs in bob-output/, the phase that produces each)
NEEDS = {
    1: [],
    2: [("antigens.json", 1)],
    3: [("antigens.json", 1), ("mutants.json", 2)],
    4: [("antigens.json", 1), ("antibodies.test.js", 3)],
    5: [("antigens.json", 1)],
    6: [("antigens.json", 1), ("mutants.json", 2), ("antibodies.test.js", 3),
        ("results-before.json", 3), ("results-after.json", 3),
        ("results-holdout.json", 4), ("pr-comment.md", 5)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", type=int, choices=sorted(NEEDS))
    ap.add_argument("--handoff", default=str(ROOT / "bob-output"), help="shared handoff folder")
    ap.add_argument("--repo", default=str(ROOT / "demo-repo"))
    args = ap.parse_args()
    handoff, repo = Path(args.handoff), Path(args.repo)

    missing = [(f, p) for f, p in NEEDS[args.phase] if not (handoff / f).exists()]
    if missing:
        print(f"[X] Phase {args.phase} can't start yet. Missing from {handoff.name}/:")
        for f, p in missing:
            print(f"   - {f}  (produced by Phase {p}; pull the latest team repo, or ask whoever ran Phase {p})")
        sys.exit(1)
    handoff.mkdir(exist_ok=True)
    (handoff / "logs").mkdir(exist_ok=True)

    subprocess.run([sys.executable, str(ROOT / "demo/build_demo_repo.py"), str(repo)], check=True)

    if args.phase >= 4:
        shutil.copy(handoff / "antibodies.test.js", repo / "test/antibodies.test.js")
        for cmd in (["add", "-A"], ["commit", "-q", "-m", "test: antibodies from Phase 3"]):
            subprocess.run(["git", *cmd], cwd=repo, check=True, capture_output=True)
        print("[OK] Re-applied Phase 3 antibody tests to demo-repo")

    npm = shutil.which("npm") or "npm"
    if subprocess.run([npm, "test", "--silent"], cwd=repo, capture_output=True).returncode != 0:
        print("[X] demo-repo tests fail after setup. Stop and report this to the team.")
        sys.exit(1)
    print(f"[OK] Ready for Phase {args.phase}: demo-repo/ built and its tests pass.")


if __name__ == "__main__":
    main()
