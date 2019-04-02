"""
This module contains user interface related code, such as the
main screen and diagram windows.
"""

from gi.repository import Gtk, Gdk
import pkg_resources
import os.path

icon_theme = Gtk.IconTheme.get_default()
icon_theme.append_search_path(
    os.path.abspath(pkg_resources.resource_filename("gaphor.ui", "pixmaps"))
)

import re


def _repl(m):
    v = m.group(1).lower()
    return len(v) == 1 and v or "%c-%c" % tuple(v)


_repl.expr = "(.?[A-Z])"


def icon_for_element(element):
    return re.sub(_repl.expr, _repl, type(element).__name__)


# Set style for model canvas
css_provider = Gtk.CssProvider.new()
screen = Gdk.Display.get_default().get_default_screen()

Gtk.StyleContext.add_provider_for_screen(
    screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)
css_provider.load_from_data("#diagram-tab { background: white }".encode("utf-8"))
