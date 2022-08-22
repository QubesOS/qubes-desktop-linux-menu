import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import qubesadmin.events

from .utils import load_icon
from .desktop_file_manager import DesktopFileManager
from .vm_page import VMPage
from .vm_manager import VMEntry, VMManager

class NotebookPages():
    def __init__(self,
                vm_manager: VMManager,
                notebook: Gtk.Notebook,
                desktop_file_manager: DesktopFileManager,
                dispatcher: qubesadmin.events.EventsDispatcher):

        self.vm_manager = vm_manager
        self.notebook = notebook

        self.desktop_file_manager = desktop_file_manager
        self.dispatcher = dispatcher
        
        self.vm_manager.register_new_vm_callback(self._vm_callback)
        
    def _vm_callback(self, vm_entry: VMEntry):
        """
        Callback to be performed on all newly loaded VMEntry instances.
        """
        if vm_entry:
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

            vm_entry.vm_page = vm_page

            self.notebook.append_page(vm_page, notebook_page_label)
            notebook_page_label.show_all()