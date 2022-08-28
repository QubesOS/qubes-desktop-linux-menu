default: help

help:
	@echo "Use setup.py to build"
	@echo "Extra make targets available:"
	@echo " install-autostart - install autostart files (xdg)"
	@echo " install-icons - install icons"
	@echo " update-icons - update the icons cashe"
	@echo " install-settings - install the settings.ini file at ~/.config must be run as user not root"
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
	cp icons/qappmenu-services.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-services.svg

update-icons:
	gtk-update-icon-cache $(DESTDIR)/usr/share/icons/hicolor

install-autostart:
	mkdir -p $(DESTDIR)/etc/xdg/autostart
	cp autostart/qubes-app-menu.desktop $(DESTDIR)/etc/xdg/autostart
	mkdir -p $(DESTDIR)/usr/share/applications
	cp desktop_files/open-qubes-app-menu.desktop $(DESTDIR)/usr/share/applications/

install-settings:
ifneq ($(shell id -u), 0)
	mkdir -p $(HOME)/.config/qubes-desktop-linux-menu
	cp qubes_menu/qappmenu-settings.ini $(HOME)/.config/qubes-desktop-linux-menu/qappmenu-settings.ini
else
	@echo "Run the install-settings command as user to install the config at ~/.config folder."
endif

install: install-autostart install-icons update-icons install-settings

.PHONY: clean
clean:
