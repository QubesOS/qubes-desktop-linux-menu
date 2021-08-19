#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=import-error
import asyncio
import subprocess
import argparse
import sys
import os
import traceback
import xdg.DesktopEntry
import xdg.BaseDirectory
import xdg.Menu
from typing import Dict, Iterable, Union, Optional, List, Callable
from pathlib import Path, PosixPath
import pyinotify
import pkg_resources
import logging

import qubesadmin
import qubesadmin.events
from qubesadmin.vm import QubesVM

from html import escape

# pylint: disable=wrong-import-position
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango

import gbulb
gbulb.install()

STATE_DICTIONARY = {
    'domain-pre-start': 'Transient',
    'domain-start': 'Running',
    'domain-start-failed': 'Halted',
    'domain-paused': 'Paused',
    'domain-unpaused': 'Running',
    'domain-shutdown': 'Halted',
    'domain-pre-shutdown': 'Transient',
    'domain-shutdown-failed': 'Running'
}

FAVORITES_FEATURE = 'menu-favorites'
DISPOSABLE_PREFIX = '@disp:'
HOVER_TIMEOUT = 20

logger = logging.getLogger('qubes-appmenu')

parser = argparse.ArgumentParser(description='Qubes Application Menu')

parser.add_argument('--keep-visible', action='store_true',
                    help='Do not hide the menu after action.')
parser.add_argument('--restart', action='store_true',
                    help="Restart the menu if it's running")
# coding
# TODO: cli option for menu restart
# TODO: make assert if dispvm line is wrong
# TODO: dispatcher functions can NOT fail
# TODO: update labels in favorite list
# TODO: how to handle errors? when something didn't want to start or run?
# TODO: need a blank placeholder icon

# packaging and docs
# TODO: decent docs: document things like new features
# TODO: add mypy and pylint
# TODO: move things into separate files

# testing
# TODO: add testing, a lot of testing, incl favorite item: vm start?
# TODO: edge case: super long app name, vm name??

# TODO: debian?


def load_icon(icon_name, size: Gtk.IconSize = Gtk.IconSize.LARGE_TOOLBAR):
    _, width, height = Gtk.icon_size_lookup(size)
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, width, height)
    except GLib.Error:
        try:
            # icon name is a path
            return Gtk.IconTheme.get_default().load_icon(icon_name, width, 0)
        except GLib.GError:
            # icon not found in any way
            return None


class LimitedWidthLabel(Gtk.Label):
    def __init__(self, label_text=None):
        super().__init__()
        if label_text:
            self.set_label(label_text)
        self.set_width_chars(35)
        self.set_xalign(0)
        self.set_ellipsize(Pango.EllipsizeMode.END)


class HoverListBox(Gtk.ListBoxRow):
    def __init__(self):
        super().__init__()
        self.mouse = False
        self.event_box = Gtk.EventBox()
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.event_box.add(self.main_box)
        self.add(self.event_box)

        self.event_box.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        self.event_box.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.event_box.connect('enter-notify-event', self._enter_event)
        self.event_box.connect('leave-notify-event', self._leave_event)

    def _enter_event(self, *_args):
        self.mouse = True
        GLib.timeout_add(HOVER_TIMEOUT, self._select_me)

    def _leave_event(self, *_args):
        self.mouse = False

    def _select_me(self, *_args):
        if not self.mouse:
            return False
        self.activate()
        self.get_parent().select_row(self)
        return False


class ApplicationInfo:
    def __init__(self, qapp, file_path):
        self.qapp: qubesadmin.Qubes = qapp
        self.file_path: PosixPath = file_path
        self.app_icon: Optional[str] = None
        self.vm_icon: Optional[str] = None
        self.app_name: Optional[str] = None
        self.vm: Optional[qubesadmin.vm.QubesVM] = None
        self.entry_name: Optional[str] = None
        self.exec: List[str] = []
        self.disposable: bool = False
        self.categories = []
        self.entries: List[AppEntry] = []

    def load_data(self, entry):
        vm_name = entry.get('X-Qubes-VmName') or None
        try:
            self.vm = self.qapp.domains[vm_name]
        except KeyError:
            self.vm = None

        self.app_name = entry.getName()
        if self.vm and self.app_name.startswith(self.vm.name + ": "):
            self.app_name = self.app_name[len(self.vm.name + ": "):]
        self.vm_icon = self.vm.icon if self.vm else None
        self.app_icon = entry.getIcon()
        self.disposable = bool(entry.get('X-Qubes-NonDispvmExec'))
        self.entry_name = entry.get('X-Qubes-AppName') or self.file_path.name
        if self.disposable:
            self.entry_name = DISPOSABLE_PREFIX + self.entry_name
        self.exec = entry.getExec().split(' ')

        self.categories = entry.getCategories()

        for menu_entry in self.entries:
            menu_entry.update_contents()

    def get_command_for_vm(self, vm=None):
        command = self.exec
        if vm and self.vm != vm:
            # replace name of the old VM - used for opening apps from DVM
            # template in their child dispvm
            command = [str(vm) if s == str(self.vm) else s for s in command]
        return command

    def is_favorite(self):
        for entry in self.entries:
            if isinstance(entry, FavoritesAppEntry):
                return True
        return False

    def is_qubes_specific(self):
        return 'X-Qubes-VM' in self.categories


