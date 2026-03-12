#!/usr/bin/env python3
"""Export normalized clean debug asset artifacts for the shared public packer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
PATH_SPLIT_RE = re.compile(r"[./\\]+")


def load_export_module():
    module_path = SCRIPT_DIR / "export_from_aseprite.py"
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_ROOT.name.replace('-', '_')}_clean_export",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load export module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


exporter = load_export_module()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def animation_rel_stem(animation_id: str) -> Path:
    parts = [piece.strip() for piece in PATH_SPLIT_RE.split(animation_id) if piece.strip()]
    if not parts:
        raise RuntimeError(f'Invalid animation id "{animation_id}"')
    if any(piece in {".", ".."} for piece in parts):
        raise RuntimeError(f'Animation id cannot contain traversal segments: "{animation_id}"')
    return Path(*parts)


def frame_relative_path(animation_id: str, frame_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.@#-]+", "_", frame_name)
    return (Path("frames") / animation_rel_stem(animation_id) / f"{safe_name}.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export package-local clean debug artifacts from grouped .aseprite sources "
            "for the shared public asset packer."
        ),
    )
    parser.add_argument(
        "--aseprite-root",
        default=exporter.package_relative("./aseprite"),
        help="Directory containing grouped .aseprite sources.",
    )
    parser.add_argument(
        "--clean-root",
        default=exporter.package_relative("./build/public-source"),
        help="Output root for normalized clean artifacts.",
    )
    parser.add_argument(
        "--aseprite-bin",
        default=exporter.configured_aseprite_bin(),
        help=(
            "Aseprite binary name or full path. "
            f'Defaults to ${exporter.ASEPRITE_BIN_ENV_VAR} or "aseprite".'
        ),
    )
    parser.add_argument(
        "--extract-script",
        default=exporter.package_relative("./pipeline/extract_group_frames.lua"),
        help="Lua extraction script path.",
    )
    parser.add_argument(
        "--source-layout",
        choices=sorted(exporter.SOURCE_LAYOUT_SLOT_TO_CASE.keys()),
        default="blob",
        help="Case ordering in source 4x4 sheets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and validate without writing destination outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    aseprite_root = Path(args.aseprite_root).resolve()
    clean_root = Path(args.clean_root).resolve()
    extract_script = Path(args.extract_script).resolve()

    if not aseprite_root.exists():
        raise RuntimeError(f"Aseprite root does not exist: {aseprite_root}")
    if not extract_script.exists():
        raise RuntimeError(f"Extraction script does not exist: {extract_script}")

    slot_to_case = exporter.resolve_slot_to_case(args.source_layout)
    aseprite_bin = exporter.resolve_aseprite_binary(args.aseprite_bin)
    grouped_sources = exporter.discover_grouped_sources(aseprite_root)
    category_by_atlas_key = {
        atlas_key: category for category, atlas_key in exporter.CATEGORY_ATLAS_KEY.items()
    }

    with tempfile.TemporaryDirectory(prefix="debug-clean-export-") as temp_dir:
        temp_root = Path(temp_dir)
        frames_by_category, animations, previews, _ = exporter.build_extracted_frames(
            aseprite_root=aseprite_root,
            grouped_sources=grouped_sources,
            aseprite_bin=aseprite_bin,
            extract_script=extract_script,
            temp_root=temp_root,
            slot_to_case=slot_to_case,
        )

        atlas_frames: OrderedDict[str, dict[str, Any]] = OrderedDict()
        animation_rows: OrderedDict[str, dict[str, Any]] = OrderedDict()

        if not args.dry_run:
            shutil.rmtree(clean_root, ignore_errors=True)
            (clean_root / "frames").mkdir(parents=True, exist_ok=True)

        for category in exporter.CATEGORY_ORDER:
            for frame in sorted(frames_by_category[category], key=lambda item: item.frame_name):
                relative_path = frame_relative_path(frame.animation_id, frame.frame_name)
                destination_path = clean_root / relative_path
                if not args.dry_run:
                    destination_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(frame.source_png, destination_path)

                atlas_frames[frame.frame_name] = {
                    "atlasKey": frame.atlas_key,
                    "path": relative_path.as_posix(),
                    "size": {"w": frame.width, "h": frame.height},
                    "durationMs": frame.duration_ms,
                    "animationId": frame.animation_id,
                    "category": category,
                }

        for animation_id in sorted(animations.keys()):
            animation = animations[animation_id]
            category = category_by_atlas_key.get(animation.atlas_key)
            preview = previews[animation_id]
            frame_size: dict[str, int] | None = None
            if animation.frame_names:
                first_frame = atlas_frames.get(animation.frame_names[0])
                if first_frame:
                    frame_size = dict(first_frame["size"])
            animation_rows[animation_id] = {
                "atlasKey": animation.atlas_key,
                "frames": list(animation.frame_names),
                "phaseDurationsMs": list(preview.durations_ms),
                "frameCount": len(animation.frame_names),
                "sourceLayout": args.source_layout,
            }
            if category:
                animation_rows[animation_id]["category"] = category
            if frame_size is not None:
                animation_rows[animation_id]["frameSize"] = frame_size

        manifest = {
            "schemaVersion": 1,
            "sourcePackage": "@towncord/debug-assets",
            "namespace": exporter.NAMESPACE,
            "outputSlug": exporter.NAMESPACE,
            "packSection": exporter.NAMESPACE,
            "animationManifestKey": "debug.animations",
            "logicalAtlasKeys": [
                exporter.CATEGORY_ATLAS_KEY[category] for category in exporter.CATEGORY_ORDER
            ],
            "atlasFrames": atlas_frames,
            "animations": animation_rows,
        }

        if not args.dry_run:
            write_json(clean_root / "manifest.json", manifest)

    frame_total = sum(len(definition["frames"]) for definition in animation_rows.values())
    print(
        "Clean export summary: "
        f"groups={len(grouped_sources)}, "
        f"animations={len(animation_rows)}, "
        f"frames={frame_total}, "
        f"cleanRoot={clean_root}, "
        f"written={'no' if args.dry_run else 'yes'}"
    )
    if args.dry_run:
        print("Dry run mode: destination outputs were not written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
