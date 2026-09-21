"""Provided command-line and file handoffs. Core analyses are student TODOs."""
import argparse
import json
from pathlib import Path

from .config import Config
from .contracts import load_processed, save_tables


def run(stage: str, raw: Path, output: Path, cfg: Config):
    # Prevent mixing processing from one configuration with analysis from another.
    settings = output / "config.json"
    expected = json.loads(json.dumps(cfg.to_dict()))
    if settings.exists() and json.loads(settings.read_text()) != expected:
        raise ValueError("This run used a different config. Use a new --output directory.")
    if stage != "processing" and stage != "all" and not settings.exists():
        raise FileNotFoundError("No processing run found here. Run --stage processing first.")
    stages = ["processing", "rules", "clustering"] if stage == "all" else [stage]
    for name in stages:
        if name == "processing":
            from .processing import run as process
            bundle = process(raw, cfg)
            # Processing changes invalidate downstream tables, so require a fresh run.
            if any((output / child).exists() for child in ("processed", "rules", "clustering")):
                raise ValueError("Processing outputs already exist. Choose a new --output directory.")
            save_tables(bundle, output / "processed")
            settings.write_text(json.dumps(expected, indent=2) + "\n")
        else:
            data = load_processed(output / "processed")
            if name == "rules":
                from .rules import run as analyze
            else:
                from .clustering import run as analyze
            save_tables(analyze(data, cfg), output / name)
        print(f"Saved {name} outputs in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["processing", "rules", "clustering", "all"], default="all")
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("results/learning"))
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    args = parser.parse_args()
    try:
        run(args.stage, args.raw, args.output, Config.load(args.config))
    except NotImplementedError as error:
        parser.exit(2, f"Learning task not implemented yet: {error}\nSee HANDOFFS.md and the TODO comments.\n")
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
