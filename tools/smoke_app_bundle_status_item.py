from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_NATIVE_EXECUTABLE_HEADERS = {
    b"\xcf\xfa\xed\xfe",  # mach-o 64-bit little endian
    b"\xfe\xed\xfa\xcf",  # mach-o 64-bit big endian
    b"\xca\xfe\xba\xbe",  # universal binary
    b"\xbe\xba\xfe\xca",  # reverse universal binary
    b"\xca\xfe\xba\xbf",  # universal 64-bit binary
    b"\xbf\xba\xfe\xca",  # reverse universal 64-bit binary
}


@dataclass(frozen=True)
class BundleProcessTree:
    parent_pid: int | None
    child_pid: int | None


@dataclass(frozen=True)
class StatusItemGeometry:
    title: str
    description: str
    x: int
    y: int
    width: int
    height: int


def is_native_bundle_executable(executable_path: Path) -> bool:
    header = executable_path.read_bytes()[:4]
    return header in _NATIVE_EXECUTABLE_HEADERS


def find_bundle_processes(*, bundle_path: str, ps_lines: list[str]) -> BundleProcessTree:
    app_name = Path(bundle_path).stem
    parent_marker = f"{bundle_path}/Contents/MacOS/{app_name}"
    child_marker = f"{bundle_path}/Contents/Resources/.venv/bin/python -m gaze"
    parsed = [_parse_ps_line(line) for line in ps_lines]
    parent_pid = next((pid for pid, _ppid, args in parsed if args.startswith(parent_marker)), None)
    child_pid = next(
        (
            pid
            for pid, ppid, args in parsed
            if args.startswith(child_marker) and (parent_pid is None or ppid == parent_pid)
        ),
        None,
    )
    return BundleProcessTree(parent_pid=parent_pid, child_pid=child_pid)


def status_item_is_visible_in_menu_bar(geometry: StatusItemGeometry) -> bool:
    return geometry.x >= 0 and 0 <= geometry.y <= 80 and geometry.width > 0 and geometry.height > 0


def parse_status_item_geometry(output: str) -> StatusItemGeometry | None:
    for line in output.splitlines():
        if not line.startswith("item "):
            continue
        fields = _parse_key_value_fields(line.removeprefix("item "))
        try:
            return StatusItemGeometry(
                title=fields.get("title", ""),
                description=fields.get("desc", ""),
                x=int(fields["x"]),
                y=int(fields["y"]),
                width=int(fields["w"]),
                height=int(fields["h"]),
            )
        except (KeyError, ValueError):
            return None
    return None


def run_smoke(app_path: Path, *, wait_seconds: float = 20.0) -> int:
    executable = app_path / "Contents" / "MacOS" / app_path.stem
    print(f"native_executable={str(is_native_bundle_executable(executable)).lower()}")
    if not is_native_bundle_executable(executable):
        print("status=failed")
        print("reason=non_native_bundle_executable")
        return 1

    subprocess.run(["open", "-n", "-g", str(app_path)], check=True)
    deadline = time.monotonic() + wait_seconds
    process_tree = BundleProcessTree(parent_pid=None, child_pid=None)
    while time.monotonic() < deadline:
        process_tree = find_bundle_processes(
            bundle_path=str(app_path),
            ps_lines=_process_lines(),
        )
        if process_tree.parent_pid is not None and process_tree.child_pid is not None:
            break
        time.sleep(0.25)

    print(f"parent_pid_present={str(process_tree.parent_pid is not None).lower()}")
    print(f"child_pid_present={str(process_tree.child_pid is not None).lower()}")
    if process_tree.child_pid is None:
        print("status=failed")
        print("reason=missing_python_child")
        return 1

    geometry = parse_status_item_geometry(_ax_status_item_output(process_tree.child_pid))
    visible = geometry is not None and status_item_is_visible_in_menu_bar(geometry)
    print(f"status_item_present={str(geometry is not None).lower()}")
    if geometry is not None:
        print(f"status_item_x={geometry.x}")
        print(f"status_item_y={geometry.y}")
        print(f"status_item_width={geometry.width}")
        print(f"status_item_height={geometry.height}")
    print(f"status_item_visible={str(visible).lower()}")

    scene_error_count = _status_scene_error_count(process_tree.child_pid)
    print(f"status_scene_error_count={scene_error_count}")
    if not visible:
        print("status=failed")
        print("reason=status_item_not_visible")
        return 1
    if scene_error_count > 0:
        print("status=failed")
        print("reason=status_scene_errors")
        return 1
    print("status=passed")
    return 0


def _parse_ps_line(line: str) -> tuple[int, int, str]:
    parts = line.strip().split(maxsplit=3)
    if len(parts) < 3:
        return 0, 0, ""
    try:
        pid = int(parts[0])
        ppid = int(parts[1])
    except ValueError:
        return 0, 0, ""
    if len(parts) == 4 and not parts[2].startswith("/"):
        return pid, ppid, parts[3]
    return pid, ppid, " ".join(parts[2:])


def _parse_key_value_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in text.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def _process_lines() -> list[str]:
    result = subprocess.run(
        ["ps", "-axo", "pid,ppid,args"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


def _ax_status_item_output(pid: int) -> str:
    script = f'''
tell application "System Events"
  set out to {{}}
  repeat with p in application processes
    try
      if (unix id of p as text) is "{pid}" then
        repeat with b in menu bars of p
          repeat with mbi in menu bar items of b
            set ttl to ""
            set desc to ""
            try
              set ttl to title of mbi
            end try
            try
              set desc to description of mbi
            end try
            if ttl contains "Gaze" or desc contains "status" then
              set posPair to position of mbi
              set sizePair to size of mbi
              set itemText to "item title=" & ttl & ",desc=" & desc
              set itemText to itemText & ",x=" & ((item 1 of posPair) as text)
              set itemText to itemText & ",y=" & ((item 2 of posPair) as text)
              set itemText to itemText & ",w=" & ((item 1 of sizePair) as text)
              set itemText to itemText & ",h=" & ((item 2 of sizePair) as text)
              set end of out to itemText
            end if
          end repeat
        end repeat
      end if
    end try
  end repeat
  return out
end tell
'''
    result = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        text=True,
        capture_output=True,
        timeout=20,
    )
    return result.stdout


def _status_scene_error_count(pid: int) -> int:
    result = subprocess.run(
        [
            "log",
            "show",
            "--style",
            "compact",
            "--last",
            "30s",
            "--predicate",
            f'processID == {pid} AND eventMessage CONTAINS[c] "NSStatusItemView"',
        ],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    return sum(
        1
        for line in result.stdout.splitlines()
        if "Error creating" in line or "Code=3" in line or "failed" in line
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test Gaze local app status item visibility."
    )
    parser.add_argument("app_path", nargs="?", default="dist/Gaze.app")
    parser.add_argument("--wait-seconds", type=float, default=20.0)
    args = parser.parse_args(argv)
    return run_smoke(Path(args.app_path).resolve(), wait_seconds=args.wait_seconds)


if __name__ == "__main__":
    sys.exit(main())
