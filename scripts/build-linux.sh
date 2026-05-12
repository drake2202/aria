#!/bin/bash
set -e

echo "Building Aria for Linux..."

# Detect host architecture and map to linuxdeploy naming
HOST_ARCH=$(uname -m)
case "$HOST_ARCH" in
    x86_64)  LD_ARCH="x86_64" ;;
    aarch64) LD_ARCH="aarch64" ;;
    *)
        echo "Unsupported architecture: $HOST_ARCH" >&2
        exit 1
        ;;
esac

echo "Architecture: $HOST_ARCH (linuxdeploy suffix: $LD_ARCH)"

# Auto-activate local venv if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Build with PyInstaller
pyinstaller --clean -y aria.spec

echo "Packaging AppImage..."
cd dist

# Download linuxdeploy and appimage plugin for this architecture
LD_BIN="linuxdeploy-${LD_ARCH}.AppImage"
LD_PLUGIN="linuxdeploy-plugin-appimage-${LD_ARCH}.AppImage"

if [ ! -f "$LD_BIN" ]; then
    wget -c -nv "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/${LD_BIN}"
    chmod +x "$LD_BIN"
fi

if [ ! -f "$LD_PLUGIN" ]; then
    wget -c -nv "https://github.com/linuxdeploy/linuxdeploy-plugin-appimage/releases/download/continuous/${LD_PLUGIN}"
    chmod +x "$LD_PLUGIN"
fi

# Create AppDir structure
APPDIR=Aria.AppDir
rm -rf $APPDIR
mkdir -p $APPDIR/usr/bin $APPDIR/usr/share/applications $APPDIR/usr/share/icons/hicolor/256x256/apps

# Copy pyinstaller output
cp -r aria/* $APPDIR/usr/bin/

# Create desktop file
cat > $APPDIR/usr/share/applications/aria.desktop <<EOF
[Desktop Entry]
Name=Aria
Exec=aria
Icon=aria
Type=Application
Categories=Game;
EOF

# Placeholder icon (you should replace this with a real one later)
touch $APPDIR/usr/share/icons/hicolor/256x256/apps/aria.png

# Build AppImage — output filename includes arch for clarity
export OUTPUT="Aria-Linux-${HOST_ARCH}.AppImage"
./"$LD_BIN" --appdir $APPDIR --plugin appimage --executable $APPDIR/usr/bin/aria

echo "Done! Linux artifact: dist/Aria-Linux-${HOST_ARCH}.AppImage"
