# ZeroTier Qt
A Qt front-end for ZeroTier

A rewrite of https://github.com/tralph3
The icon is from https://github.com/PapirusDevelopmentTeam/papirus-icon-theme

# Features
- List networks
- Get detailed netwok info
- Manage ZeroTier-One service
- Disable/Enable network interfaces
- Join/Leave networks
- See peers and peer paths

# Screenshots
(My IDs and addresses are edited out)
![All Windows](/screenshots/all_windows.png)
![Main Window](/screenshots/main_window.png)
![Peers Window](/screenshots/peers_window.png)
![Context Menu](/screenshots/context_menu.png)

# Dependencies
- systemctl (if someone shows interest, I might make compatability with other inits)
- PySide6
- zerotier-one

# Installation
You can install it from AUR:
```
yay -S zerotier-qt
```

Or, everywhere else, install it with:
```
cd ${TMPDIR:-/tmp}
git clone https://github.com/Damglador/zerotier-qt
cd zerotier-qt
make install
```

AppImage: soon™
