from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interconnect_alpha.validation import ValidationError, project_root, validate_report_voice


def main() -> int:
    try:
        result = validate_report_voice(project_root())
    except ValidationError as exc:
        print(f"VOICE_LINT_ERROR {exc}")
        return 1
    print(f"VOICE_LINT_OK {result.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
