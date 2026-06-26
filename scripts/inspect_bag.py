#!/usr/bin/env python3
"""Inspect Intel RealSense .bag recording: streams, intrinsics, frame counts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyrealsense2 as rs


def _stream_names() -> dict:
    names = {}
    for attr in (
        "depth", "color", "infrared", "infrared1", "infrared2",
        "accel", "gyro", "pose", "fisheye1", "fisheye2",
    ):
        if hasattr(rs.stream, attr):
            names[getattr(rs.stream, attr)] = attr
    return names


STREAM_NAMES = _stream_names()


def stream_label(stream_type: rs.stream) -> str:
    return STREAM_NAMES.get(stream_type, str(stream_type))


def intrinsics_to_dict(intr: rs.intrinsics) -> dict:
    return {
        "width": intr.width,
        "height": intr.height,
        "fx": intr.fx,
        "fy": intr.fy,
        "ppx": intr.ppx,
        "ppy": intr.ppy,
        "model": str(intr.model),
        "coeffs": list(intr.coeffs),
        "K": [[intr.fx, 0, intr.ppx], [0, intr.fy, intr.ppy], [0, 0, 1]],
    }


def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def inspect_bag(bag_path: Path, count_frames: bool, max_frames: int | None) -> dict:
    if not bag_path.is_file():
        raise FileNotFoundError(bag_path)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_device_from_file(str(bag_path), repeat_playback=False)

    profile = pipeline.start(config)
    device = profile.get_device()
    playback = device.as_playback()
    playback.set_real_time(False)

    duration_raw = playback.get_duration()
    if hasattr(duration_raw, "total_seconds"):
        duration_sec = duration_raw.total_seconds()
    else:
        duration_sec = float(duration_raw) / 1e9 if duration_raw else 0.0

    report: dict = {
        "file": str(bag_path.resolve()),
        "file_size": format_bytes(bag_path.stat().st_size),
        "duration_sec": round(float(duration_sec), 3),
        "device": {},
        "streams": [],
        "frame_counts": {},
    }

    for key in (
        rs.camera_info.name,
        rs.camera_info.serial_number,
        rs.camera_info.firmware_version,
        rs.camera_info.product_id,
        rs.camera_info.usb_type_descriptor,
    ):
        try:
            report["device"][str(key)] = device.get_info(key)
        except Exception:
            pass

    streams = profile.get_streams()
    for s in streams:
        entry = {
            "stream": stream_label(s.stream_type()),
            "format": str(s.format()),
            "fps": s.fps(),
        }
        if s.is_video_stream_profile():
            vsp = s.as_video_stream_profile()
            entry["width"] = vsp.width()
            entry["height"] = vsp.height()
            try:
                entry["intrinsics"] = intrinsics_to_dict(vsp.get_intrinsics())
            except Exception:
                pass
        report["streams"].append(entry)

    if count_frames:
        stream_types = [s.stream_type() for s in streams]
        counts: dict[str, int] = {stream_label(st): 0 for st in stream_types}
        n = 0
        while True:
            try:
                frames = pipeline.wait_for_frames(timeout_ms=10000)
            except RuntimeError:
                break
            for st in stream_types:
                f = frames.first_or_default(st)
                if f:
                    counts[stream_label(st)] += 1
            n += 1
            if max_frames and n >= max_frames:
                break
        report["frame_counts"] = counts
        report["frames_polled"] = n

    pipeline.stop()
    return report


def print_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print("=" * 60)
    print("RealSense bag inspection")
    print("=" * 60)
    print(f"File      : {report['file']}")
    print(f"Size      : {report['file_size']}")
    print(f"Duration  : {report['duration_sec']} s")
    print()
    print("Device:")
    for k, v in report.get("device", {}).items():
        print(f"  {k}: {v}")
    print()
    print(f"Streams ({len(report['streams'])}):")
    for i, s in enumerate(report["streams"], 1):
        print(f"  [{i}] {s['stream']}")
        print(f"      format: {s['format']}, fps: {s['fps']}", end="")
        if "width" in s:
            print(f", size: {s['width']}x{s['height']}")
        else:
            print()
        if "intrinsics" in s:
            intr = s["intrinsics"]
            print(f"      K: fx={intr['fx']:.3f} fy={intr['fy']:.3f} "
                  f"cx={intr['ppx']:.3f} cy={intr['ppy']:.3f}")
    if report.get("frame_counts"):
        print()
        print("Frame counts (playback scan):")
        for name, cnt in report["frame_counts"].items():
            print(f"  {name}: {cnt}")
        if "frames_polled" in report:
            print(f"  (polled {report['frames_polled']} composite frame sets)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect RealSense .bag file contents")
    parser.add_argument(
        "bag",
        nargs="?",
        default="data/20260530_151155.bag",
        help="Path to .bag file",
    )
    parser.add_argument(
        "--count-frames",
        action="store_true",
        help="Scan entire bag and count frames per stream (slower)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Stop frame scan after N polls (for quick test)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    bag_path = Path(args.bag)
    try:
        report = inspect_bag(bag_path, args.count_frames, args.max_frames)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print_report(report, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
