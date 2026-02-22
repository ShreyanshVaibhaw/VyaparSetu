"""Generate an evidence bundle for competition submission."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.common.submission_pack import generate_submission_pack


def main() -> int:
    result = generate_submission_pack()
    print("Submission Pack Summary")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
