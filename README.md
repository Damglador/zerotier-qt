# ZeroTier Qt
A Qt front-end for ZeroTier

A rewrite of https://github.com/tralph3/ZeroTier-GUI

The icon is from https://github.com/PapirusDevelopmentTeam/papirus-icon-theme

# Features
- List networks
- Get detailed netwok info
- Manage ZeroTier-One service
- Disable/Enable network interfaces
- Join/Leave networks
- See peers and peer paths

# Dependencies
- systemctl (if someone shows interest, I might make compatability with other inits)
- PySide6
- zerotier-one

# Installation
You can install it from [AUR](https://aur.archlinux.org/packages/zerotier-qt):
```
yay -S zerotier-qt
```

Get an AppImage: https://github.com/Damglador/zerotier-qt/releases/latest/download/zerotier-qt-x86_64.AppImage

Or install for you user with:
```
cd ${TMPDIR:-/tmp}
git clone https://github.com/Damglador/zerotier-qt
cd zerotier-qt
make install
```

# Screenshots
(My IDs and addresses are edited out)
![All Windows](/screenshots/all_windows.png)
![Main Window](/screenshots/main_window.png)
![Peers Window](/screenshots/peers_window.png)
![Context Menu](/screenshots/context_menu.png)
