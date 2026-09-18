# -*- coding: utf-8 -*-
"""Pagina de ajustes."""

import os
import shutil
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ... import __version__  # noqa: E402
from ...backend import appupdate  # noqa: E402
from ...config import Config, DEFAULTS, CONFIG_DIR  # noqa: E402


class SettingsPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._config = Config()
        self._pending_update = None

        self._build_header()
        self._build_scan_prefs()
        self._build_database_prefs()
        self._build_app_updates()
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

    def _build_app_updates(self):
        card = self._card("Actualizaciones de Antivinux")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_bottom(12)

        self.app_version_label = Gtk.Label(
            label="Version instalada: {0}".format(__version__)
        )
        self.app_version_label.set_halign(Gtk.Align.START)
        self.app_version_label.get_style_context().add_class("metric-label")
        box.pack_start(self.app_version_label, False, False, 0)

        self.app_status_label = Gtk.Label(
            label="Pulsa en Buscar actualizaciones para comprobar si hay una "
            "version nueva del programa."
        )
        self.app_status_label.set_halign(Gtk.Align.START)
        self.app_status_label.set_line_wrap(True)
        self.app_status_label.get_style_context().add_class("metric-label")
        box.pack_start(self.app_status_label, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.app_check_button = Gtk.Button(label="Buscar actualizaciones")
        self.app_check_button.connect("clicked", self._on_check_app_update)
        row.pack_start(self.app_check_button, False, False, 0)

        self.app_install_button = Gtk.Button(label="Descargar e instalar")
        self.app_install_button.get_style_context().add_class("suggested-action")
        self.app_install_button.set_sensitive(False)
        self.app_install_button.connect("clicked", self._on_install_app_update)
        row.pack_start(self.app_install_button, False, False, 0)

        self.app_open_button = Gtk.Button(label="Abrir pagina de descarga")
        self.app_open_button.set_sensitive(False)
        self.app_open_button.connect("clicked", self._on_open_release)
        row.pack_start(self.app_open_button, False, False, 0)
        box.pack_start(row, False, False, 0)

        self.check_app_updates_check = Gtk.CheckButton(
            label="Buscar actualizaciones del programa al iniciar"
        )
        self.check_app_updates_check.set_active(
            self._config.get_bool("check_app_updates")
        )
        box.pack_start(self.check_app_updates_check, False, False, 0)

        card.pack_start(box, False, False, 0)
        self.pack_start(card, False, False, 0)

    def _on_check_app_update(self, button):
        self.app_check_button.set_sensitive(False)
        self.app_install_button.set_sensitive(False)
        self.app_open_button.set_sensitive(False)
        self.app_status_label.set_text("Buscando actualizaciones...")
        self._pending_update = None
        threading.Thread(target=self._worker_check_update, daemon=True).start()

    def _worker_check_update(self):
        info = appupdate.check_for_update(__version__)
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, self._apply_update_info, info)

    def _apply_update_info(self, info):
        self.app_check_button.set_sensitive(True)
        if info.get("error"):
            self.app_status_label.set_text(
                "No se pudo comprobar la actualizacion: {0}".format(info["error"])
            )
            return
        if info.get("available"):
            self._pending_update = info
            self.app_status_label.set_text(
                "Hay una version nueva disponible: {0} (tienes {1}).".format(
                    info["latest"], info["current"]
                )
            )
            self.app_install_button.set_sensitive(True)
            self.app_open_button.set_sensitive(bool(info.get("html_url")))
        else:
            self.app_status_label.set_text(
                "Esta es la ultima version disponible ({0}).".format(info["current"])
            )

    def start_update(self, info):
        """Inicia la instalacion de una actualizacion ya detectada."""
        if not info or not info.get("available"):
            return
        self._pending_update = info
        self.app_status_label.set_text(
            "Hay una version nueva disponible: {0} (tienes {1}).".format(
                info["latest"], info["current"]
            )
        )
        self.app_open_button.set_sensitive(bool(info.get("html_url")))
        self._on_install_app_update(None)

    def _on_install_app_update(self, button):
        info = self._pending_update
        if not info:
            return
        self.app_install_button.set_sensitive(False)
        self.app_check_button.set_sensitive(False)
        self.app_status_label.set_text(
            "Descargando {0}...".format(info.get("asset_name") or "el paquete")
        )
        threading.Thread(
            target=self._worker_install_update, args=(info,), daemon=True
        ).start()

    def _download_progress(self, done, total):
        if not total:
            return
        percent = int(done * 100 / total)
        Gdk.threads_add_idle(
            GLib.PRIORITY_DEFAULT,
            self.app_status_label.set_text,
            "Descargando... {0}%".format(percent),
        )

    def _worker_install_update(self, info):
        try:
            path = appupdate.download_update(info, progress_cb=self._download_progress)
        except Exception as exc:
            Gdk.threads_add_idle(
                GLib.PRIORITY_DEFAULT,
                self._install_failed,
                "No se pudo descargar la actualizacion: {0}".format(exc),
            )
            return
        Gdk.threads_add_idle(
            GLib.PRIORITY_DEFAULT,
            self.app_status_label.set_text,
            "Instalando... se solicitara tu contrasena.",
        )
        ok, message = appupdate.install_package(path)
        appupdate.cleanup(path)
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, self._install_finished, ok, message)

    def _install_failed(self, text):
        self.app_check_button.set_sensitive(True)
        self.app_install_button.set_sensitive(True)
        self.app_status_label.set_text(text)

    def _install_finished(self, ok, message):
        self.app_check_button.set_sensitive(True)
        if ok:
            self.app_status_label.set_text(
                "Actualizacion instalada. Reinicia Antivinux para aplicar los cambios."
            )
            self.app_install_button.set_sensitive(False)
            self.app_open_button.set_sensitive(False)
            self._pending_update = None
            self._prompt_restart()
        else:
            lines = (message or "").strip().splitlines()
            summary = lines[-1] if lines else "error desconocido"
            self.app_status_label.set_text(
                "No se pudo instalar la actualizacion: {0}".format(summary)
            )
            self.app_install_button.set_sensitive(True)

    def _on_open_release(self, button):
        info = self._pending_update or {}
        if info.get("html_url"):
            opener = shutil.which("xdg-open")
            if opener:
                subprocess.Popen([opener, info["html_url"]])

    def _prompt_restart(self):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Reiniciar Antivinux",
        )
        dialog.format_secondary_text(
            "La actualizacion se aplicara al reiniciar la aplicacion. "
            "¿Quieres reiniciarla ahora?"
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self._restart_app()

    def _restart_app(self):
        launcher = shutil.which("antivinux") or "/usr/bin/antivinux"
        try:
            subprocess.Popen([launcher])
        except Exception:
            return
        Gtk.main_quit()

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
        self._config["check_app_updates"] = "true" if self.check_app_updates_check.get_active() else "false"
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
        self.check_app_updates_check.set_active(
            self._config.get_bool("check_app_updates")
        )
        self.app_version_label.set_text(
            "Version instalada: {0}".format(__version__)
        )

    def on_show_page(self):
        self.refresh()
