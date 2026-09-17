#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arranque de Antivinux desde el sistema instalado (no en consola).

Si algo falla al iniciar, el error se escribe en
~/.cache/antivinux/error.log y se intenta mostrar un dialogo, de modo que
un fallo nunca quede en silencio al lanzar la aplicacion desde el icono.
"""

import datetime
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _error_log_path():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    directory = os.path.join(base, "antivinux")
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        return None
    return os.path.join(directory, "error.log")


def _log_traceback(text):
    path = _error_log_path()
    if not path:
        return None
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(
                "\n===== {0} =====\n{1}\n".format(
                    datetime.datetime.now().isoformat(timespec="seconds"), text
                )
            )
    except OSError:
        return None
    return path


def _show_dialog(title, message):
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
    except Exception:
        Gtk = None
    if Gtk is not None:
        try:
            dialog = Gtk.MessageDialog(
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text=title,
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
            return
        except Exception:
            pass
    import shutil
    import subprocess

    if shutil.which("zenity"):
        try:
            subprocess.run(
                ["zenity", "--error", "--title", title, "--text", message],
                check=False,
            )
            return
        except Exception:
            pass
    sys.stderr.write("{0}\n{1}\n".format(title, message))


def _fail(title, hint):
    text = traceback.format_exc()
    sys.stderr.write(text)
    log = _log_traceback(text)
    if log:
        hint += "\n\nDetalle guardado en:\n{0}".format(log)
    _show_dialog(title, hint)
    return 1


def main():
    try:
        from antivinux.__main__ import main as run
    except Exception:
        return _fail(
            "Antivinux no pudo iniciarse",
            "No se pudieron cargar los componentes de Antivinux.\n\n"
            "Comprueba que estan instaladas las dependencias:\n"
            "  sudo apt install python3-gi gir1.2-gtk-3.0 clamav clamav-freshclam",
        )
    try:
        return run()
    except Exception:
        return _fail(
            "Antivinux ha fallado",
            "Se ha producido un error inesperado al iniciar la aplicacion.",
        )


if __name__ == "__main__":
    sys.exit(main())
