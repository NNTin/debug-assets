from __future__ import annotations

import os
import shutil
from pathlib import Path


ASEPRITE_BIN_ENV_VAR = "ASEPRITE_BIN"


def configured_aseprite_bin(default: str = "aseprite") -> str:
    configured = os.environ.get(ASEPRITE_BIN_ENV_VAR, "").strip()
    if configured:
        return configured
    return default


def resolve_aseprite_binary(preferred: str) -> str:
    candidate = preferred.strip()
    if not candidate:
        raise RuntimeError(
            f"Aseprite binary is not configured. Pass --aseprite-bin or set "
            f"{ASEPRITE_BIN_ENV_VAR}."
        )

    resolved = shutil.which(candidate)
    if resolved:
        return resolved

    candidate_path = Path(candidate).expanduser()
    if candidate_path.exists() and candidate_path.is_file():
        return str(candidate_path.resolve())

    raise RuntimeError(
        f'Could not resolve Aseprite binary from "{candidate}". '
        f"Pass --aseprite-bin or set {ASEPRITE_BIN_ENV_VAR} to a full path."
    )
