#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from typing import Optional

try:
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


# Configuration constants
TEXT = "save transcript"
PANE = "Transcript"
APP = "zoom.us"

# Runtime constants
MAX_ELEMENT_DEPTH = 3
MAX_WINDOW_RETRIES = 3
RETRY_DELAY_BASE = 0.5  # seconds
PGREP_TIMEOUT = 2  # seconds


def dbg(message: str, debug: bool):
    """Debug logging helper"""
    if debug:
        print(f"[DBG] {message}")


def cfarray_to_list(cfarray, debug: bool = False) -> list:
    """Convert a CFArray to a Python list, handling both CFArray and list types."""
    if isinstance(cfarray, list):
        return cfarray
    result = []
    try:
        count = len(cfarray) if hasattr(cfarray, "__len__") else 0
        for i in range(count):
            try:
                result.append(cfarray[i])
            except Exception:
                pass
    except Exception as e:
        if debug:
            dbg(f"Error converting CFArray to list: {e}", debug)
    return result


def get_zoom_process(debug: bool) -> Optional[int]:
    """Find the Zoom process by name and return its PID.

    Uses pgrep to find Zoom processes, which always returns current PIDs.
    This avoids the stale data issue with NSWorkspace.runningApplications().
    """
    try:
        # Find Zoom process using pgrep
        result = subprocess.run(
            ["pgrep", "-x", "zoom.us"],
            capture_output=True,
            text=True,
            timeout=PGREP_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [
                int(pid.strip())
                for pid in result.stdout.strip().split("\n")
                if pid.strip()
            ]
            # Return the first PID found
            if pids:
                pid = pids[0]
                dbg(f"Found Zoom process via pgrep (PID: {pid})", debug)
                return pid
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
        if debug:
            dbg(f"pgrep failed: {e}", debug)

    dbg("NO_PROCESS - Zoom not found", debug)
    return None


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


def get_windows(pid: int, debug: bool, retry_count: int = 0) -> list:
    """Get all windows for the application.

    Note: Creates a fresh AXUIElement from the PID each time.
    If the PID is stale (Zoom restarted), this will fail gracefully.

    Args:
        pid: Process ID
        debug: Enable debug logging
        retry_count: Internal parameter for retry attempts (max 2 retries with delay)
    """
    try:
        app_element = AXUIElementCreateApplication(pid)
        # PyObjC returns (error_code, value) tuple
        result, windows = AXUIElementCopyAttributeValue(
            app_element, kAXWindowsAttribute, None
        )
        # Check for common errors that indicate stale PID
        if result != 0:
            # -25204 = kAXErrorInvalidUIElement, -25205 = kAXErrorCannotComplete
            if result in (-25204, -25205):
                if debug:
                    dbg(
                        f"PID {pid} appears to be stale (Zoom may have restarted): error {result}",
                        debug,
                    )
            return []

        # If no windows and we haven't retried yet, wait a bit and retry
        # (Zoom might be starting up and windows not ready yet, especially after restart)
        if not windows and retry_count < MAX_WINDOW_RETRIES:
            wait_time = RETRY_DELAY_BASE * (retry_count + 1)  # Exponential backoff
            if debug:
                dbg(
                    f"No windows found, retrying in {wait_time}s (attempt {retry_count + 1}/{MAX_WINDOW_RETRIES})...",
                    debug,
                )
            time.sleep(wait_time)
            return get_windows(pid, debug, retry_count + 1)

        if not windows and debug:
            dbg(
                f"No windows found after {retry_count + 1} attempts - Zoom may still be starting or has no windows",
                debug,
            )

        if windows:
            window_list = cfarray_to_list(windows, debug)
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

    # 2) Else "Zoom Meeting" - only search in meeting windows
    for window in windows:
        name = get_window_name(window, debug)
        if name and "meeting" in name.lower():
            dbg(f'scope=Zoom Meeting window: "{name}"', debug)
            return window

    # 3) No meeting window found - return None to avoid searching in wrong windows
    # (e.g., "Share Screen", "Zoom Workplace" home screen, etc.)
    dbg("No meeting or transcript window found - meeting may be closed", debug)
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
            children_list = cfarray_to_list(children, debug)
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
        all_elements.extend(
            get_all_elements(scope_window, debug, max_depth=MAX_ELEMENT_DEPTH)
        )
        dbg(f"Scanning {len(all_elements)} elements", debug)

        if not all_elements:
            dbg("no elements found in scope", debug)
            return "NOT_FOUND"

        # Only match by name/description/help - no fallback to random buttons
        needle_lower = needle.lower()
        for elem in all_elements:
            try:
                name = get_attribute_string(elem, kAXTitleAttribute, debug)
                desc = get_attribute_string(elem, kAXDescriptionAttribute, debug)
                help_text = get_attribute_string(elem, kAXHelpAttribute, debug)

                haystack = f"{name}|{desc}|{help_text}".lower()
                if needle_lower in haystack:
                    # Verify it's actually a button before clicking
                    role = get_attribute_string(elem, kAXRoleAttribute, debug)
                    if role.lower() != kAXButtonRole.lower():
                        if debug:
                            dbg(
                                f'MATCH found but not a button (role="{role}"), skipping',
                                debug,
                            )
                        continue

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

        # No fallback - only click if we find the exact button we're looking for
        dbg(
            "Save transcript button not found - meeting may be closed or transcript unavailable",
            debug,
        )
        return "NOT_FOUND"
    except Exception as e:
        dbg(f"searchAndPress failed: {e}", debug)
        return "NOT_FOUND"


def run_accessibility_click(debug: bool) -> str:
    """Main function to find and click the button using Accessibility API.

    Note: This function gets a fresh Zoom PID on every call, so it handles
    cases where Zoom restarts and gets a new PID between loop iterations.
    Always runs in background mode (does not activate/focus Zoom).
    """
    # Find Zoom process - gets fresh PID on every call
    pid = get_zoom_process(debug)
    if not pid:
        return "NO_PROCESS"

    # Get windows
    windows = get_windows(pid, debug)
    if not windows:
        return "NO_WINDOWS"

    # Log window names
    for i, window in enumerate(windows):
        name = get_window_name(window, debug)
        dbg(f'window[{i}]="{name}"', debug)

    # Find scope window
    scope = find_scope_window(windows, PANE, debug)
    if not scope:
        return "NO_SCOPE"

    # Search and press
    status = search_and_press(scope, TEXT.lower(), debug)
    return status


def main():
    ap = argparse.ArgumentParser(
        description="Zoom Transcript autoclicker. Runs in background mode (no focus required)."
    )
    ap.add_argument(
        "--interval", type=int, default=60, help="Seconds between clicks. Default: 60"
    )
    ap.add_argument("--once", action="store_true", help="Click once then exit.")
    ap.add_argument("--debug", action="store_true", help="Print detailed [DBG] logs.")
    args = ap.parse_args()

    print(f"[RUN] Python: {sys.executable}")
    print(f"[RUN] Zoom app: {APP}")
    print(f"[RUN] Target text: {TEXT!r} | Pane: {PANE!r}")
    print(f"[RUN] Interval: {args.interval}s | Debug: {args.debug}")
    print(
        "[NOTE] Ensure Accessibility + Automation permissions for your terminal, Python, System Events, and Zoom."
    )

    def print_result(out: str):
        """Print result, extracting status line if debug mode."""
        status = out.splitlines()[-1] if "\n" in out else out if out else "[NO OUTPUT]"
        if args.debug:
            print(f"[RESULT] {out}")
            if out:
                print(f"[STATUS] {status}")
        else:
            print(f"[RESULT] {status}")

    try:
        while True:
            if args.interval > 0 and not args.once:
                time.sleep(args.interval)

            out = run_accessibility_click(args.debug)
            print_result(out)

            if args.once:
                break
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted.")


if __name__ == "__main__":
    main()
