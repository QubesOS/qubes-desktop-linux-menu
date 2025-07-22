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
	cp icons/qappmenu-search.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-search.svg
	cp icons/qappmenu-settings.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-settings.svg
	cp icons/appmenu-settings-program-icon.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/appmenu-settings-program-icon.svg
	cp icons/qappmenu-pause.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-pause.svg
	cp icons/qappmenu-start.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-start.svg
	cp icons/qappmenu-shutdown.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-shutdown.svg
	cp icons/qappmenu-top-left.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-top-left.svg
	cp icons/qappmenu-top-right.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-top-right.svg
	cp icons/qappmenu-bottom-left.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-bottom-left.svg
	cp icons/qappmenu-bottom-right.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-bottom-right.svg
	cp icons/qappmenu-az.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-az.svg
	cp icons/qappmenu-za.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-za.svg
	cp icons/qappmenu-qube-az.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-qube-az.svg
	cp icons/qappmenu-qube-za.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qappmenu-qube-za.svg
	cp icons/settings-*.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/

install-autostart:
	mkdir -p $(DESTDIR)/etc/xdg/autostart
	cp autostart/qubes-app-menu.desktop $(DESTDIR)/etc/xdg/autostart
	mkdir -p $(DESTDIR)/usr/share/applications
	cp desktop_files/open-qubes-app-menu.desktop $(DESTDIR)/usr/share/applications/
	cp desktop_files/qubes-appmenu-settings.desktop $(DESTDIR)/usr/share/applications/
	mkdir -p $(DESTDIR)/lib/systemd/user/
	cp service_files/qubes-app-menu.service $(DESTDIR)/lib/systemd/user/
	mkdir -p $(DESTDIR)/usr/share/dbus-1/services/
	cp service_files/dbus-qubes-app-menu.service $(DESTDIR)/usr/share/dbus-1/services/

install: install-autostart install-icons

.PHONY: clean
clean:
