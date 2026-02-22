.PHONY: usage install uninstall
usage:
	@echo "Usage:"
	@echo "make install    - install zerotier-qt"
	@echo "make uninstall  - uninstall zerotier-qt"

install: main.py
	install -Dm755 main.py $${XDG_BIN_HOME:-$$HOME/.local/bin}/zerotier-qt
	install -Dm644 assets/zerotier-qt.desktop \
	  $${XDG_DATA_HOME:-$$HOME/.local/share}/applications/zerotier-qt.desktop
	install -Dm644 assets/zerotier-qt.svg \
		$${XDG_DATA_HOME:-$$HOME/.local/share}/icons/zerotier-qt.svg
	install -Dm644 assets/zerotier-central-new.png \
		$${XDG_DATA_HOME:-$$HOME/.local/share}/icons/zerotier-central-new.png
	install -Dm644 assets/zerotier-central-old.png \
		$${XDG_DATA_HOME:-$$HOME/.local/share}/icons/zerotier-central-old.png

uninstall:
	rm $${XDG_BIN_HOME:-$$HOME/.local/bin}/zerotier-qt
	rm $${XDG_DATA_HOME:-$$HOME/.local/share}/applications/zerotier-qt.desktop
	rm $${XDG_DATA_HOME:-$$HOME/.local/share}/icons/zerotier-qt.svg
	rm $${XDG_DATA_HOME:-$$HOME/.local/share}/icons/zerotier-central-new.png
	rm $${XDG_DATA_HOME:-$$HOME/.local/share}/icons/zerotier-central-old.png
