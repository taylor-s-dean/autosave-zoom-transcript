#!/bin/bash
# Uninstall LaunchAgent for autosave-zoom-transcript

set -e

PLIST_NAME="dev.makeshift.autosave-zoom-transcript.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
INSTALLED_SCRIPT="$HOME/.local/bin/autosave-zoom-transcript"
LOG_DIR="$HOME/Library/Logs/autosave-zoom-transcript"

echo "Uninstalling autosave-zoom-transcript..."
echo ""

# Unload the LaunchAgent if it's loaded
if [ -f "$PLIST_DEST" ]; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm "$PLIST_DEST"
    echo "✓ Removed LaunchAgent"
else
    echo "⚠ LaunchAgent plist not found"
fi

# Remove installed script
if [ -f "$INSTALLED_SCRIPT" ]; then
    rm "$INSTALLED_SCRIPT"
    echo "✓ Removed script: $INSTALLED_SCRIPT"
else
    echo "⚠ Script not found at $INSTALLED_SCRIPT"
fi

# Optionally remove log directory (ask user or just leave it)
if [ -d "$LOG_DIR" ]; then
    echo "⚠ Log directory still exists: $LOG_DIR"
    echo "  (Remove manually if desired: rm -rf $LOG_DIR)"
fi

echo ""
echo "Uninstallation complete!"

