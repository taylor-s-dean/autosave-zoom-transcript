#!/usr/bin/env python3
import argparse
import sys
import time
from typing import Optional

try:
    from AppKit import NSWorkspace  # type: ignore

    # NSWorkspace is in AppKit, which is part of Cocoa framework in PyObjC
    from ApplicationServices import (  # type: ignore
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
        AXUIElementPerformAction,
        kAXButtonRole,
        kAXTitleAttribute,
        kAXRoleAttribute,
        kAXChildrenAttribute,
        kAXDescriptionAttribute,
        kAXHelpAttribute,
        kAXPressAction,
        kAXWindowsAttribute,
    )
except ImportError as e:
    print(
        f"[ERROR] PyObjC not installed. Install with: pip install pyobjc-framework-ApplicationServices pyobjc-framework-Cocoa pyobjc-core",
        file=sys.stderr,
    )
    print(f"[ERROR] Import error details: {e}", file=sys.stderr)
    sys.exit(1)


def dbg(message: str, debug: bool):
    """Debug logging helper"""
    if debug:
        print(f"[DBG] {message}")


def get_zoom_process(candidates: list[str], debug: bool) -> Optional[int]:
    """Find the Zoom process by name and return its PID"""
    workspace = NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()

    for candidate in candidates:
        for app in running_apps:
            bundle_id = app.bundleIdentifier()
            localized_name = app.localizedName()

            if bundle_id == candidate or localized_name == candidate:
                pid = app.processIdentifier()
                dbg(f"Found Zoom process: {candidate} (PID: {pid})", debug)
                return pid

    dbg("NO_PROCESS", debug)
    return None


def activate_application(pid: int, debug: bool) -> bool:
    """Activate the application by PID using NSWorkspace"""
    try:
        workspace = NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()

        # Find the app by PID
        for app in running_apps:
            if app.processIdentifier() == pid:
                app.activateWithOptions_(0)  # NSApplicationActivateAllWindows
                time.sleep(0.30)  # Give it time to hydrate
                dbg("Application activated", debug)
                return True

        dbg(f"Failed to find application with PID {pid}", debug)
        return False
    except Exception as e:
        dbg(f"Exception activating application: {e}", debug)
        return False


def get_attribute_value(element, attribute, debug: bool = False):
    """Safely get an attribute value from an AXUIElement"""
    try:
        # PyObjC returns (error_code, value) tuple for output parameters
        result, value = AXUIElementCopyAttributeValue(element, attribute, None)
        if result == 0:  # kAXErrorSuccess
            return value
        return None
    except Exception as e:
        if debug:
            dbg(f"Error getting attribute {attribute}: {e}", debug)
        return None


def get_attribute_string(element, attribute, debug: bool = False) -> str:
    """Get a string attribute value"""
    value = get_attribute_value(element, attribute, debug)
    if value is None:
        return ""
    try:
        # PyObjC automatically converts CFString to Python string
        return str(value)
    except:
        return ""


def get_windows(pid: int, debug: bool) -> list:
    """Get all windows for the application"""
    try:
        app_element = AXUIElementCreateApplication(pid)
        # PyObjC returns (error_code, value) tuple
        result, windows = AXUIElementCopyAttributeValue(
            app_element, kAXWindowsAttribute, None
        )
        if result == 0 and windows:
            # PyObjC may return a list or CFArray - handle both
            if isinstance(windows, list):
                window_list = windows
            else:
                # Convert CFArray to Python list
                window_list = []
                try:
                    count = len(windows) if hasattr(windows, "__len__") else 0
                    for i in range(count):
                        try:
                            window_list.append(windows[i])
                        except:
                            pass
                except:
                    pass
            dbg(f"Found {len(window_list)} windows", debug)
            return window_list
        dbg("No windows found", debug)
        return []
    except Exception as e:
        dbg(f"Error getting windows: {e}", debug)
        return []


def get_window_name(window, debug: bool = False) -> str:
    """Get the name/title of a window"""
    return get_attribute_string(window, kAXTitleAttribute, debug)


def find_scope_window(windows: list, pane: str, debug: bool):
    """Find the appropriate window to search in (prefer Transcript, then Meeting, etc.)"""
    # 1) Prefer undocked Transcript window
    for window in windows:
        name = get_window_name(window, debug)
        if name == pane:
            dbg(f'scope=Transcript window (undocked): "{name}"', debug)
            return window

    # 2) Else "Zoom Meeting"
    for window in windows:
        name = get_window_name(window, debug)
        if "meeting" in name.lower():
            dbg(f'scope=Zoom Meeting window: "{name}"', debug)
            return window

    # 3) Else first named window
    for window in windows:
        name = get_window_name(window, debug)
        if name:
            dbg(f'scope=first named window: "{name}"', debug)
            return window

    # 4) Else last window
    if windows:
        dbg("scope=last window (fallback)", debug)
        return windows[-1]

    return None


