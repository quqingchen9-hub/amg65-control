#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DESKTOP="$ROOT/desktop"
VENV="${AMG65_BUILD_VENV:-$DESKTOP/.build-venv}"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet pyinstaller -r "$ROOT/requirements.txt"

cd "$ROOT"
DATA_ARGS=(
  --add-data "$ROOT/panel/static:panel/static"
  --add-data "$ROOT/panel/settings.example.json:panel"
  --add-data "$ROOT/tool/key_pos.json:tool"
  --add-data "$ROOT/tool/agent_hook.sh:tool"
)

if [[ -f "$ROOT/vendor/db/ledlayer_v2.data" ]]; then
  DATA_ARGS+=(--add-data "$ROOT/vendor/db/ledlayer_v2.data:extracted/app/db")
else
  echo "Warning: vendor/db/ledlayer_v2.data not found; official preset effects will be disabled." >&2
fi

"$VENV/bin/python" -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --name amg65-backend \
  --distpath "$DESKTOP/backend/dist" \
  --workpath "$DESKTOP/backend/build" \
  --specpath "$DESKTOP/backend" \
  --paths "$ROOT/panel" \
  --paths "$ROOT/tool" \
  "${DATA_ARGS[@]}" \
  --hidden-import hid \
  --hidden-import usb.backend.libusb1 \
  --hidden-import usb.backend.openusb \
  --hidden-import psutil \
  "$DESKTOP/backend_entry.py"

echo "Backend built: $DESKTOP/backend/dist/amg65-backend"
