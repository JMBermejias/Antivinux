# -*- coding: utf-8 -*-
"""Pagina de ajustes."""

import os
import shutil
import subprocess

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ...config import Config, DEFAULTS, CONFIG_DIR  # noqa: E402


class SettingsPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._config = Config()

        self._build_header()
        self._build_scan_prefs()
        self._build_database_prefs()
        self._build_notifications()
        self._build_reset()

    def _make_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("category-title")
        label.set_halign(Gtk.Align.START)
        label.set_margin_bottom(6)
        return label

    def _build_header(self):
        self.pack_start(self._make_title("Ajustes"), False, False, 0)

    def _card(self, title_text):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(4)

        title = Gtk.Label(label=title_text)
        title.get_style_context().add_class("category-title")
        title.set_halign(Gtk.Align.START)
        title.set_margin_start(14)
        title.set_margin_top(12)
        card.pack_start(title, False, False, 0)
        return card

    def _build_scan_prefs(self):
        card = self._card("Preferencias de analisis")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(14)
        row.set_margin_bottom(12)

        self.archive_check = Gtk.CheckButton(label="Analizar archivos comprimidos")
        self.archive_check.set_active(self._config.get_bool("scan_archive"))
        row.pack_start(self.archive_check, False, False, 0)

        self.update_on_start_check = Gtk.CheckButton(
            label="Comprobar actualizaciones al iniciar"
        )
        self.update_on_start_check.set_active(self._config.get_bool("update_on_start"))
        row.pack_start(self.update_on_start_check, False, False, 0)
        card.pack_start(row, False, False, 0)
        self.pack_start(card, False, False, 0)

    def _build_database_prefs(self):
        card = self._card("Base de datos de virus (ClamAV)")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        box.set_margin_bottom(12)

        info = Gtk.Label(
            label="Definiciones gestionadas por freshclam desde los repositorios de ClamAV:\n"
            "main.cvd, daily.cvd y bytecode.cvd."
        )
        info.set_halign(Gtk.Align.START)
        info.get_style_context().add_class("metric-label")
        box.pack_start(info, False, False, 0)

        open_view = Gtk.Button(label="Abrir carpeta de definiciones")
        open_view.set_halign(Gtk.Align.START)
        open_view.connect("clicked", self._on_open_db)
        box.pack_start(open_view, False, False, 0)

        card.pack_start(box, False, False, 0)
        self.pack_start(card, False, False, 0)

    def _build_notifications(self):
        card = self._card("Notificaciones y registro")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(14)
        row.set_margin_end(14)
        row.set_margin_bottom(12)

        self.notifications_check = Gtk.CheckButton(label="Mostrar notificaciones de escritorio")
        self.notifications_check.set_active(self._config.get_bool("show_notifications"))
        row.pack_start(self.notifications_check, False, False, 0)
        card.pack_start(row, False, False, 0)

        self.pack_start(card, False, False, 0)

    def _build_reset(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(10)
        row.set_margin_top(8)
        row.set_margin_bottom(8)

        open_log = Gtk.Button(label="Abrir registro")
        open_log.set_halign(Gtk.Align.START)
        open_log.connect("clicked", self._on_open_log)
        row.pack_start(open_log, False, False, 0)

        reset = Gtk.Button(label="Restaurar ajustes por defecto")
        reset.set_halign(Gtk.Align.START)
        reset.connect("clicked", self._on_reset)
        row.pack_start(reset, False, False, 0)

        self.save_button = Gtk.Button(label="Guardar ajustes")
        self.save_button.get_style_context().add_class("suggested-action")
        self.save_button.connect("clicked", self._on_save)
        row.pack_end(self.save_button, False, False, 0)
        self.pack_start(row, False, False, 0)

    def _on_open_db(self, button):
        from ...backend import find_database_dir

        self._open_folder(find_database_dir())

    def _on_open_log(self, button):
        self._open_folder(CONFIG_DIR)

    def _open_folder(self, path):
        if not os.path.isdir(path):
            return
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen([opener, path])

    def _on_save(self, button):
        self._config["scan_archive"] = "true" if self.archive_check.get_active() else "false"
        self._config["update_on_start"] = "true" if self.update_on_start_check.get_active() else "false"
        self._config["show_notifications"] = "true" if self.notifications_check.get_active() else "false"
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Ajustes guardados",
        )
        dialog.format_secondary_text("La configuracion se guardo en {0}".format(self._config.path))
        dialog.run()
        dialog.destroy()

    def _on_reset(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="¿Restaurar ajustes por defecto?",
        )
        dialog.format_secondary_text("Se perderan los valores actuales de la configuracion.")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self._config.parser["antivinux"] = dict(DEFAULTS)
            self._config.save()
            self.refresh()

    def refresh(self):
        self.archive_check.set_active(self._config.get_bool("scan_archive"))
        self.update_on_start_check.set_active(self._config.get_bool("update_on_start"))
        self.notifications_check.set_active(self._config.get_bool("show_notifications"))

    def on_show_page(self):
        self.refresh()