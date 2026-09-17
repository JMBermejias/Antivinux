# -*- coding: utf-8 -*-
"""Prueba de arranque de la interfaz grafica.

Construye la ventana principal con GTK real para detectar errores de API
(por ejemplo el uso de metodos inexistentes) que no se ven al compilar.
Se omite automaticamente si GTK 3 no esta disponible. Requiere un servidor
grafico, por lo que en integracion continua se ejecuta bajo Xvfb.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk  # noqa: E402

    from antivinux.ui.window import AntivinuxWindow, CSS  # noqa: E402

    HAVE_GTK = True
except Exception:  # pragma: no cover - depende del entorno
    HAVE_GTK = False


@unittest.skipUnless(HAVE_GTK, "GTK 3 no esta disponible")
class WindowSmokeTests(unittest.TestCase):
    def test_css_is_valid(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode("utf-8"))

    def test_window_builds(self):
        win = AntivinuxWindow()
        win.show_all()
        self.assertIsNotNone(win.pages["home"])
        self.assertEqual(set(win.pages), set(win.sidebar_buttons))
        win.destroy()

    def test_navigation_changes_page(self):
        win = AntivinuxWindow()
        win.show_all()
        win.navigate_to("settings")
        self.assertEqual(win.stack.get_visible_child_name(), "settings")
        win.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
