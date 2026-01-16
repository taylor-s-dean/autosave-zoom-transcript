# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A macOS utility that automatically saves Zoom transcripts by clicking the "Save transcript" button at configurable intervals using the Accessibility API. Runs in background mode without requiring window focus.

## Commands

### Setup
```bash
pip install -r requirements.txt
```

### Run manually
```bash
python autosave-zoom-transcript.py                    # Default 60s interval
python autosave-zoom-transcript.py --once             # Single execution
python autosave-zoom-transcript.py --interval 30 --debug  # Custom interval with debug logging
```

### LaunchAgent (background service)
```bash
./install-launchagent.sh    # Install and start
./uninstall-launchagent.sh  # Stop and remove

# Check status
launchctl list | grep autosave-zoom-transcript

# View logs
tail -f ~/Library/Logs/autosave-zoom-transcript/autosave-zoom-transcript.log
```

## Architecture

Single Python script (`autosave-zoom-transcript.py`) using PyObjC to access macOS Accessibility API:

1. **Process discovery**: Uses `pgrep` to find Zoom PID (avoids stale data from NSWorkspace)
2. **Window hierarchy**: Creates AXUIElement from PID, gets windows via `kAXWindowsAttribute`
3. **Window scoping**: Prioritizes undocked "Transcript" window, then "Zoom Meeting" windows
4. **Element search**: Recursively traverses UI elements (max depth 3) looking for button matching "save transcript"
5. **Action execution**: Calls `AXUIElementPerformAction` with `kAXPressAction` on matched button

Key configuration constants at top of script:
- `TEXT = "save transcript"` - Button text to match
- `PANE = "Transcript"` - Window name to prioritize
- `APP = "zoom.us"` - Process name

## Requirements

- Python 3.13.4 (via pyenv, see `.python-version`)
- macOS with Accessibility permissions granted to terminal, Python, System Events, and Zoom