def get_all_elements(
    element, debug: bool = False, max_depth: int = 3, current_depth: int = 0
) -> list:
    """Recursively get all UI elements from an element"""
    if current_depth >= max_depth:
        return []

    elements = []
    try:
        # Try to get children - PyObjC returns (error_code, value) tuple
        result, children = AXUIElementCopyAttributeValue(
            element, kAXChildrenAttribute, None
        )
        if result == 0 and children:
            # PyObjC may return a list or CFArray - handle both
            if isinstance(children, list):
                children_list = children
            else:
                # Convert CFArray to Python list
                children_list = []
                try:
                    count = len(children) if hasattr(children, "__len__") else 0
                    for i in range(count):
                        try:
                            children_list.append(children[i])
                        except:
                            pass
                except:
                    pass

            for child in children_list:
                try:
                    elements.append(child)
                    # Recursively get children's children (limited depth)
                    elements.extend(
                        get_all_elements(child, debug, max_depth, current_depth + 1)
                    )
                except:
                    pass
    except Exception as e:
        if debug:
            dbg(f"Error getting children at depth {current_depth}: {e}", debug)

    return elements


def press_element(element, debug: bool) -> bool:
    """Try to press an element using AXPress action"""
    try:
        result = AXUIElementPerformAction(element, kAXPressAction)
        if result == 0:  # kAXErrorSuccess
            return True
        return False
    except Exception as e:
        if debug:
            dbg(f"Error pressing element: {e}", debug)
        return False


def search_and_press(scope_window, needle: str, debug: bool) -> str:
    """Search for a button matching the needle text and press it"""
    try:
        # Get all elements in the window
        dbg("Starting element search...", debug)
        all_elements = [scope_window]
        all_elements.extend(get_all_elements(scope_window, debug, max_depth=3))
        dbg(f"Scanning {len(all_elements)} elements", debug)

        if not all_elements:
            dbg("no elements found in scope", debug)
            return "NOT_FOUND"

        # 1) Match by name/description/help
        needle_lower = needle.lower()
        for elem in all_elements:
            try:
                name = get_attribute_string(elem, kAXTitleAttribute, debug)
                desc = get_attribute_string(elem, kAXDescriptionAttribute, debug)
                help_text = get_attribute_string(elem, kAXHelpAttribute, debug)

                haystack = f"{name}|{desc}|{help_text}".lower()
                if needle_lower in haystack:
                    dbg(
                        f'MATCH label name="{name}" desc="{desc}" help="{help_text}"',
                        debug,
                    )
                    if press_element(elem, debug):
                        dbg("ACTION: press by label -> OK", debug)
                        return "OK_LABEL"
                    dbg("press failed on label match; continuing", debug)
            except Exception as e:
                if debug:
                    dbg(f"Error checking element: {e}", debug)
                continue

        # 2) Fallback: last button
        buttons: list = []
        for elem in all_elements:
            try:
                role = get_attribute_string(elem, kAXRoleAttribute, debug)
                if role.lower() == kAXButtonRole.lower():
                    name = get_attribute_string(elem, kAXTitleAttribute, debug)
                    desc = get_attribute_string(elem, kAXDescriptionAttribute, debug)
                    help_text = get_attribute_string(elem, kAXHelpAttribute, debug)
                    if debug and len(buttons) < 5:
                        dbg(
                            f'button[{len(buttons)}] name="{name}" desc="{desc}" help="{help_text}"',
                            debug,
                        )
                    buttons.append(elem)
            except:
                continue

        dbg(f"AXButtons in scope={len(buttons)}", debug)
        if buttons:
            last_btn = buttons[-1]
            name = get_attribute_string(last_btn, kAXTitleAttribute, debug)
            desc = get_attribute_string(last_btn, kAXDescriptionAttribute, debug)
            help_text = get_attribute_string(last_btn, kAXHelpAttribute, debug)
            dbg(f'lastBtn name="{name}" desc="{desc}" help="{help_text}"', debug)
            if press_element(last_btn, debug):
                dbg("ACTION: press lastBtn -> OK", debug)
                return "OK_FALLBACK"
            return "PRESS_FAILED"

        return "NOT_FOUND"
    except Exception as e:
        dbg(f"searchAndPress failed: {e}", debug)
        return "NOT_FOUND"


