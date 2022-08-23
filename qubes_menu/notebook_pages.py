import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import qubesadmin.events

from .custom_widgets import ServiceVM
from .app_widgets import BaseAppEntry
from .utils import load_icon
from .desktop_file_manager import ApplicationInfo, DesktopFileManager
from .vm_page import VMPage
from .vm_manager import VMEntry, VMManager

class NotebookPages():
    def __init__(self,
                vm_manager: VMManager,
                notebook: Gtk.Notebook,
                desktop_file_manager: DesktopFileManager,
                dispatcher: qubesadmin.events.EventsDispatcher,
                service_vms_page: Gtk.ListBox, 
                qubes_settings_page: Gtk.ListBox):
    
        '''
        To set the vm pages below the favorite tab and above 
        the settings and vm services tab
        '''
        self.page_postion = 1

        self.vm_manager = vm_manager

        self.service_vms_page = service_vms_page
        self.qubes_settings_page = qubes_settings_page

        self.qubes_settings_page.connect('row-activated', self._app_clicked)

        self.notebook = notebook
        self.notebook.connect('switch-page', self._handle_page_switch)

        self.desktop_file_manager = desktop_file_manager
        self.dispatcher = dispatcher
        
        self.vm_manager.register_new_vm_callback(self._vm_callback)
        self.desktop_file_manager.register_callback(self._qube_settings_callback)
        
    def _vm_callback(self, vm_entry: VMEntry):
        """
        Callback to be performed on all newly loaded VMEntry instances.
        """
        if vm_entry:
            if vm_entry.service_vm:
                self.service_vms_page.add(ServiceVM(vm_entry))
            else:
                vm_page = VMPage(
                    vm_entry, self.desktop_file_manager, self.dispatcher
                )

                notebook_page_label = Gtk.Box()
                vm_icon = Gtk.Image.new_from_pixbuf(
                    load_icon(vm_entry.vm_icon_name, Gtk.IconSize.LARGE_TOOLBAR)
                )
                vm_label = Gtk.Label(vm_entry.vm_name)
                notebook_page_label.pack_start(vm_icon, False, True, 0)
                notebook_page_label.pack_start(vm_label, False, True, 10)

                vm_entry.updater = vm_page.update_contents

                self.notebook.insert_page(vm_page, notebook_page_label, self.page_postion)
                notebook_page_label.show_all()
                self.page_postion += 1

    def _app_clicked(self, _widget, row: BaseAppEntry):
        row.run_app(None)

    def _qube_settings_callback(self, app_info: ApplicationInfo):
   
        if 'qubes' in app_info.entry_name\
            and not app_info.is_qubes_specific()\
            and 'X-XFCE-SettingsDialog' in app_info.categories:
            entry = BaseAppEntry(app_info)
            app_info.entries.append(entry)
            self.qubes_settings_page.add(entry)

    def _handle_page_switch(self, _widget, page: VMPage, page_num):
        pass