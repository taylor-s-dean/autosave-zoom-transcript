#!/bin/bash
# Install LaunchAgent for autosave-zoom-transcript

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="dev.makeshift.autosave-zoom-transcript.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

# Installation paths
BIN_DIR="$HOME/.local/bin"
INSTALLED_SCRIPT="$BIN_DIR/autosave-zoom-transcript"
LOG_DIR="$HOME/Library/Logs/autosave-zoom-transcript"

echo "Installing autosave-zoom-transcript..."
echo ""

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"
echo "✓ Created/verified $BIN_DIR"

# Copy script to bin directory
cp "$SCRIPT_DIR/autosave-zoom-transcript.py" "$INSTALLED_SCRIPT"
chmod +x "$INSTALLED_SCRIPT"
echo "✓ Installed script to $INSTALLED_SCRIPT"

# Create log directory
mkdir -p "$LOG_DIR"
echo "✓ Created log directory: $LOG_DIR"

# Get Python path
PYTHON_PATH="$(pyenv which python 2>/dev/null || which python3)"
if [ -z "$PYTHON_PATH" ]; then
    echo "Error: Could not find Python interpreter" >&2
    exit 1
fi
echo "✓ Using Python: $PYTHON_PATH"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Generate plist with correct paths
sed -e "s|__PYTHON_PATH__|$PYTHON_PATH|g" \
    -e "s|__SCRIPT_PATH__|$INSTALLED_SCRIPT|g" \
    -e "s|__LOG_DIR__|$LOG_DIR|g" \
    "$PLIST_SOURCE" > "$PLIST_DEST"

echo "✓ Generated LaunchAgent plist"

# Unload existing agent if present
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the LaunchAgent
launchctl load "$PLIST_DEST"
echo "✓ LaunchAgent loaded"

echo ""
echo "Installation complete!"
echo ""
echo "Script location: $INSTALLED_SCRIPT"
echo "Logs location: $LOG_DIR/"
echo ""
echo "To check status: launchctl list | grep autosave-zoom-transcript"
echo "To view logs: tail -f $LOG_DIR/autosave-zoom-transcript.log"
echo "To unload: launchctl unload $PLIST_DEST"
echo "To reload: launchctl unload $PLIST_DEST && launchctl load $PLIST_DEST"

