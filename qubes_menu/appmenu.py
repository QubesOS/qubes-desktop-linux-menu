#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Application Menu class and helpers.
"""
# pylint: disable=import-error
import asyncio
import subprocess
import sys
from typing import Optional
from contextlib import suppress
import pkg_resources
import logging

import qubesadmin
import qubesadmin.events

from .settings_page import SettingsPage
from .application_page import AppPage
from .desktop_file_manager import DesktopFileManager
from .favorites_page import FavoritesPage
from .custom_widgets import SelfAwareMenu
from .vm_manager import VMManager
from . import constants

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio

import gbulb
gbulb.install()


logger = logging.getLogger('qubes-appmenu')


class AppMenu(Gtk.Application):
    """
    Main Gtk.Application for appmenu.
    """
    def __init__(self, qapp, dispatcher):
        """
        :param qapp: qubesadmin.Qubes object
        :param dispatcher: qubesadmin.vm.EventsDispatcher
        """
        super().__init__(application_id='org.qubesos.appmenu',
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,)
        self.qapp = qapp
        self.dispatcher = dispatcher
        self.primary = False
        self.keep_visible = False
        self.restart = False
        self.initial_page = 0
        self.start_in_background = False

        self._add_cli_options()

        self.builder: Optional[Gtk.Builder] = None
        self.main_window: Optional[Gtk.Window] = None
        self.main_notebook: Optional[Gtk.Notebook] = None

        self.fav_app_list: Optional[Gtk.ListBox] = None
        self.sys_tools_list: Optional[Gtk.ListBox] = None

        self.desktop_file_manager: Optional[DesktopFileManager] = None
        self.vm_manager: Optional[VMManager] = None
        self.app_page: Optional[AppPage] = None

        self.favorites_page: Optional[FavoritesPage] = None
        self.settings_page: Optional[SettingsPage] = None

        self.power_button: Optional[Gtk.Button] = None
        self.tasks = []

    def _add_cli_options(self):
        self.add_main_option(
            "keep-visible",
            ord("k"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Do not hide the menu after action",
            None,
        )
        self.add_main_option(
            constants.RESTART_PARAM_LONG,
            ord(constants.RESTART_PARAM_SHORT),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Restart the menu if it's running",
            None,
        )

        self.add_main_option(
            'page',
            ord('p'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.INT,
            "Open menu at selected page; 0 is the application page, 1 is the"
            "favorites page and 2 is the system tools page"
        )

        self.add_main_option(
            "background",
            ord("b"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Do not show the menu at start, run in the background; useful "
            "for initial autostart",
            None,
        )

    def do_command_line(self, command_line):
        """
        Handle CLI arguments. This method overrides default do_command_line
        from Gtk.Application (and due to pygtk being dynamically generated
        pylint is confused about its arguments).
        """
        # pylint: disable=arguments-differ
        Gtk.Application.do_command_line(self, command_line)
        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if "keep-visible" in options:
            self.keep_visible = True
        if "restart" in options:
            self.restart = True
        if "page" in options:
            self.initial_page = options['page']
        if "background" in options:
            self.start_in_background = True
        self.activate()
        return 0

    @staticmethod
    def _do_power_button(_widget):
        """
        Run xfce4's default logout button. Possible enhancement would be
        providing our own tiny program.
        """
        subprocess.Popen('xfce4-session-logout', stdin=subprocess.DEVNULL)

    def do_activate(self, *args, **kwargs):
        """
        Method called whenever this program is run; it executes actual setup
        only at true first start, in other cases just presenting the main window
        to user.
        """
        if not self.primary:
            self.perform_setup()
            self.primary = True
            assert self.main_window
            if not self.start_in_background:
                self.main_window.show_all()
            self.initialize_state()
            self.hold()
        else:
            if self.restart:
                self.exit_app()
            if self.main_notebook:
                self.main_notebook.set_current_page(self.initial_page)
            if self.main_window and not self.start_in_background:
                if self.main_window.is_visible() and not self.keep_visible:
                    self.main_window.hide()
                else:
                    self.main_window.present()

    def hide_menu(self):
        """
        Unless CLI options specified differently, the menu will try to hide
        itself. Should be called after all sorts of actions like running an
        app or clicking outside of the menu.
        """
        if not self.keep_visible and self.main_window:
            self.main_window.hide()

    def _key_press(self, _widget, event):
        """
        Keypress handler, to allow closing the menu with an ESC key
        """
        if event.keyval == Gdk.KEY_Escape:
            self.hide_menu()

    def _focus_out(self, _widget, _event: Gdk.EventFocus):
        """
        Hide the menu on focus out, unless a right-click menu is open
        """
        if SelfAwareMenu.OPEN_MENUS <= 0:
            self.hide_menu()

    def initialize_state(self):
        """
        Initial state, that is - menu is open at the 0th page and pages
        will initialize their state if needed. Separate function because
        some things (like widget size adjustments) must be called after
        widgets are realized and not on init.
        """
        if self.main_notebook:
            self.main_notebook.set_current_page(self.initial_page)
        if self.app_page:
            self.app_page.initialize_state(None)

    def perform_setup(self):
        """
        The function that performs actual widget realization and setup. Should
        be only called once, in the main instance of this application.
        """
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_path(pkg_resources.resource_filename(
            __name__, 'qubes-menu-dark.css'))
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.builder = Gtk.Builder()

        self.fav_app_list = self.builder.get_object('fav_app_list')
        self.sys_tools_list = self.builder.get_object('sys_tools_list')
        self.builder.add_from_file(pkg_resources.resource_filename(
            __name__, 'qubes-menu.glade'))
        self.main_window = self.builder.get_object('main_window')
        self.main_notebook = self.builder.get_object('main_notebook')

        self.main_window.set_events(Gdk.EventMask.FOCUS_CHANGE_MASK)
        self.main_window.connect('focus-out-event', self._focus_out)
        self.main_window.connect('key_press_event', self._key_press)
        self.add_window(self.main_window)
        self.desktop_file_manager = DesktopFileManager(self.qapp)
        self.vm_manager = VMManager(self.qapp, self.dispatcher)

        self.app_page = AppPage(self.vm_manager, self.builder,
                                self.desktop_file_manager)
        self.favorites_page = FavoritesPage(self.qapp, self.builder,
                                            self.desktop_file_manager,
                                            self.dispatcher, self.vm_manager)
        self.settings_page = SettingsPage(self.qapp, self.builder,
                                          self.desktop_file_manager,
                                          self.dispatcher)
        self.power_button = self.builder.get_object('power_button')
        self.power_button.connect('clicked', self._do_power_button)
        self.main_notebook.connect('switch-page', self._handle_page_switch)
        self.connect('shutdown', self.do_shutdown)

        self.tasks = [
            asyncio.ensure_future(self.dispatcher.listen_for_events())]

    def _handle_page_switch(self, _widget, _page, page_num):
        """
        On page switch some things need to happen, mostly cleaning any old
        selections/menu options highlighted.
        """
        if page_num == 0 and self.app_page:
            self.app_page.initialize_state()
        elif page_num == 2 and self.settings_page:
            self.settings_page.initialize_state()

    def exit_app(self):
        """
        Exit. Used by restart only at the moment, as the menu is designed to
        keep running in the background.
        """
        self.quit()
        for task in self.tasks:
            with suppress(asyncio.CancelledError):
                task.cancel()


from .tests.mock_app import new_mock_qapp
import os


def main():
    """
    Start the menu app
    """

    qapp = qubesadmin.Qubes()
    if "QUBES_MENU_TEST" in os.environ:
        qapp = new_mock_qapp(qapp)
        qapp.domains[qapp.local_name] = qapp.domains['dom0']
    dispatcher = qubesadmin.events.EventsDispatcher(qapp)
    app = AppMenu(qapp, dispatcher)
    app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