def run_accessibility_click(
    text: str,
    pane: str,
    app: Optional[str],
    debug: bool,
    do_act: bool,
    timeout: int = 10,
) -> str:
    """Main function to find and click the button using Accessibility API"""
    candidates = [app] if app else ["zoom.us", "Zoom Workplace"]

    # Find Zoom process
    pid = get_zoom_process(candidates, debug)
    if not pid:
        return "NO_PROCESS"

    # Optionally activate
    if do_act:
        activate_application(pid, debug)
    else:
        dbg("no-focus mode: skipping activate()", debug)

    # Get windows
    windows = get_windows(pid, debug)
    if not windows:
        return "NO_WINDOWS"

    # Log window names
    for i, window in enumerate(windows):
        name = get_window_name(window, debug)
        dbg(f'window[{i}]="{name}"', debug)

    # Find scope window
    scope = find_scope_window(windows, pane, debug)
    if not scope:
        return "NO_SCOPE"

    # Search and press
    status = search_and_press(scope, text.lower(), debug)
    return status


def main():
    ap = argparse.ArgumentParser(
        description="Zoom Transcript autoclicker (no mouse). Prefers background (no focus), falls back to focus."
    )
    ap.add_argument(
        "--text",
        default="save transcript",
        help="Substring to match in name/description/help (case-insensitive). Default: 'save transcript'",
    )
    ap.add_argument(
        "--pane",
        default="Transcript",
        help="Pane/window label to anchor scope. Default: Transcript",
    )
    ap.add_argument(
        "--app",
        default=None,
        help="Override Zoom process name (e.g., 'zoom.us' or 'Zoom Workplace').",
    )
    ap.add_argument(
        "--interval", type=int, default=60, help="Seconds between clicks. Default: 60"
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds for each attempt. Default: 10",
    )
    ap.add_argument("--once", action="store_true", help="Click once then exit.")
    ap.add_argument("--debug", action="store_true", help="Print detailed [DBG] logs.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--background-only",
        action="store_true",
        help="Never focus Zoom; do not fall back to focus.",
    )
    mode.add_argument(
        "--force-focus",
        action="store_true",
        help="Always focus Zoom before scanning; skip background attempt.",
    )
    args = ap.parse_args()

    print(f"[RUN] Python: {sys.executable}")
    print(f"[RUN] Zoom app candidates: {args.app or 'zoom.us, Zoom Workplace'}")
    print(f"[RUN] Target text: {args.text!r} | Pane: {args.pane!r}")
    pref = (
        "background-only"
        if args.background_only
        else (
            "force-focus" if args.force_focus else "auto (background → focus fallback)"
        )
    )
    print(f"[RUN] Mode: {pref} | Interval: {args.interval}s | Debug: {args.debug}")
    print(
        "[NOTE] Ensure Accessibility + Automation permissions for your terminal, Python, System Events, and Zoom."
    )

    def print_result(tag: str, out: str):
        if args.debug:
            print(f"[{tag}] {out}")
            if out:
                print("[STATUS]", out.splitlines()[-1] if "\n" in out else out)
        else:
            status = out.splitlines()[-1] if "\n" in out else out
            print(f"[{tag}] {status or '[NO OUTPUT]'}")

    try:
        while True:
            if args.interval > 0 and not args.once:
                time.sleep(args.interval)

            if args.force_focus:
                # Always focus
                out = run_accessibility_click(
                    args.text,
                    args.pane,
                    args.app,
                    args.debug,
                    do_act=True,
                    timeout=args.timeout,
                )
                print_result("FOCUS", out)

            elif args.background_only:
                # Never focus
                out = run_accessibility_click(
                    args.text,
                    args.pane,
                    args.app,
                    args.debug,
                    do_act=False,
                    timeout=args.timeout,
                )
                print_result("BG", out)

            else:
                # AUTO: try background first, then fallback to focus if needed
                out_bg = run_accessibility_click(
                    args.text,
                    args.pane,
                    args.app,
                    args.debug,
                    do_act=False,
                    timeout=args.timeout,
                )
                status_bg = out_bg.splitlines()[-1] if "\n" in out_bg else out_bg
                if status_bg in ("OK_LABEL", "OK_FALLBACK"):
                    print_result("BG", out_bg)
                else:
                    # Fallback with a quick focus hop
                    out_fg = run_accessibility_click(
                        args.text,
                        args.pane,
                        args.app,
                        args.debug,
                        do_act=True,
                        timeout=args.timeout,
                    )
                    # Print both results so it's clear what happened
                    if args.debug:
                        print_result("BG", out_bg)
                        print_result("FOCUS", out_fg)
                    else:
                        # If focus succeeded, show FOCUS; otherwise show BG status
                        status_fg = (
                            out_fg.splitlines()[-1] if "\n" in out_fg else out_fg
                        )
                        which = (
                            "FOCUS"
                            if status_fg in ("OK_LABEL", "OK_FALLBACK")
                            else "BG"
                        )
                        print_result(which, out_fg if which == "FOCUS" else out_bg)

            if args.once:
                break
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted.")


if __name__ == "__main__":
    main()
