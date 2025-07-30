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
Helper class that manages all events related to VMs.
"""
import qubesadmin.events
import qubesadmin.exc
from qubesadmin.vm import QubesVM
from typing import Optional, Dict, List, Callable

from . import constants


class VMEntry:
    """
    A helper object containing information about a VM. Attempts to cache as
    much data as possible and update it on events, sending also information
    to all related menu entries to update themselves.
    """

    def __init__(self, vm: QubesVM):
        self.vm = vm
        self.vm_name = str(vm)
        self.vm_klass = vm.klass

        if self.vm.klass == "DispVM" and self.vm.auto_cleanup:
            self.parent_vm = self.vm.template
            self.sort_name = (
                f"{str(self.parent_vm.name).lower()} :{self.vm_name.lower()}"
            )
        else:
            self.parent_vm = None
            # the space here is to assure correct sorting for dispvm children
            self.sort_name = self.vm_name.lower() + " "

        try:
            self._internal = bool(
                self.vm.features.check_with_template("internal", False)
            )
        except qubesadmin.exc.QubesDaemonAccessError:
            self._internal = False
        self._servicevm = bool(self.vm.features.get("servicevm", False))
        self._is_dispvm_template = getattr(self.vm, "template_for_dispvms", False)
        self._has_network = self.vm.is_networked() if vm.klass != "AdminVM" else False
        self._vm_icon_name = getattr(
            self.vm, "icon", getattr(self.vm.label, "icon", None)
        )
        self._power_state = self.vm.get_power_state()
        self.show_dispvm_template_in_apps = bool(
            vm.features.get("appmenus-dispvm", False)
        )
        self.entries: List = []

    def update_entries(
        self,
        update_power_state=False,
        update_label=False,
        update_has_network=False,
        update_type=False,
    ):
        """
        Update all related menu entries.
        :param update_power_state: did power state change?
        :param update_label: did VM label change?
        :param update_has_network: did networking state change?
        :param update_type: did type change?
        """
        for entry in self.entries:
            entry.update_contents(
                update_power_state,
                update_label,
                update_has_network,
                update_type,
            )

    @property
    def power_state(self):
        """
        Property representing VM's current power state; updated based on events,
        not on get_power_state method to avoid slowdowns.
        """
        return self._power_state

    @power_state.setter
    def power_state(self, new_value):
        self._power_state = new_value
        self.update_entries(update_power_state=True)

    @property
    def vm_icon_name(self):
        """
        Name of VM's icon.
        """
        return self._vm_icon_name

    @vm_icon_name.setter
    def vm_icon_name(self, _new_value):
        self._vm_icon_name = getattr(self.vm, "icon", self.vm.label.icon)
        self.update_entries(update_label=True)

    @property
    def has_network(self):
        """Whether VM currently has network (or, to be more precise, if its
        connected to a sensible netvm"""
        return self._has_network

    @has_network.setter
    def has_network(self, new_value):
        self._has_network = new_value
        self.update_entries(update_has_network=True)

    @property
    def is_dispvm_template(self):
        """Is the VM a template for disposable VMs"""
        return self._is_dispvm_template

    @is_dispvm_template.setter
    def is_dispvm_template(self, new_value):
        self._is_dispvm_template = new_value
        self.update_entries(update_type=True)

    @property
    def internal(self):
        """Is the VM internal"""
        return self._internal

    @internal.setter
    def internal(self, new_value):
        self._internal = new_value
        self.update_entries(update_type=True)

    @property
    def service_vm(self):
        """Does the VM provide network"""
        return self._servicevm

    @service_vm.setter
    def service_vm(self, new_value):
        self._servicevm = new_value
        self.update_entries(update_type=True)

    @property
    def show_in_apps(self):
        """Should this qube be shown in the Apps section of the menu?"""
        if self.internal:
            return False
        if self.service_vm:
            return False
        if self.vm_klass == "TemplateVM":
            return False
        if self.vm_klass == "AdminVM":
            return False
        if self.is_dispvm_template and not self.show_dispvm_template_in_apps:
            return False
        return True

    @property
    def _escaped_name(self) -> str:
        """Name escaped according to rules from desktop-linux-common
        package"""
        return self.vm_name.replace("_", "_u").replace("-", "_d").replace(".", "_p")

    @property
    def settings_desktop_file_name(self) -> str:
        """
        Name of relevant .desktop vm settings file.
        """
        return "org.qubes-os.qubes-vm-settings._" + self._escaped_name + ".desktop"

    @property
    def start_vm_desktop_file_name(self) -> str:
        """
        Name of relevant .desktop start vm file.
        """
        return "org.qubes-os.vm._" + self._escaped_name + ".qubes-start.desktop"


class VMManager:
    """A helper class that watches for VM-related events"""

    def __init__(self, qapp: qubesadmin.Qubes, dispatcher):
        self.qapp = qapp
        self.dispatcher = dispatcher
        self.new_vm_callbacks: List[Callable] = []

        self.vms: Dict[str, VMEntry] = {}

        for vm in self.qapp.domains:
            self.load_vm_from_name(vm.name)

        self.register_events()

    def register_new_vm_callback(self, func):
        """Register a callback to be executed whenever a VM is added."""
        self.new_vm_callbacks.append(func)
        for entry in self.vms.values():
            func(entry)

    def load_vm_from_name(self, vm_name: str) -> Optional[VMEntry]:
        """Get a VM entry corresponding to a VM name"""
        if vm_name in self.vms:
            return self.vms[vm_name]
        try:
            vm: QubesVM = self.qapp.domains[vm_name]
        except KeyError:
            return None
        try:
            if vm.features.check_with_template("internal", False):
                return None
        except qubesadmin.exc.QubesDaemonAccessError:
            pass

        return self._add_vm(vm)

    def _add_vm(self, vm) -> Optional[VMEntry]:
        try:
            entry = VMEntry(vm)
        except Exception:  # pylint: disable=broad-except
            # a wrapper, to make absolutely sure dispatcher is not crashed
            # by a rogue Exception
            return None
        self.vms[vm.name] = entry
        for func in self.new_vm_callbacks:
            func(entry)
        return entry

    def _add_domain(self, _submitter, _event, vm, **_kwargs):
        self.load_vm_from_name(vm)

    def _remove_domain(self, _submitter, _event, vm, **_kwargs):
        vm_entry = self.vms.get(vm)
        if vm_entry:
            for child in vm_entry.entries:
                try:
                    child.get_parent().remove(child)
                except Exception:  # pylint: disable=broad-except
                    # a wrapper, to make absolutely sure dispatcher is not
                    # crashed by a rogue Exception
                    return
            del self.vms[vm]

    def _update_domain_state(self, vm_name, event, **_kwargs):
        vm_entry = self.load_vm_from_name(vm_name)
        if not vm_entry:
            return

        if event in constants.STATE_DICTIONARY:
            state = constants.STATE_DICTIONARY[event]
            vm_entry.power_state = state

    def _update_domain_property(self, vm_name, event, newvalue, *_args, **_kwargs):
        vm_entry = self.load_vm_from_name(vm_name)

        if not vm_entry:
            return

        if newvalue == "False":
            newvalue = False

        try:
            if event == "property-set:label":
                vm_entry.vm_icon_name = newvalue
            elif event == "property-set:netvm":
                vm_entry.has_network = vm_entry.vm.is_networked()
            elif event == "property-set:template_for_dispvms":
                vm_entry.is_dispvm_template = newvalue
        except Exception:  # pylint: disable=broad-except
            # dispatcher functions cannot raise any Exception, because
            # it will disable any future event handling
            pass

    def _update_domain_feature(self, vm, _event, feature=None, value=None, **_kwargs):
        vm_entry = self.load_vm_from_name(vm)

        if not vm_entry:
            return

        if value == "False":
            value = False
        value = bool(value)

        try:
            if feature == "internal":
                vm_entry.internal = value
                for derived in self.qapp.domains:
                    if not getattr(derived, "template", None) == vm:
                        continue
                    derived_vm_entry = self.load_vm_from_name(derived)
                    if derived_vm_entry:
                        derived_vm_entry.internal = value
            if feature == "servicevm":
                vm_entry.service_vm = value
            if feature == "appmenus-dispvm":
                vm_entry.show_dispvm_template_in_apps = value
        except Exception:  # pylint: disable=broad-except
            # dispatcher functions cannot raise any Exception, because
            # it will disable any future event handling
            pass

        for entry in vm_entry.entries:
            # try to fix filtering, if appropriate
            try:
                entry.get_parent().invalidate_filter()
            except Exception:  # pylint: disable=broad-except
                # a wrapper, to make absolutely sure dispatcher is not
                # crashed by a rogue Exception
                continue

    def register_events(self):
        """Register handlers for all relevant VM events."""
        self.dispatcher.add_handler("domain-pre-start", self._update_domain_state)
        self.dispatcher.add_handler("domain-start", self._update_domain_state)
        self.dispatcher.add_handler("domain-start-failed", self._update_domain_state)
        self.dispatcher.add_handler("domain-paused", self._update_domain_state)
        self.dispatcher.add_handler("domain-unpaused", self._update_domain_state)
        self.dispatcher.add_handler("domain-shutdown", self._update_domain_state)
        self.dispatcher.add_handler("domain-pre-shutdown", self._update_domain_state)
        self.dispatcher.add_handler("domain-shutdown-failed", self._update_domain_state)

        self.dispatcher.add_handler("domain-add", self._add_domain)
        self.dispatcher.add_handler("domain-delete", self._remove_domain)

        self.dispatcher.add_handler("property-set:netvm", self._update_domain_property)
        self.dispatcher.add_handler("property-set:label", self._update_domain_property)
        self.dispatcher.add_handler(
            "property-set:template_for_dispvms", self._update_domain_property
        )
        self.dispatcher.add_handler(
            "domain-feature-set:servicevm", self._update_domain_feature
        )
        self.dispatcher.add_handler(
            "domain-feature-delete:servicevm", self._update_domain_feature
        )
        self.dispatcher.add_handler(
            "domain-feature-set:appmenus-dispvm", self._update_domain_feature
        )
        self.dispatcher.add_handler(
            "domain-feature-delete:appmenus-dispvm", self._update_domain_feature
        )
        self.dispatcher.add_handler(
            "domain-feature-set:internal", self._update_domain_feature
        )
        self.dispatcher.add_handler(
            "domain-feature-delete:internal", self._update_domain_feature
        )
