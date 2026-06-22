from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interconnect_alpha.validation import ValidationError, project_root, validate_traceability


def main() -> int:
    try:
        result = validate_traceability(project_root())
    except ValidationError as exc:
        print(f"TRACEABILITY_ERROR {exc}")
        return 1
    print(f"TRACEABILITY_OK {result.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
