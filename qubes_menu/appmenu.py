#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Application Menu class and helpers.
"""
# pylint: disable=import-error
import asyncio
from pickle import NONE
import subprocess, threading
import sys
from typing import Optional
from contextlib import suppress
import pkg_resources
import logging

import qubesadmin
import qubesadmin.events

from .notebook_pages import NotebookPages
from .utils import load_icon, read_settings, write_settings
from .desktop_file_manager import DesktopFileManager
from .favorites_page import FavoritesPage
from .vm_manager import VMManager
from . import constants

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio

import gbulb
gbulb.install()


logger = logging.getLogger('qubes-appmenu')

SUN_WHITE_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.SUN_WHITE, Gtk.IconSize.DND)
)

SUN_BLACK_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.SUN_BLACK, Gtk.IconSize.DND)
)

MOON_WHITE_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.MOON_WHITE, Gtk.IconSize.DND)
)

MOON_BLACK_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.MOON_BLACK, Gtk.IconSize.DND)
)

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
        
        self.screen: Optional[Gdk.Screen] = None
        self.provider: Optional[Gtk.CssProvider] = None

        self.builder: Optional[Gtk.Builder] = None
        self.main_window: Optional[Gtk.Window] = None
        self.main_notebook: Optional[Gtk.Notebook] = None

        self.desktop_file_manager: Optional[DesktopFileManager] = None
        self.vm_manager: Optional[VMManager] = None

        self.favorites_page: Optional[FavoritesPage] = None
        self.notebook_pages: Optional[NotebookPages] = None

        self.power_button: Optional[Gtk.Button] = None
        self.light_mode_button: Optional[Gtk.Button] = None

        self.light_mode = None

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
                self.main_window.show()
            self.initialize_state()
            self.hold()
        else:
            if self.restart:
                self.exit_app()
            if self.main_notebook:
                self.main_notebook.set_current_page(self.initial_page)
            if self.main_window and self.start_in_background:
                if self.main_window.is_visible() and not self.keep_visible:
                    self.main_window.hide()
                else:
                    self.main_window.present()


    def initialize_state(self):
        """
        Initial state, that is - menu is open at the 0th page and pages
        will initialize their state if needed. Separate function because
        some things (like widget size adjustments) must be called after
        widgets are realized and not on init.
        """
        if self.main_notebook:
            self.main_notebook.set_current_page(self.initial_page)

    def perform_setup(self):
        """
        The function that performs actual widget realization and setup. Should
        be only called once, in the main instance of this application.
        """
        self.screen = Gdk.Screen.get_default()

        self.provider = Gtk.CssProvider()

        self.light_mode = read_settings(constants.LIGHT_MODE)

        if self.light_mode == constants.DARK:
            self.provider.load_from_path(
                pkg_resources.resource_filename(__name__, 'qubes-menu-dark.css')
            )
        else:
            self.provider.load_from_path(
                pkg_resources.resource_filename(__name__, 'qubes-menu-light.css')
            )

        Gtk.StyleContext.add_provider_for_screen(
            self.screen, self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.builder = Gtk.Builder()

        self.builder.add_from_file(
            pkg_resources.resource_filename(__name__, 'qubes-menu.glade')
        )


        self.main_window = self.builder.get_object('main_window')
        self.main_notebook = self.builder.get_object('main_notebook')
        self.power_button = self.builder.get_object('power_button')
        self.light_mode_button = self.builder.get_object('light_mode_toggle')

        self.light_mode_button.connect('clicked', self._toggle_light_mode)
        self.light_mode_button.connect('enter-notify-event', self._enter_light_mode_button)
        self.light_mode_button.connect('leave-notify-event', self._leave_light_mode_button)

        self.light_mode_button.set_image(SUN_WHITE_ICON)\
            if self.light_mode == constants.DARK\
                 else self.light_mode_button.set_image(MOON_BLACK_ICON)
        
        self.desktop_file_manager = DesktopFileManager(self.qapp)
        
        self.vm_manager = VMManager(self.qapp, self.dispatcher)

        self.notebook_pages = NotebookPages(
            self.vm_manager, self.main_notebook, self.desktop_file_manager, self.dispatcher
        )

        self.favorites_page = FavoritesPage(
            self.qapp, self.builder, self.desktop_file_manager, self.dispatcher, self.vm_manager
        )


        self.add_window(self.main_window)

        self.main_window.set_events(Gdk.EventMask.FOCUS_CHANGE_MASK)
        self.main_window.connect('focus-out-event', self._focus_out)
        self.main_window.connect('key_press_event', self._key_press)
                
        self.power_button.connect('clicked', self._do_power_button)
        
        self.connect('shutdown', self.do_shutdown)

    def _toggle_light_mode(self, *args, **kwargs):
        Gtk.StyleContext.remove_provider_for_screen(self.screen, self.provider)

        if self.light_mode == constants.DARK:
            self.light_mode_button.set_image(MOON_BLACK_ICON)
            
            self.provider.load_from_path(
                    pkg_resources.resource_filename(__name__, 'qubes-menu-light.css')
            )

            self.light_mode = constants.LIGHT
            write_settings(constants.LIGHT_MODE, constants.LIGHT)

        else:
            self.light_mode_button.set_image(SUN_WHITE_ICON)

            self.provider.load_from_path(
                    pkg_resources.resource_filename(__name__, 'qubes-menu-dark.css')
            )

            self.light_mode = constants.DARK
            write_settings(constants.LIGHT_MODE, constants.DARK)

        Gtk.StyleContext.add_provider_for_screen(
            self.screen, self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _enter_light_mode_button(self, *args, **kwargs):
        current_img = self.light_mode_button.get_image()

        if (current_img == SUN_WHITE_ICON):
            self.light_mode_button.set_image(SUN_BLACK_ICON)

    def _leave_light_mode_button(self, *args, **kwargs):
        current_img = self.light_mode_button.get_image()

        if (current_img == SUN_BLACK_ICON):
            self.light_mode_button.set_image(SUN_WHITE_ICON)

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
        Hide the menu on focus out
        """
        self.hide_menu()
            
    def exit_app(self):
        """
        Exit. Used by restart only at the moment, as the menu is designed to
        keep running in the background.
        """
        self.quit()
        for task in self.tasks:
            with suppress(asyncio.CancelledError):
                task.cancel()

def run_asyncio(dispatcher):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        asyncio.ensure_future(dispatcher.listen_for_events())
    )
    loop.run_forever()

def main():
    """
    Start the menu app
    """
    qapp = qubesadmin.Qubes()
    dispatcher = qubesadmin.events.EventsDispatcher(qapp)
    threading.Thread(target=run_asyncio, args=(dispatcher, )).start()
    app = AppMenu(qapp, dispatcher)
    app.run(sys.argv)

    if f'--{constants.RESTART_PARAM_LONG}' in sys.argv or \
            f'-{constants.RESTART_PARAM_SHORT}' in sys.argv:
        sys.argv = [x for x in sys.argv if x not in
                    (f'--{constants.RESTART_PARAM_LONG}',
                     f'-{constants.RESTART_PARAM_SHORT}')]
        app = AppMenu(qapp, dispatcher)
        app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
