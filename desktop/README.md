# AMG65 Control Desktop

The macOS desktop shell wraps the shared Python backend in Electron and adds
the React console, menu-bar controls, and login-item support.

![Desktop overview](../docs/assets/overview.png)

## Development

```bash
cd desktop
npm install
npm run dev
```

`npm run dev` starts Vite and Electron. Electron launches
`../panel/server.py` when no compatible service is already listening on port
8655.

If your Python executable is not `python3`:

```bash
AMG65_PYTHON=/path/to/python3 npm run dev
```

## Build

```bash
npm run build:backend   # PyInstaller backend in backend/dist
npm run build:app       # .app in dist
npm run dist            # .dmg in dist
```

`build:backend` creates `desktop/.build-venv` and installs
`../requirements.txt`. The current Electron Builder configuration targets
Apple Silicon (`arm64`). The build is ad-hoc signed, not notarized.

## Runtime behavior

- Closing the window hides the app; it remains available from the menu bar.
- The backend log is written to
  `~/Library/Application Support/AMG65 Control/backend.log`.
- User settings are stored in
  `~/Library/Application Support/AMG65 Control/settings.json`.
- The app reuses an existing compatible backend on `127.0.0.1:8655`.

## Structure

```text
desktop/
├── electron/               main process and preload bridge
├── src/                    React + TypeScript UI
├── public/                 static UI assets
├── build/                  app and menu-bar icons
├── scripts/                asset and backend build scripts
└── backend_entry.py        PyInstaller entry point
```

The vendor preset database is optional. Set `AMG65_PRESET_DB` to a local
`ledlayer_v2.data` copy to enable the official preset effects.
