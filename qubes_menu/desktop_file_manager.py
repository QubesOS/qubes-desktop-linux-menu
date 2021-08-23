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

import pyinotify
import logging
import asyncio
import os
import xdg.DesktopEntry
import xdg.BaseDirectory
import xdg.Menu
from pathlib import PosixPath, Path
from typing import Optional, List, Union, Dict, Callable
import qubesadmin
import qubesadmin.vm
import qubesadmin.events

from . import constants

logger = logging.getLogger('qubes-appmenu')


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
        self.entries: List = []

    def load_data(self, entry):
        vm_name = entry.get('X-Qubes-VmName') or None
        try:
            self.vm = self.qapp.domains[vm_name]
        except KeyError:
            self.vm = None

        self.app_name = entry.getName() or ''
        if self.vm and self.app_name.startswith(self.vm.name + ": "):
            self.app_name = self.app_name[len(self.vm.name + ": "):]
        self.vm_icon = self.vm.icon if self.vm else None
        self.app_icon = entry.getIcon()
        self.disposable = bool(entry.get('X-Qubes-NonDispvmExec'))
        self.entry_name = entry.get('X-Qubes-AppName') or self.file_path.name
        if self.disposable:
            self.entry_name = constants.DISPOSABLE_PREFIX + self.entry_name
        self.exec = entry.getExec().split(' ')

        self.categories = entry.getCategories()

        for menu_entry in self.entries:
            menu_entry.update_contents()

    def get_command_for_vm(self, vm=None):
        command = self.exec
        if vm and self.vm != vm:
            # replace name of the old VM - used for opening apps from DVM
            # template in their child dispvm
            if command[5] != str(self.vm):
                logger.warning(
                    'Unexpected command for a disposable VM: %s', command)
            command = [str(vm) if s == str(self.vm) else s for s in command]
        return command

    def is_qubes_specific(self):
        return 'X-Qubes-VM' in self.categories


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
