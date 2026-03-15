#!/bin/sh
set -eux

ARCH="$(uname -m)"
SHARUN="https://raw.githubusercontent.com/pkgforge-dev/Anylinux-AppImages/refs/heads/main/useful-tools/quick-sharun.sh"

APP_NAME=zerotier-qt

# Configure the AppImage
export ICON=/usr/share/icons/hicolor/scalable/apps/$APP_NAME.svg
export DESKTOP=/usr/share/applications/$APP_NAME.desktop
export OUTPATH=./dist
export OUTNAME=$APP_NAME-"$ARCH".AppImage

# sharun options
export DEPLOY_SYS_PYTHON=1

sudo pacman -S --needed --noconfirm git base-devel zsync
sudo pacman -S --needed --noconfirm breeze
if [ ! -d zerotier-qt ]; then
  git clone https://aur.archlinux.org/zerotier-qt.git
  cd zerotier-qt
else
  cd zerotier-qt
  git pull
fi
makepkg -Cfsi --noconfirm
cd ..

# Download and run quick-sharun
wget "$SHARUN" -O ./quick-sharun
chmod +x ./quick-sharun

# Bundle the application
./quick-sharun /usr/bin/$APP_NAME

# My tweaks
for item in /usr/lib/python3.14/*; do
  [ "$(basename "$item")" = "site-packages" ] && continue
  cp -r "$item" ./AppDir/lib/python3.14/
done

cp -r /usr/lib/python3.14/site-packages/shiboken6  ./AppDir/lib/python3.14/site-packages/
cp -r /usr/lib/python3.14/site-packages/PySide6    ./AppDir/lib/python3.14/site-packages/
rm -r ./AppDir/lib/systemd/

install -D /usr/share/pixmaps/zerotier-central-new.png \
  ./AppDir/share/pixmaps/zerotier-central-new.png
install -D /usr/share/pixmaps/zerotier-central-old.png \
  ./AppDir/share/pixmaps/zerotier-central-old.png

# Create the AppImage
./quick-sharun --make-appimage
