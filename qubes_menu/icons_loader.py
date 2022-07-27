import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from .utils import load_icon
from . import constants

class IconsLoader:
    def __init__(self):
        self.BOOKMARK_BLACK = Gtk.Image.new_from_pixbuf(
            load_icon(constants.BOOKMARK_BLACK, Gtk.IconSize.LARGE_TOOLBAR)
        )
        self.BOOKMARK_FILL_BLACK = Gtk.Image.new_from_pixbuf(
            load_icon(constants.BOOKMARK_FILL_BLACK, Gtk.IconSize.LARGE_TOOLBAR)
        )

        self.BOOKMARK_FILL_WHITE = Gtk.Image.new_from_pixbuf(
            load_icon(constants.BOOKMARK_FILL_WHITE, Gtk.IconSize.LARGE_TOOLBAR)
        )
        self.BOOKMARK_WHITE = Gtk.Image.new_from_pixbuf(
            load_icon(constants.BOOKMARK_WHITE, Gtk.IconSize.LARGE_TOOLBAR)
        )