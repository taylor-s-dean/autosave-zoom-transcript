# Autosave Zoom Transcript

Automatically saves Zoom transcripts by clicking the "Save transcript" button at regular intervals.

## Features

- Runs in background mode (no window focus required)
- Configurable interval between save attempts
- Automatic fallback to focus mode if background fails
- Minimal CPU usage with sleep intervals

## Setup

### Python Environment

This project uses Python 3.13.4 via pyenv. The `.python-version` file ensures the correct version is used.

### Dependencies

Install PyObjC frameworks:
```bash
pip install -r requirements.txt
```

This installs:
- `pyobjc-framework-ApplicationServices` - For Accessibility API
- `pyobjc-framework-Cocoa` - For AppKit (NSWorkspace)
- `pyobjc-core` - Core PyObjC functionality

## Running as a LaunchAgent (Recommended)

To run the script continuously in the background with minimal CPU overhead:

1. **Install the LaunchAgent:**
   ```bash
   ./install-launchagent.sh
   ```

2. **Check status:**
   ```bash
   launchctl list | grep autosave-zoom-transcript
   ```

3. **View logs:**
   ```bash
   tail -f ~/Library/Logs/autosave-zoom-transcript/autosave-zoom-transcript.log
   ```

4. **Uninstall the LaunchAgent:**
   ```bash
   ./uninstall-launchagent.sh
   ```

The installation process will:
- Install the script to `~/.local/bin/autosave-zoom-transcript` (standard location for user scripts)
- Create log directory at `~/Library/Logs/autosave-zoom-transcript/`
- Automatically detect and use the correct Python interpreter (from pyenv if available)
- Generate and install the LaunchAgent plist with correct paths

The LaunchAgent is configured to:
- Start automatically on login
- Restart automatically if it crashes
- Run in background mode (no window focus required)
- Check every 10 seconds (configurable in the plist template)
- Log output to `~/Library/Logs/autosave-zoom-transcript/autosave-zoom-transcript.log` and errors to `autosave-zoom-transcript.error.log`

## Manual Usage

Run the script directly:

```bash
python autosave-zoom-transcript.py [options]
```

### Options

- `--interval SECONDS`: Seconds between clicks (default: 60)
- `--once`: Click once then exit
- `--debug`: Print detailed debug logs

### Configuration

The script uses global constants at the top of the file for configuration:
- `TEXT = "save transcript"` - Button text to search for
- `PANE = "Transcript"` - Window/pane name to search in
- `APP = "zoom.us"` - Zoom process name

To change these values, edit the constants in `autosave-zoom-transcript.py`.

### Examples

```bash
# Run once
python autosave-zoom-transcript.py --once

# Run with 30-second interval and debug output
python autosave-zoom-transcript.py --interval 30 --debug

# Run continuously (default 60-second interval)
python autosave-zoom-transcript.py
```

## Permissions

Ensure you have granted Accessibility and Automation permissions to:
- Your terminal application
- Python (the interpreter)
- System Events
- Zoom

You can check/grant these in: **System Settings → Privacy & Security → Accessibility** and **Automation**

## Notes

- The script uses macOS Accessibility features to interact with Zoom
- Always runs in background mode (no window focus required)
- Automatically handles Zoom restarts and PID changes
- Only clicks the "Save transcript" button when it's available in an active meeting

