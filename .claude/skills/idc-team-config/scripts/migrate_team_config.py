#!/usr/bin/env python3
"""Print a deterministic v1-to-v2 preview; never applies or writes migration output."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import yaml
from migration_preview import build_preview


def main():
    parser = argparse.ArgumentParser(description="Preview a deterministic team-config v1 to v2 migration")
    parser.add_argument("--config", required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    if not args.preview:
        parser.error("--preview is required; this tool has no apply mode")
    path = Path(args.config).resolve()
    if not path.is_file():
        parser.error("config not found: {}".format(path))
    document = build_preview(path)
    print(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), end="")
    status = document["migration_preview"]["status"]
    return 0 if status == "READY" else (2 if status == "BLOCKED" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
