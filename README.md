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

No external dependencies required - uses only Python standard library modules.

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
- Run in background-only mode (no window focus)
- Check every 10 seconds (configurable in the plist template)
- Log output to `~/Library/Logs/autosave-zoom-transcript/autosave-zoom-transcript.log` and errors to `autosave-zoom-transcript.error.log`

## Manual Usage

Run the script directly:

```bash
python autosave-zoom-transcript.py [options]
```

### Options

- `--text TEXT`: Substring to match in button name/description (default: "save transcript")
- `--pane TEXT`: Pane/window label to anchor scope (default: "Transcript")
- `--app TEXT`: Override Zoom process name (e.g., "zoom.us" or "Zoom Workplace")
- `--interval SECONDS`: Seconds between clicks (default: 60)
- `--once`: Click once then exit
- `--debug`: Print detailed debug logs
- `--background-only`: Never focus Zoom; do not fall back to focus
- `--force-focus`: Always focus Zoom before scanning

### Examples

```bash
# Run once in background mode
python autosave-zoom-transcript.py --once --background-only

# Run with 30-second interval and debug output
python autosave-zoom-transcript.py --interval 30 --debug

# Force focus mode (useful for troubleshooting)
python autosave-zoom-transcript.py --force-focus --debug
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
- Background mode is preferred to avoid interrupting your workflow
- The script will automatically fall back to focus mode if background mode fails (unless `--background-only` is used)

