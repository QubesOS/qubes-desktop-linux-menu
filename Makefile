default: help

help:
	@echo "Use setup.py to build"
	@echo "Extra make targets available:"
	@echo " install-autostart - install autostart files (xdg)"
	@echo " install-icons - install icons"
	@echo " install - calls all of the above (but calling setup.py is still necessary)"

install-icons:
	mkdir -p $(DESTDIR)/usr/share/icons/hicolor/scalable/apps
	cp icons/qappmenu-dispvm-child.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-dispvm-child.svg
	cp icons/qappmenu-favorites.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-favorites.svg
	cp icons/qappmenu-favorites-blue.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-favorites-blue.svg
	cp icons/qappmenu-grab-handle.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-grab-handle.svg
	cp icons/qappmenu-networking-no.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-networking-no.svg
	cp icons/qappmenu-networking-vpn.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-networking-vpn.svg
	cp icons/qappmenu-networking-yes.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-networking-yes.svg
	cp icons/qappmenu-power.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-power.svg
	cp icons/qappmenu-qube.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-qube.svg
	cp icons/qappmenu-settings.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-settings.svg
	cp icons/qappmenu-bookmark-black.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-black.svg
	cp icons/qappmenu-bookmark-white.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-white.svg
	cp icons/qappmenu-bookmark-fill-black.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-fill-black.svg
	cp icons/qappmenu-bookmark-fill-white.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-fill-white.svg
	cp icons/qappmenu-list-white.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-list-white.svg
	cp icons/qappmenu-list-black.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-list-black.svg
	cp icons/qappmenu-grid-white.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-grid-white.svg
	cp icons/qappmenu-grid-black.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-grid-black.svg
	cp icons/qappmenu-sun-black.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-sun-black.svg
	cp icons/qappmenu-sun-white.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-sun-white.svg
	cp icons/qappmenu-moon-black.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-moon-black.svg

install-autostart:
	mkdir -p $(DESTDIR)/etc/xdg/autostart
	cp autostart/qubes-app-menu.desktop $(DESTDIR)/etc/xdg/autostart
	mkdir -p $(DESTDIR)/usr/share/applications
	cp desktop_files/open-qubes-app-menu.desktop $(DESTDIR)/usr/share/applications/

install-settings:
	cp qubes_menu/qappmenu-settings.ini $(HOME)/.config/qappmenu-settings.ini

install: install-autostart install-icons install-settings

.PHONY: clean
clean:
