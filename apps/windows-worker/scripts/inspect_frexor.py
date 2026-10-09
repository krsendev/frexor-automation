"""Print the Frexor UI Automation control tree for discovery on Windows."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default=".*Frexor.*", help="Window title regular expression")
    parser.add_argument("--depth", type=int, default=8)
    parser.add_argument("--process-id", type=int, help="Target a specific process ID")
    parser.add_argument("--handle", type=int, help="Target a specific native window handle")
    parser.add_argument("--output", help="Write the control tree to this text file")
    parser.add_argument(
        "--all-process-windows", action="store_true",
        help="Include dialogs and every visible window owned by the Frexor process",
    )
    parser.add_argument(
        "--list-windows", action="store_true",
        help="List visible top-level UIA windows and exit",
    )
    args = parser.parse_args()
    try:
        from pywinauto import Desktop
    except ImportError:
        print('Install worker dari apps\\windows-worker: py -m pip install -e .')
        return 1
    desktop = Desktop(backend="uia")
    if args.list_windows:
        for index, current in enumerate(desktop.windows(visible_only=True), start=1):
            try:
                info = current.element_info
                print(
                    f"{index:02d}. title={current.window_text()!r} "
                    f"class={info.class_name!r} process_id={current.process_id()} "
                    f"handle={current.handle}"
                )
            except Exception as exc:
                print(f"{index:02d}. unreadable window: {exc}")
        return 0

    if args.handle:
        criteria = {"handle": args.handle}
    else:
        criteria = {"title_re": args.title}
        if args.process_id:
            criteria["process"] = args.process_id
    window = desktop.window(**criteria)
    window.wait("visible", timeout=10)

    def print_tree():
        if args.all_process_windows:
            process_id = window.process_id()
            windows = Desktop(backend="uia").windows(process=process_id, visible_only=True)
        else:
            windows = [window]
        for index, current in enumerate(windows, start=1):
            wrapped = current.wrapper_object() if hasattr(current, "wrapper_object") else current
            print(f"=== WINDOW {index}: {wrapped.window_text()} ===")
            specification = desktop.window(handle=wrapped.handle)
            specification.print_control_identifiers(depth=args.depth)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle, redirect_stdout(handle):
            print_tree()
        print(f"Control tree saved to {output.resolve()}")
    else:
        print_tree()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
