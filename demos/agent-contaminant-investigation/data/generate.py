"""Generate synthetic contamination investigation inputs."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from worker.synthetic import PROFILES, write_synthetic_dataset  # noqa: E402

DATA_DIR = ROOT / "data"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples", type=int, default=24, help="Number of synthetic samples. Default: 24")
    p.add_argument(
        "--profile",
        type=str,
        default="low_contam",
        choices=sorted(PROFILES.keys()),
        help="Synthetic contamination profile",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        paths = write_synthetic_dataset(
            output_dir=DATA_DIR,
            sample_count=args.samples,
            profile=args.profile,
            seed=args.seed,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    for key, path in paths.items():
        print(f"Wrote {key}: {path}")


if __name__ == "__main__":
    main()
