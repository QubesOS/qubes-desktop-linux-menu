# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2021 Marta Marczykowska-Górecka
#                               <marmarta@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.
"""
Various custom Gtk widgets used in Qubes App Menu.
"""
import subprocess

from .vm_manager import VMEntry
from . import constants
from .utils import load_icon

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango


class LimitedWidthLabel(Gtk.Label):
    """
    Gtk.Label, but with ellipsization and capped at 35 characters wide
    (which is not coincidentally 4 characters more than maximum VM name length)
    """
    def __init__(self, label_text=None):
        """
        :param label_text: optional text of the newly instantiated label
        """
        super().__init__()
        if label_text:
            self.set_label(label_text)
        self.set_width_chars(35)
        self.set_xalign(0)
        self.set_ellipsize(Pango.EllipsizeMode.END)

class NetworkIndicator(Gtk.Box):
    """
    Network Indicator Gtk.Box - changes appearance when set_network_state is
    called.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.icon_size = Gtk.IconSize.DND
        self.network_on = Gtk.Image.new_from_pixbuf(
            load_icon('qappmenu-networking-yes', self.icon_size))
        self.network_off = Gtk.Image.new_from_pixbuf(
            load_icon('qappmenu-networking-no', self.icon_size))

        _, height, _ = Gtk.icon_size_lookup(self.icon_size)
        self.network_on.set_size_request(-1, height * 1.3)
        self.network_off.set_size_request(-1, height * 1.3)

        self.pack_end(self.network_on, False, True, 10)
        self.pack_end(self.network_off, False, True, 10)

        self.network_on.set_no_show_all(True)
        self.network_off.set_no_show_all(True)

    def set_network_state(self, state: bool):
        """
        :param state: boolean, True indicates network is on and False indicates
        it is off
        """
        self.set_visible(True)
        self.network_on.set_visible(state)
        self.network_off.set_visible(not state)

class ServiceVM(Gtk.ListBoxRow):
    def __init__(self, vm_entry: VMEntry):
        super().__init__()
        self.get_style_context().add_class('service_vm_entry')

        self.vm_entry = vm_entry

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.icon_img = Gtk.Image()
        self.icon_img.set_from_pixbuf(
            load_icon(
                self.vm_entry.vm_icon_name,
                Gtk.IconSize.DND
            )
        )
        
        self.main_box.pack_start(self.icon_img, False, False, 15)
        self.main_box.pack_start(Gtk.Label(label=self.vm_entry.vm_name), False, False, 15)
        
        self.add(self.main_box)
        self.show_all()

    def update_contents(self,
                    update_power_state=False,
                    update_label=False,
                    update_has_network=False,
                    update_type=False):
        """
        Update own contents (or related widgets, if applicable) based on state
        change.
        :param update_power_state: whether to update if VM is running or not
        :param update_label: whether label (vm icon) should be updated
        :param update_has_network: whether VM networking state should be
        updated
        :param update_type: whether VM type should be updated
        :return:
        """
        if update_label:
            pass
        if update_type or update_power_state:
            pass
        if update_has_network:
            pass

class SettingsEntry(Gtk.ListBoxRow):
    """
    Gtk.ListBoxRow especially for a (run VM) Settings entry.
    """
    def __init__(self):
        super().__init__()
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.settings_icon = Gtk.Image.new_from_pixbuf(
            load_icon('qappmenu-settings'))
        self.hbox.pack_start(self.settings_icon, False, False, 5)
        self.settings_label = Gtk.Label(label="Settings", xalign=0)
        self.hbox.pack_start(self.settings_label, False, False, 5)
        self.get_style_context().add_class('app_entry')
        self.add(self.hbox)

    def run_app(self, vm):
        """Run settings for specified vm."""
        subprocess.Popen(
            ['qubes-vm-settings', vm.name], stdin=subprocess.DEVNULL)
        self.get_toplevel().get_application().hide_menu()