class SelfAwareMenu(Gtk.Menu):
    OPEN_MENUS = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('realize', self._add_to_open)
        self.connect('deactivate', self._remove_from_open)

    @staticmethod
    def _add_to_open(*_args):
        SelfAwareMenu.OPEN_MENUS += 1

    @staticmethod
    def _remove_from_open(*_args):
        SelfAwareMenu.OPEN_MENUS -= 1


class AppEntry(Gtk.ListBoxRow):
    def __init__(self, app_info: ApplicationInfo, **properties):
        super().__init__(**properties)
        self.app_info = app_info

        self.menu = SelfAwareMenu()
        self.menu.get_style_context().add_class('right_menu')

        self.event_box = Gtk.EventBox()
        self.add(self.event_box)
        self.event_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.event_box.connect('button-press-event', self.show_menu)

    def show_menu(self, _widget, event):
        if event.button == 3:
            self.menu.popup_at_pointer(None)  # None means current event

    def update_contents(self):
        pass

    def run_app(self, vm):
        command = self.app_info.get_command_for_vm(vm)
        subprocess.Popen(command, stdout=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_toplevel().get_application().hide_menu()


class BaseAppEntry(AppEntry):
    def __init__(self, app_info: ApplicationInfo, **properties):
        super().__init__(app_info, **properties)
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.event_box.add(self.box)
        self.get_style_context().add_class('app_entry')
        self._setup_menu()
        self.update_contents()

    def _setup_menu(self):
        self.add_menu_item = Gtk.CheckMenuItem(label='Add to favorites')
        self.add_menu_item.connect('activate', self._add_to_favorites)
        self.menu.add(self.add_menu_item)
        self.menu.show_all()

    def show_menu(self, widget, event):
        if getattr(self.get_parent(), 'ephemeral_vm', False):
            self.add_menu_item.set_active(False)
            self.add_menu_item.set_sensitive(False)
        else:
            self.add_menu_item.set_active(self.app_info.is_favorite())
            self.add_menu_item.set_sensitive(not self.app_info.is_favorite())
        super().show_menu(widget, event)

    def update_contents(self):
        icon = load_icon(self.app_info.app_icon, Gtk.IconSize.LARGE_TOOLBAR)
        icon_img: Gtk.Image = Gtk.Image.new_from_pixbuf(icon)

        for child in self.box:
            self.box.remove(child)
        self.box.pack_start(icon_img, False, False, 5)
        self.box.pack_start(
            LimitedWidthLabel(self.app_info.app_name), False, False, 5)
        self.show_all()

    def _add_to_favorites(self, *_args, **_kwargs):
        # disable the add-to-favorites for already-added items
        target_vm = self.app_info.vm
        if not target_vm:
            target_vm = self.app_info.qapp.domains[
                self.app_info.qapp.local_name]

        current_feature = target_vm.features.get(
            FAVORITES_FEATURE, '').split(' ')

        if self.app_info.entry_name in current_feature:
            return
        current_feature.append(self.app_info.entry_name)
        target_vm.features[FAVORITES_FEATURE] = ' '.join(current_feature)


class FavoritesAppEntry(AppEntry):
    def __init__(self, app_info: ApplicationInfo, **properties):
        super().__init__(app_info, **properties)
        self.get_style_context().add_class('favorite_entry')
        self.grid = Gtk.Grid()
        self.event_box.add(self.grid)
        self.remove_item = Gtk.MenuItem(label='Remove from favorites')
        self.remove_item.connect('activate', self._remove_from_favorites)
        self.menu.add(self.remove_item)
        self.menu.show_all()

        self.app_label = LimitedWidthLabel()
        self.vm_label = Gtk.Label()
        self.app_icon = Gtk.Image()
        self.vm_icon = Gtk.Image()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(self.vm_icon, False, False, 5)
        box.pack_start(self.vm_label, False, False, 5)
        self.vm_label.get_style_context().add_class('favorite_vm_name')
        self.app_label.get_style_context().add_class('favorite_app_name')
        self.app_label.set_halign(Gtk.Align.START)

        self.grid.attach(self.app_icon, 0, 0, 1, 2)
        self.grid.attach(self.app_label, 1, 0, 1, 1)
        self.grid.attach(box, 1, 1, 1, 1)

        self.update_contents()

    def update_contents(self):
        if self.app_info.vm_icon:
            vm_icon = load_icon(
                self.app_info.vm_icon, Gtk.IconSize.LARGE_TOOLBAR)
        else:
            vm_icon = None
        self.vm_icon.set_from_pixbuf(vm_icon)

        app_icon = load_icon(self.app_info.app_icon, Gtk.IconSize.DIALOG)
        self.app_icon.set_from_pixbuf(app_icon)

        if self.app_info.disposable:
            self.vm_label.set_label(
                'new Disposable VM from ' + str(self.app_info.vm))
        elif self.app_info.vm:
            self.vm_label.set_label(str(self.app_info.vm))
        else:
            self.vm_label.set_label(str(self.app_info.qapp.local_name))
        self.app_label.set_label(str(self.app_info.app_name))
        self.show_all()

    def _remove_from_favorites(self, *_args, **_kwargs):
        vm = self.app_info.vm or self.app_info.qapp.domains[
            self.app_info.qapp.local_name]
        current_feature = vm.features.get(
            FAVORITES_FEATURE, '').split(' ')

        try:
            current_feature.remove(self.app_info.entry_name)
        except ValueError:
            logger.info('Failed to remove %s from vm favorites for vm %s: '
                        'favorites did not contain %s',
                        self.app_info.entry_name, str(vm),
                        self.app_info.entry_name)
            self.get_parent().remove(self)
            return
        vm.features[FAVORITES_FEATURE] = ' '.join(current_feature)


class VMEntry(HoverListBox):
    def __init__(self, vm: QubesVM, qapp: qubesadmin.Qubes):
        super().__init__()
        self.qapp = qapp
        self.vm = vm
        self.vm_state = vm.get_power_state()
        self.sort_order = self.vm.name
        if self.vm.klass == 'DispVM':
            self.sort_order = self.vm.template.name + ":" + self.sort_order
        self.parent_vm = self.vm.template if self.vm.klass == 'DispVM' else None
        self.is_dispvmtemplate = bool(
            getattr(vm, 'template_for_dispvms', False))
        self.has_network = vm.is_networked()
        self.get_style_context().add_class('vm_entry')

        self.update_style()
        self.load_contents()

    def update_style(self):
        style_context: Gtk.StyleContext = self.get_style_context()
        if self.is_dispvmtemplate:
            style_context.add_class('dvm_template_entry')
        elif self.vm.klass == 'DispVM':
            style_context.add_class('dispvm_entry')
        else:
            if style_context.has_class('dispvm_entry'):
                style_context.remove_class('dispvm_entry')
            if style_context.has_class('dvm_template_entry'):
                style_context.remove_class('dvm_template_entry')

    def load_contents(self):
        for child in self.main_box.get_children():
            self.main_box.remove(child)

        icon = getattr(self.vm, 'icon', self.vm.label.icon)
        icon_vm = load_icon(icon)
        icon_img = Gtk.Image.new_from_pixbuf(icon_vm)

        self.main_box.pack_start(icon_img, False, False, 2)
        self.main_box.pack_start(
            Gtk.Label(label=self.vm.name), False, False, 2)
        self.main_box.show_all()

    @property
    def vm_state(self):
        return self._vm_state

    @vm_state.setter
    def vm_state(self, new_value):
        self._vm_state = new_value
        style_context = self.get_style_context()
        if self._vm_state == 'Running':
            style_context.add_class('running_vm')
        else:
            if style_context.has_class('running_vm'):
                style_context.remove_class('running_vm')


class ControlRow(Gtk.ListBoxRow):
    def __init__(self):
        super().__init__()
        self.row_label = LimitedWidthLabel()
        self.get_style_context().add_class('app_entry')
        self.add(self.row_label)
        self.command = None

    def update_state(self, state):
        pass

    def run_app(self, vm):
        if self.command and self.is_sensitive():
            subprocess.Popen([self.command, str(vm)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)


class StartControlItem(ControlRow):
    def __init__(self):
        super().__init__()
        self.state = None

    def update_state(self, state):
        self.state = state
        if state == 'Running':
            self.row_label.set_label('Shutdown qube')
            self.command = 'qvm-shutdown'
            return
        if state == 'Transient':
            self.row_label.set_label('Kill qube')
            self.command = 'qvm-kill'
            return
        if state == 'Halted':
            self.row_label.set_label('Start qube')
            self.command = 'qvm-start'
            return
        if state == 'Paused':
            self.row_label.set_label('Unpause qube')
            self.command = 'qvm-unpause'
            return


class PauseControlItem(ControlRow):
    def __init__(self):
        super().__init__()
        self.state = None

    def update_state(self, state):
        self.state = state
        if state == 'Running':
            self.row_label.set_label('Pause qube')
            self.set_sensitive(True)
            self.command = 'qvm-pause'
            return
        self.row_label.set_label(' ')
        self.set_sensitive(False)
        self.command = None


class ControlList(Gtk.ListBox):
    def __init__(self, app_page):
        super().__init__()
        self.app_page = app_page

        self.get_style_context().add_class('right_pane')

        self.start_item = StartControlItem()

        self.add(self.start_item)
        self.add(PauseControlItem())

    def update_visibility(self, state):
        for row in self.get_children():
            row.update_state(state)


class DesktopFileManager:
    # pylint: disable=invalid-name
    class EventProcessor(pyinotify.ProcessEvent):
        def __init__(self, parent):
            self.parent = parent
            super().__init__()

        def process_IN_CREATE(self, event):
            self.parent.load_file(event.pathname)

        def process_IN_DELETE(self, event):
            self.parent.remove_file(event.pathname)

        def process_IN_MODIFY(self, event):
            self.parent.load_file(event.pathname)

    def __init__(self, qapp):
        self.qapp = qapp
        self.watch_manager = None
        self.notifier = None
        self.watches = []
        self._callbacks: List[Callable] = []

        # directories used by Qubes menu tools, not necessarily all possible
        # XDG directories
        self.desktop_dirs = [
            Path(xdg.BaseDirectory.xdg_data_home) / 'applications',
            Path('/usr/share/applications')]
        self.current_environments = os.environ['XDG_CURRENT_DESKTOP'].split(':')

        self.app_entries: Dict[Path, ApplicationInfo] = {}

        for directory in self.desktop_dirs:
            for file in os.listdir(directory):
                self.load_file(directory / file)
        self.initialize_watchers()

    def register_callback(self, func):
        # for new file callbacks
        self._callbacks.append(func)
        for info in self.app_entries.values():
            func(info)

    def get_app_infos(self):
        for info in self.app_entries.values():
            yield info

    def remove_file(self, path: Union[str, Path]):
        if isinstance(path, str):
            path = Path(path)
        app_info = self.app_entries.get(path)

        if app_info:
            for child in app_info.entries:
                parent = child.get_parent()
                parent.remove(child)
                parent.invalidate_filter()
            del self.app_entries[path]

    def load_file(self, path: Union[str, Path]):
        if isinstance(path, str):
            path = Path(path)

        if not path.name.endswith('.desktop'):
            return

        try:
            entry = xdg.DesktopEntry.DesktopEntry(path)
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning(
                'Cannot load desktop entry file %s: %s', path, str(ex))
            self.remove_file(path)
            return

        if not self._eligibility_check(entry):
            self.remove_file(path)
            return

        app_info = self.app_entries.get(path, None)
        if not app_info:
            new_entry = True
            app_info = ApplicationInfo(self.qapp, path)
            self.app_entries[path] = app_info
        else:
            new_entry = False
        app_info.load_data(entry)

        if new_entry:
            for func in self._callbacks:
                func(app_info)

    def _eligibility_check(self, entry):
        if entry.getHidden():
            return False
        if entry.getOnlyShowIn():
            return bool(set(entry.getOnlyShowIn()).intersection(
                self.current_environments))
        if entry.getNotShowIn():
            return not bool(
                set(entry.getNotShowIn()).intersection(
                    self.current_environments))
        return True

    def initialize_watchers(self):
        self.watch_manager = pyinotify.WatchManager()

        # pylint: disable=no-member
        mask = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MODIFY

        loop = asyncio.get_event_loop()

        self.notifier = pyinotify.AsyncioNotifier(
            self.watch_manager, loop,
            default_proc_fun=DesktopFileManager.EventProcessor(self))

        for path in self.desktop_dirs:
            self.watches.append(
                self.watch_manager.add_watch(
                    str(path), mask, rec=True, auto_add=True))


class NetworkIndicator(Gtk.Box):
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
        # True is network on, False is network off
        self.set_visible(True)
        self.network_on.set_visible(state)
        self.network_off.set_visible(not state)


class VMManager:
    def __init__(self, qapp: qubesadmin.Qubes, dispatcher,
                 vm_list_widget: Gtk.ListBox):
        self.qapp = qapp
        self.dispatcher = dispatcher
        self.vm_list_widget: Gtk.ListBox = vm_list_widget

        self.vms: Dict[str, VMEntry] = {}

        for vm in self.qapp.domains:
            self._get_vm_entry(vm.name)

        self.register_events()

    def _get_vm_entry(self, vm_name: str) -> Optional[VMEntry]:
        try:
            vm: QubesVM = self.qapp.domains[vm_name]
        except KeyError:
            return None
        if vm.klass == 'AdminVM' or vm.features.get('internal', False):
            return None

        if vm_name not in self.vms:
            try:
                entry = VMEntry(vm, self.qapp)
            except Exception:  # pylint: disable=broad-except
                # a wrapper, to make absolutely sure dispatcher is not crashed
                # by a rogue Exception
                return None
            entry.show_all()
            self.vms[vm.name] = entry
            self.vm_list_widget.add(entry)
            return entry
        return self.vms[vm_name]

    def _add_vm(self, vm) -> VMEntry:
        entry = VMEntry(vm, self.qapp)
        entry.show_all()
        self.vms[vm.name] = entry
        self.vm_list_widget.add(entry)
        return entry

    def get_vm_entries(self) -> Iterable[VMEntry]:
        for entry in self.vms.values():
            yield entry

    def add_domain_entry(self, _submitter, _event, vm, **_kwargs):
        self._get_vm_entry(vm)

    def remove_domain_entry(self, _submitter, _event, vm, **_kwargs):
        entry = self.vms.get(vm)
        if entry:
            self.vm_list_widget.remove(entry)
            del self.vms[vm]

    def update_domain_entry(self, vm_name, event, **_kwargs):
        vm_entry = self._get_vm_entry(vm_name)

        if event in STATE_DICTIONARY:
            state = STATE_DICTIONARY[event]
            vm_entry.vm_state = state
            # State for new vms
        elif event == 'property-set:label':
            vm_entry.load_contents()
        elif event == 'property-set:netvm':
            vm_entry.has_network = vm_entry.vm.is_networked()
        elif event == 'property-set:template-for-dispvms':
            vm_entry.is_dispvmtemplate = \
                bool(getattr(vm_entry.vm, 'template_for_dispvms', False))
            vm_entry.update_style()
            self.vm_list_widget.invalidate_sort()
            self.vm_list_widget.invalidate_filter()

        if vm_entry.is_selected():
            vm_entry.get_parent().select_row(None)
            vm_entry.get_parent().select_row(vm_entry)

    def register_events(self):
        self.dispatcher.add_handler('domain-pre-start',
                                    self.update_domain_entry)
        self.dispatcher.add_handler('domain-start', self.update_domain_entry)
        self.dispatcher.add_handler('domain-start-failed',
                                    self.update_domain_entry)
        self.dispatcher.add_handler('domain-paused', self.update_domain_entry)
        self.dispatcher.add_handler('domain-unpaused', self.update_domain_entry)
        self.dispatcher.add_handler('domain-shutdown', self.update_domain_entry)
        self.dispatcher.add_handler('domain-pre-shutdown',
                                    self.update_domain_entry)
        self.dispatcher.add_handler('domain-shutdown-failed',
                                    self.update_domain_entry)

        self.dispatcher.add_handler('domain-add', self.add_domain_entry)
        self.dispatcher.add_handler('domain-delete', self.remove_domain_entry)
        self.dispatcher.add_handler('property-set:netvm',
                                    self.update_domain_entry)
        self.dispatcher.add_handler('property-set:label',
                                    self.update_domain_entry)
        self.dispatcher.add_handler('property-set:template-for-dispvms',
                                    self.update_domain_entry)


class VMTypeToggle:
    def __init__(self, builder: Gtk.Builder, qapp: qubesadmin.Qubes):
        self.apps_toggle: Gtk.RadioButton = builder.get_object('apps_toggle')
        self.templates_toggle: Gtk.RadioButton = \
            builder.get_object('templates_toggle')
        self.system_toggle: Gtk.RadioButton = \
            builder.get_object('system_toggle')
        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')
        self.qapp = qapp

        self.buttons = [self.apps_toggle, self.templates_toggle,
                        self.system_toggle]

        for button in self.buttons:
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            button.set_can_focus(True)
            button.connect('focus', self._activate_button)

    def initialize_state(self):
        self.apps_toggle.set_active(True)

        for button in self.buttons:
            if button.get_size_request() == (-1, -1):
                button.set_size_request(button.get_allocated_width()*1.2, -1)

    def _activate_button(self, widget, _event):
        widget.set_active(True)

    def connect_to_toggle(self, func):
        for button in self.buttons:
            button.connect('toggled', func)

    def filter_function(self, row):
        try:
            vm = self.qapp.domains[row.vm]
        except KeyError:
            return False

        if self.apps_toggle.get_active():
            return self._filter_appvms(vm)
        if self.templates_toggle.get_active():
            return self._filter_templatevms(vm)
        if self.system_toggle.get_active():
            return self._filter_service(vm)
        return False

    @staticmethod
    def _filter_appvms(vm: qubesadmin.vm.QubesVM):
        if vm.provides_network:
            return False
        if vm.klass == 'TemplateVM':
            return False
        return True

    @staticmethod
    def _filter_templatevms(vm: qubesadmin.vm.QubesVM):
        if vm.klass == 'TemplateVM':
            return True
        return getattr(vm, 'template_for_dispvms', False)

    @staticmethod
    def _filter_service(vm: qubesadmin.vm.QubesVM):
        return vm.provides_network


class SettingsEntry(Gtk.ListBoxRow):
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
        subprocess.Popen(
            ['qubes-vm-settings', vm.name], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self.get_toplevel().get_application().hide_menu()


class AppPage:
    def __init__(self, qapp: qubesadmin.Qubes, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher):
        self.qapp = qapp
        self.dispatcher = dispatcher
        self.desktop_file_manager = desktop_file_manager

        self.selected_vm_entry: Optional[VMEntry] = None
        self.main_window: Gtk.Window = builder.get_object('main_window')

        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')
        self.settings_list: Gtk.ListBox = builder.get_object('settings_list')
        self.vm_right_pane: Gtk.Box = builder.get_object('vm_right_pane')
        self.network_indicator = NetworkIndicator()
        self.vm_right_pane.pack_start(self.network_indicator, False, False, 0)
        self.vm_right_pane.reorder_child(self.network_indicator, 0)

        self.desktop_file_manager.register_callback(self._app_info_callback)
        self.toggle_buttons = VMTypeToggle(builder, self.qapp)
        self.toggle_buttons.connect_to_toggle(self._button_toggled)

        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect('row-activated', self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        self.app_list.invalidate_sort()

        self.vm_manager = VMManager(self.qapp, self.dispatcher,
                                    self.vm_list)
        self.vm_list.set_sort_func(lambda x, y: x.sort_order > y.sort_order)
        self.vm_list.set_filter_func(self.toggle_buttons.filter_function)

        self.vm_list.connect('row-selected', self._selection_changed)

        self.settings_list.add(SettingsEntry())
        self.settings_list.connect('row-activated', self._app_clicked)

        self.control_list = ControlList(self)
        self.control_list.connect('row-activated', self._app_clicked)
        self.vm_right_pane.pack_end(self.control_list, False, False, 0)

        self._set_keyboard_focus_chain()
        self.app_list.connect('keynav-failed', self._keynav_failed)
        self.settings_list.connect('keynav-failed', self._keynav_failed)
        self.control_list.connect('keynav-failed', self._keynav_failed)
        self.app_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.settings_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.control_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.widget_order = [self.settings_list, self.app_list,
                             self.control_list]

    def _app_info_callback(self, app_info):
        if app_info.vm:
            entry = BaseAppEntry(app_info)
            app_info.entries.append(entry)
            self.app_list.add(entry)

    def _is_app_fitting(self, appentry: BaseAppEntry):
        if not self.selected_vm_entry:
            return False
        if appentry.app_info.vm and \
                appentry.app_info.vm.name != self.selected_vm_entry.vm:
            return self.selected_vm_entry.parent_vm == \
                   appentry.app_info.vm.name and \
                   not appentry.app_info.disposable
        if self.selected_vm_entry.is_dispvmtemplate:
            return appentry.app_info.disposable == \
                   self.toggle_buttons.apps_toggle.get_active()
        return True

    def _set_keyboard_focus_chain(self):
        self.control_list.focus_neighbors = {
            Gtk.DirectionType.UP: self.app_list,
            Gtk.DirectionType.DOWN: self.settings_list,
        }
        self.app_list.focus_neighbors = {
            Gtk.DirectionType.UP: self.settings_list,
            Gtk.DirectionType.DOWN: self.control_list,
        }
        self.settings_list.focus_neighbors = {
            Gtk.DirectionType.UP: self.control_list,
            Gtk.DirectionType.DOWN: self.app_list,
        }

    def _get_direction_child(self, widget: Gtk.ListBox,
                             direction: Gtk.DirectionType):
        child_list = widget.get_children()
        if direction == Gtk.DirectionType.UP:
            child_list = reversed(child_list)
        for child in child_list:
            if widget != self.app_list or self._is_app_fitting(child):
                return child
        return widget.get_row_at_index(0)

    def _keynav_failed(self, widget: Gtk.ListBox, direction: Gtk.DirectionType):
        next_widget_dict = getattr(widget, 'focus_neighbors', None)
        if not next_widget_dict:
            return
        next_widget = next_widget_dict.get(direction, None)
        if not next_widget:
            return
        next_focus_widget = self._get_direction_child(next_widget, direction)
        next_focus_widget.grab_focus()

    def _app_clicked(self, _widget: Gtk.Widget, row: AppEntry):
        if not self.selected_vm_entry:
            return
        row.run_app(self.selected_vm_entry.vm)

    def _button_toggled(self, widget: Gtk.ToggleButton):
        if not widget.get_active():
            return
        self.vm_list.select_row(None)
        self.app_list.invalidate_filter()
        self.vm_list.invalidate_filter()

    def initialize_state(self, _vm: Optional[qubesadmin.vm.QubesVM] = None):
        self.toggle_buttons.initialize_state()
        self.app_list.select_row(None)
        self.control_list.hide()
        self.settings_list.hide()

    def _selection_changed(self, _widget, row: Optional[VMEntry]):
        if row is None:
            self.selected_vm_entry = None
            self.control_list.hide()
            self.settings_list.hide()
            self.network_indicator.set_visible(False)
            return
        self.selected_vm_entry = row
        self.control_list.show_all()
        self.settings_list.show_all()
        self.app_list.invalidate_filter()
        self.control_list.update_visibility(row.vm_state)
        self.control_list.select_row(None)
        self.app_list.ephemeral_vm = bool(self.selected_vm_entry.parent_vm)
        self.network_indicator.set_network_state(row.has_network)


class FavoritesPage:
    def __init__(self, qapp: qubesadmin.Qubes, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher):
        self.qapp = qapp
        self.desktop_file_manager = desktop_file_manager
        self.dispatcher = dispatcher

        self.app_list: Gtk.ListBox = builder.get_object('fav_app_list')
        self.app_list.connect('row-activated', self._app_clicked)

        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        self.desktop_file_manager.register_callback(self._app_info_callback)
        self.app_list.show_all()
        self.app_list.invalidate_sort()
        self.app_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.dispatcher.add_handler(
            f'domain-feature-delete:{FAVORITES_FEATURE}', self._feature_deleted)
        self.dispatcher.add_handler(
            f'domain-feature-set:{FAVORITES_FEATURE}', self._feature_set)
        self.dispatcher.add_handler('domain-add', self._domain_added)
        self.dispatcher.add_handler('domain-delete', self._domain_deleted)

    def _load_vms_favorites(self, vm):
        if isinstance(vm, str):
            try:
                vm = self.qapp.domains[vm]
            except KeyError:
                return
        favorites = vm.features.get(FAVORITES_FEATURE, '')
        favorites = favorites.split(' ')

        is_local_vm = (vm.name == self.qapp.local_name)

        for app_info in self.desktop_file_manager.get_app_infos():
            if (not is_local_vm and app_info.vm == vm)\
                    or (is_local_vm and not app_info.vm):
                if app_info.entry_name in favorites:
                    self._add_from_app_info(app_info)
        self.app_list.invalidate_sort()
        self.app_list.show_all()

    def _app_info_callback(self, app_info):
        if app_info.vm:
            vm = app_info.vm
        else:
            vm = app_info.qapp.domains[app_info.qapp.local_name]

        feature = vm.features.get(FAVORITES_FEATURE, '').split(' ')
        if app_info.entry_name in feature:
            self._add_from_app_info(app_info)

    def _add_from_app_info(self, app_info):
        entry = FavoritesAppEntry(app_info)
        app_info.entries.append(entry)
        self.app_list.add(entry)

    @staticmethod
    def _app_clicked(_widget, row: AppEntry):
        row.run_app(row.app_info.vm)

    def _feature_deleted(self, vm, _event, _feature, *_args, **_kwargs):
        try:
            if str(vm) == self.qapp.local_name:
                vm = None
            for child in self.app_list.get_children():
                if str(child.app_info.vm) == str(vm):
                    child.app_info.entries.remove(child)
                    self.app_list.remove(child)
            self.app_list.invalidate_sort()
        except Exception as ex: # pylint: disable=broad-except
            logger.warning(
                'Encountered problem removing favorite entry: %s', repr(ex))

    def _feature_set(self, vm, event, feature, *_args, **_kwargs):
        try:
            self._feature_deleted(vm, event, feature)
            self._load_vms_favorites(vm)
        except Exception as ex: # pylint: disable=broad-except
            logger.warning(
                'Encountered problem adding favorite entry: %s', repr(ex))

    def _domain_added(self, _submitter, _event, vm, **_kwargs):
        self._load_vms_favorites(vm)

    def _domain_deleted(self, _submitter, event, vm, **_kwargs):
        self._feature_deleted(vm, event, None)


class SettingsCategoryRow(HoverListBox):
    def __init__(self, name, filter_func):
        super().__init__()
        self.name = name
        self.label = LimitedWidthLabel(self.name)
        self.main_box.add(self.label)
        self.filter_func = filter_func
        self.get_style_context().add_class('settings_category_row')
        self.show_all()


class SettingsPage:
    def __init__(self, qapp, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher):
        self.qapp = qapp
        self.desktop_file_manager = desktop_file_manager
        self.dispatcher = dispatcher

        self.app_list: Gtk.ListBox = builder.get_object('sys_tools_list')
        self.app_list.connect('row-activated', self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        self.app_list.set_filter_func(self._filter_apps)

        self.category_list: Gtk.ListBox = builder.get_object(
            'settings_categories')

        self.category_list.connect('row-activated', self._category_clicked)
        self.category_list.add(SettingsCategoryRow('Qubes Tools',
                                                   self._filter_qubes_tools))
        self.category_list.add(
            SettingsCategoryRow('System Settings',
                                self._filter_system_settings))
        self.category_list.add(SettingsCategoryRow('Other', self._filter_other))

        self.desktop_file_manager.register_callback(self._app_info_callback)

        self.app_list.show_all()
        self.app_list.invalidate_filter()
        self.app_list.invalidate_sort()

    def initialize_state(self):
        self.category_list.select_row(None)

    def _filter_apps(self, row):
        filter_func = getattr(self.category_list.get_selected_row(),
                              'filter_func', None)
        if not filter_func:
            return False
        return filter_func(row)

    @staticmethod
    def _filter_qubes_tools(row):
        if 'X-XFCE-SettingsDialog' not in row.app_info.categories:
            return False
        return 'qubes' in row.app_info.entry_name

    @staticmethod
    def _filter_system_settings(row):
        if 'X-XFCE-SettingsDialog' in row.app_info.categories:
            return 'qubes' not in row.app_info.entry_name
        if 'Settings' in row.app_info.categories:
            return True
        return False

    def _filter_other(self, row):
        return not self._filter_qubes_tools(row) and \
               not self._filter_system_settings(row)

    def _category_clicked(self, *_args):
        self.app_list.invalidate_filter()

    @staticmethod
    def _app_clicked(_widget, row: AppEntry):
        row.run_app(None)

    def _app_info_callback(self, app_info):
        if not app_info.vm and not app_info.is_qubes_specific():
            entry = BaseAppEntry(app_info)
            app_info.entries.append(entry)
            self.app_list.add(entry)


def show_error(title, text):
    dialog = Gtk.MessageDialog(
        None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK)
    dialog.set_title(title)
    dialog.set_markup(text)
    dialog.connect("response", lambda *x: dialog.destroy())
    dialog.show()


class AppMenu(Gtk.Application):
    def __init__(self, qapp, dispatcher, keep_visible):
        super().__init__(application_id='org.qubesos.appmenu')
        self.qapp = qapp
        self.dispatcher = dispatcher
        self.primary = False
        self.keep_visible = keep_visible

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_path(pkg_resources.resource_filename(
            __name__, 'qubes-menu-dark.css'))
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.builder = Gtk.Builder()
        self.builder.add_from_file(pkg_resources.resource_filename(
            __name__, 'qubes-menu.glade'))
        self.main_window: Gtk.Window = self.builder.get_object('main_window')
        self.main_window.focus_out_callback = self._focus_out
        self.main_notebook: Gtk.Notebook = \
            self.builder.get_object('main_notebook')

        self.fav_app_list: Gtk.ListBox = self.builder.get_object('fav_app_list')
        self.sys_tools_list: Gtk.ListBox = \
            self.builder.get_object('sys_tools_list')

        self.desktop_file_manager: Optional[DesktopFileManager] = None
        self.app_page: Optional[AppPage] = None

        self.favorites_page: Optional[FavoritesPage] = None
        self.settings_page: Optional[SettingsPage] = None

        self.power_button: Gtk.Button = self.builder.get_object('power_button')
        self.tasks = []

    @staticmethod
    def _do_power_button(_widget):
        subprocess.Popen('xfce4-session-logout',
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL)

    def do_activate(self, *args, **kwargs):
        # this should be just show, also:
        if not self.primary:
            self.perform_setup()
            self.primary = True
            self.main_window.show_all()
            self.initialize_state()
            self.hold()
        else:
            self.main_window.present()

    def hide_menu(self):
        if not self.keep_visible:
            self.main_window.hide()

    def _key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_menu()

    def _focus_out(self, _widget, _event: Gdk.EventFocus):
        if SelfAwareMenu.OPEN_MENUS <= 0:
            self.hide_menu()

    def initialize_state(self):
        self.main_notebook.set_current_page(0)
        self.app_page.initialize_state(None)

    def perform_setup(self):
        self.main_window.set_events(Gdk.EventMask.FOCUS_CHANGE_MASK)
        self.main_window.connect('focus-out-event', self._focus_out)
        self.main_window.connect('key_press_event', self._key_press)
        self.add_window(self.main_window)
        self.desktop_file_manager = DesktopFileManager(self.qapp)

        self.app_page = AppPage(self.qapp, self.builder,
                                self.desktop_file_manager, self.dispatcher)
        self.favorites_page = FavoritesPage(self.qapp, self.builder,
                                            self.desktop_file_manager,
                                            self.dispatcher)
        self.settings_page = SettingsPage(self.qapp, self.builder,
                                          self.desktop_file_manager,
                                          self.dispatcher)
        self.power_button.connect('clicked', self._do_power_button)
        self.main_notebook.connect('switch-page', self._handle_page_switch)

        self.tasks = [
            asyncio.ensure_future(self.dispatcher.listen_for_events())]

    def _handle_page_switch(self, _widget, _page, page_num):
        if page_num == 0:
            self.app_page.initialize_state()
        elif page_num == 2:
            self.settings_page.initialize_state()

    def do_shutdown(self, *args, **kwargs):
        print("go away!")


def main():
    """
    Start the menu app
    """
    args = parser.parse_args()
    qapp = qubesadmin.Qubes()
    dispatcher = qubesadmin.events.EventsDispatcher(qapp)
    app = AppMenu(qapp, dispatcher, args.keep_visible)
    loop = asyncio.get_event_loop()
    app.run()

    if not app.primary:
        return

    done, _unused = loop.run_until_complete(asyncio.wait(
            app.tasks, return_when=asyncio.FIRST_EXCEPTION))

    exit_code = 0

    for d in done:  # pylint: disable=invalid-name
        try:
            d.result()
        except Exception as _ex:  # pylint: disable=broad-except
            exc_type, exc_value = sys.exc_info()[:2]
            dialog = Gtk.MessageDialog(
                None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK)
            dialog.set_title("Houston, we have a problem...")
            dialog.set_markup(
                "<b>Whoops. A critical error in App Menu has occured.</b>"
                " This is most likely a bug in the widget. The App Menu"
                " will restart itself.")
            exc_description = "\n<b>{}</b>: {}\n{}".format(
                   exc_type.__name__, exc_value, traceback.format_exc(limit=10)
                )
            dialog.format_secondary_markup(escape(exc_description))
            dialog.run()
            exit_code = 1
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

# future: rethink categorizing apps and maybe use Menu files for that
# future: add placeholder entries for missing favorites entries
# future: vm color on hover on apps
# future: add Terminal and Files to each VM?
# future: perhaps the not working add to favs when ephemeral_vm could use a
#   tooltip or something
# future: changing keep visible setting
# future: shortcut keys for control row items; not a great idea RN,
# should be added with search
# future: add restart vm item
# future: add resizing in a smarter way
# future: add handling sizes in a smarter way
# future: nicer handling for dispvm line icon
