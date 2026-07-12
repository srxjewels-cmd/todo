#!/bin/bash
# Double-click me to download images from a website. No terminal knowledge needed.
cd "$(dirname "$0")"

echo "============================================"
echo "  Image Grabber"
echo "============================================"
echo

pause_exit() { echo; read -n 1 -s -r -p "Press any key to close..."; echo; exit "${1:-1}"; }

if [ ! -f imgscraper.py ]; then
    echo "I can't find the tool's files next to me. If you're running this from"
    echo "inside the zip, extract the zip first, open the imgscraper folder,"
    echo "then double-click me again."
    pause_exit 1
fi

# macOS ships a python3 stub; running it pops up the tools installer if needed.
if ! python3 --version >/dev/null 2>&1; then
    echo "macOS is asking to install its command-line tools (they include Python)."
    echo "Click Install in the popup, wait for it to finish, then double-click me again."
    pause_exit 1
fi

# One-time: install the pieces the tool needs.
if ! python3 -c "import requests, bs4, PIL, tqdm" >/dev/null 2>&1; then
    echo "First run — setting things up. This takes a minute or two..."
    python3 -m pip install -q -r requirements.txt 2>/dev/null \
        || python3 -m pip install -q --user -r requirements.txt 2>/dev/null \
        || python3 -m pip install -q --user --break-system-packages -r requirements.txt
fi
if ! python3 -c "import requests, bs4, PIL, tqdm" >/dev/null 2>&1; then
    echo
    echo "Setup hit a problem. Take a screenshot of this window and send it to Claude."
    pause_exit 1
fi

echo
read -r -p "Paste the website address and press Enter: " URL
if [ -z "$URL" ]; then
    echo "No address given — nothing to do."
    pause_exit 1
fi
read -r -p "How many images maximum? Press Enter for no limit: " MAX
EXTRA=()
[ -n "$MAX" ] && EXTRA=(--max-images "$MAX")

echo
python3 imgscraper.py "$URL" "${EXTRA[@]}"

echo
if [ -d images ]; then
    echo "Opening the folder with your images..."
    open images 2>/dev/null
fi
pause_exit 0
