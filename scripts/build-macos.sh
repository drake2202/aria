#!/bin/bash
set -e

echo "Building Aria for macOS..."

# Build with PyInstaller
pyinstaller --clean -y aria.spec

echo "Packaging DMG..."
cd dist

# If create-dmg is installed, use it for a nice DMG, else use hdiutil
if command -v create-dmg &> /dev/null; then
    create-dmg \
      --volname "Aria Launcher" \
      --window-pos 200 120 \
      --window-size 600 400 \
      --icon-size 100 \
      --icon "Aria.app" 150 190 \
      --hide-extension "Aria.app" \
      --app-drop-link 450 190 \
      "Aria-macOS-x64.dmg" \
      "Aria.app"
else
    echo "create-dmg not found, using hdiutil..."
    mkdir -p Aria_dmg
    cp -r Aria.app Aria_dmg/
    ln -s /Applications Aria_dmg/Applications
    hdiutil create -volname "Aria Launcher" -srcfolder Aria_dmg -ov -format UDZO Aria-macOS-x64.dmg
    rm -rf Aria_dmg
fi

echo "Done! macOS artifact: dist/Aria-macOS-x64.dmg"
