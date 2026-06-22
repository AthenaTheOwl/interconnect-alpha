from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .validation import ValidationError, project_root, validate_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m interconnect_alpha",
        description="Validate Interconnect Alpha report artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate the checked-in v0.1 report artifact.",
    )
    validate_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root. Defaults to the current installed package root.",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable validation results.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        root = args.root.resolve() if args.root else project_root()
        try:
            results = validate_all(root)
        except ValidationError as exc:
            print(f"VALIDATION_ERROR {exc.check}: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps([result.to_dict() for result in results], indent=2))
        else:
            for result in results:
                print(f"OK {result.name}: {result.detail}")
            scenario = next(
                result.detail for result in results if result.name == "canonical_scenario"
            )
            print(f"VALIDATION_OK canonical_scenario={scenario}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2

