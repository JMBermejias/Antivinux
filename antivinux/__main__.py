#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Punto de entrada de Antivinux."""

import os
import sys

import gi

gi.require_version("Gtk", "3.0")


def _parse_args(argv):
    options = {"scan_home": False, "update": False, "page": None}
    for arg in argv[1:]:
        if arg in ("--scan-home", "-s"):
            options["scan_home"] = True
        elif arg in ("--update", "-u"):
            options["update"] = True
        elif arg == "--version":
            from . import __version__

            print("Antivinux {0}".format(__version__))
            sys.exit(0)
        elif arg == "--help":
            print(
                "Uso: antivinux [OPCIONES]\n\n"
                "  --scan-home, -s   Abre la aplicacion en la pagina de analisis\n"
                "  --update, -u      Abre la pagina de actualizaciones\n"
                "  --version         Muestra la version\n"
                "  --help            Muestra esta ayuda\n"
            )
            sys.exit(0)
        elif arg.startswith("--page="):
            options["page"] = arg.split("=", 1)[1]
    return options


def main(argv=None):
    from gi.repository import Gtk

    argv = argv if argv is not None else sys.argv
    options = _parse_args(argv)

    from .ui.window import AntivinuxWindow

    win = AntivinuxWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()

    if options["page"]:
        win.navigate_to(options["page"])
    elif options["scan_home"]:
        win.navigate_to("scan")
    elif options["update"]:
        win.navigate_to("update")

    if win.config.get_bool("check_app_updates"):
        win.check_app_updates()

    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())