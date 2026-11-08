# ruff: noqa: INP001 - Standalone, explicitly invoked GitHub evidence sender.

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Send the collected ZIP to the authorized draft PR #5")
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    path = args.archive.resolve()
    if path.suffix != ".zip" or not path.is_file():
        parser.error("Pass the ZIP produced by collect.py")
    gh = shutil.which("gh")
    if gh is None:
        parser.error("GitHub CLI is required; authenticate it before sending")
    data = path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    sidecar = path.with_suffix(".zip.sha256").read_text(encoding="utf-8").split()[0]
    if checksum != sidecar:
        parser.error("ZIP differs from its checksum sidecar")
    encoded = base64.b64encode(data).decode("ascii")
    chunks = [encoded[index : index + 32000] for index in range(0, len(encoded), 32000)]
    with tempfile.TemporaryDirectory(prefix="astrofairy-github-return-") as temporary:
        body = Path(temporary) / "comment.md"
        for index, chunk in enumerate(chunks, 1):
            packet = {
                "name": path.name,
                "sha256": checksum,
                "bytes": len(data),
                "part": index,
                "parts": len(chunks),
                "encoding": "base64",
                "data": chunk,
            }
            body.write_text(
                "AF_WINDOWS_EVIDENCE_V1\n```json\n" + json.dumps(packet) + "\n```\n", encoding="utf-8"
            )
            result = subprocess.run(
                [
                    gh,
                    "pr",
                    "comment",
                    "5",
                    "--repo",
                    "Etoileint/AstroFairy",
                    "--body-file",
                    str(body),
                ],
                check=False,
            )
            if result.returncode:
                sys.stderr.write(f"Stopped at part {index}/{len(chunks)}; earlier comments remain.\n")
                return result.returncode
    sys.stdout.write(f"Sent {len(chunks)} parts; {len(data)} bytes; SHA256 {checksum}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
