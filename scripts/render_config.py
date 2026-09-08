"""Copy Guardrails configs and interpolate Azure/Foundry env vars into config.yml."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

REQUIRED_VARS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: render_config.py <src_config_dir> <dst_config_dir>")

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))

    replacements = {
        "${AZURE_OPENAI_ENDPOINT}": os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
        "${AZURE_OPENAI_DEPLOYMENT}": os.environ["AZURE_OPENAI_DEPLOYMENT"],
        "${AZURE_OPENAI_API_VERSION}": os.environ["AZURE_OPENAI_API_VERSION"],
    }

    for config_file in dst.rglob("config.yml"):
        text = config_file.read_text(encoding="utf-8")
        for token, value in replacements.items():
            text = text.replace(token, value)
        config_file.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
