#!/bin/bash
set -e

echo "Building Aria for Linux..."

# Auto-activate local venv if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Build with PyInstaller
pyinstaller --clean -y aria.spec

echo "Packaging AppImage..."
cd dist

# Download linuxdeploy and appimage plugin
if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget -c -nv "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
    chmod +x linuxdeploy-x86_64.AppImage
fi

if [ ! -f linuxdeploy-plugin-appimage-x86_64.AppImage ]; then
    wget -c -nv "https://github.com/linuxdeploy/linuxdeploy-plugin-appimage/releases/download/continuous/linuxdeploy-plugin-appimage-x86_64.AppImage"
    chmod +x linuxdeploy-plugin-appimage-x86_64.AppImage
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

# Build AppImage
export OUTPUT=Aria-Linux-x86_64.AppImage
./linuxdeploy-x86_64.AppImage --appdir $APPDIR --plugin appimage --executable $APPDIR/usr/bin/aria

echo "Done! Linux artifact: dist/Aria-Linux-x86_64.AppImage"
