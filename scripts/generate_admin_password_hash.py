"""Generate SHA-256 hash for VYAPARSETU_ADMIN_PASSWORD_HASH."""

from __future__ import annotations

import getpass
import hashlib
import sys


def main() -> int:
    password = ""
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Enter admin password: ")

    if not password:
        print("No password provided.")
        return 1

    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
