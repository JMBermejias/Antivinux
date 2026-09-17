# -*- coding: utf-8 -*-
"""Pagina de actualizaciones de la base de datos con freshclam."""

import os
import time

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ...backend import check_database_status, parse_cvd_header  # noqa: E402
from ...backend.update import Updater, UPDATE_EVENT_STATUS, UPDATE_EVENT_LINE, UPDATE_EVENT_DONE  # noqa: E402


class UpdatePage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._updater = None

        self._build_header()
        self._build_info_cards()
        self._build_actions()
        self._build_log()

    def _make_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("category-title")
        label.set_halign(Gtk.Align.START)
        label.set_margin_bottom(6)
        return label

    def _build_header(self):
        self.pack_start(self._make_title("Actualizaciones de la base de datos"), False, False, 0)

    def _build_info_cards(self):
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)

        self.db_files_label = self._info_card(grid, 0, 0, "Archivos", "Definiciones")
        self.db_dir_label = self._info_card(grid, 0, 1, "Directorio", "Ubicacion de la base")
        self.db_age_label = self._info_card(grid, 1, 0, "Edad", "De la base diaria")
        self.last_check_label = self._info_card(grid, 1, 1, "Ultima revision", "Estado")
        self.pack_start(grid, False, False, 0)

    def _info_card(self, grid, row, col, value, label):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("metric-card")
        card.set_size_request(-1, 80)
        card.set_margin_top(4)
        card.set_margin_bottom(4)

        value_label = Gtk.Label(label=value)
        value_label.get_style_context().add_class("metric-value")
        value_label.set_halign(Gtk.Align.START)
        value_label.set_margin_start(16)
        value_label.set_margin_top(12)
        value_label.set_line_wrap(True)
        value_label.set_max_width_chars(38)
        card.pack_start(value_label, False, False, 0)

        info_label = Gtk.Label(label=label)
        info_label.get_style_context().add_class("metric-label")
        info_label.set_halign(Gtk.Align.START)
        info_label.set_margin_start(16)
        info_label.set_margin_top(2)
        info_label.set_margin_bottom(8)
        card.pack_start(info_label, False, False, 0)

        grid.attach(card, col, row, 1, 1)
        return value_label

    def _build_actions(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(6)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_margin_start(12)
        row.set_margin_top(12)
        row.set_margin_bottom(12)

        self.update_button = Gtk.Button(label="Buscar y aplicar actualizaciones")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self._on_update)
        row.pack_start(self.update_button, False, False, 0)

        self.cancel_button = Gtk.Button(label="Cancelar")
        self.cancel_button.connect("clicked", self._on_cancel)
        self.cancel_button.set_sensitive(False)
        row.pack_start(self.cancel_button, False, False, 0)

        self.status_pill = Gtk.Label(label="ESTADO")
        self.status_pill.get_style_context().add_class("statuspill")
        self.status_pill.set_halign(Gtk.Align.END)
        row.pack_end(self.status_pill, False, False, 0)

        card.pack_start(row, False, False, 0)
        self.pack_start(card, False, False, 0)

    def _build_log(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(6)

        title = Gtk.Label(label="Registro de freshclam")
        title.get_style_context().add_class("category-title")
        title.set_halign(Gtk.Align.START)
        title.set_margin_start(14)
        title.set_margin_top(12)
        card.pack_start(title, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(200)
        scroller.set_margin_start(12)
        scroller.set_margin_end(12)
        scroller.set_margin_top(4)
        scroller.set_margin_bottom(12)

        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.get_style_context().add_class("log-textview")
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroller.add(self.log_view)
        card.pack_start(scroller, True, True, 0)
        self.pack_start(card, True, True, 0)

    def _pill_state(self, state):
        self.status_pill.get_style_context().remove_class("green")
        self.status_pill.get_style_context().remove_class("red")
        self.status_pill.get_style_context().remove_class("orange")
        self.status_pill.get_style_context().add_class(state)

    def _append_log(self, text):
        self.log_buffer.insert(self.log_buffer.get_end_iter(), text + "\n")

    def _on_update(self, button):
        self.update_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self._pill_state("orange")
        self.status_pill.set_text("ACTUALIZANDO")
        self._append_log("\n== Inicio de actualizacion: {0} ==\n".format(
            time.strftime("%Y-%m-%d %H:%M:%S")
        ))
        self._updater = Updater()

        def on_event(event, data):
            if event == UPDATE_EVENT_STATUS:
                text = data.get("text", "")
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, lambda: self._status_text(text))
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, lambda: self._append_log(text))
            elif event == UPDATE_EVENT_LINE:
                lines = data.get("lines", [])
                for line in lines:
                    Gdk.threads_add_idle(
                        GLib.PRIORITY_DEFAULT, lambda l=line: self._append_log(l.rstrip("\n"))
                    )
            elif event == UPDATE_EVENT_DONE:
                Gdk.threads_add_idle(
                    GLib.PRIORITY_DEFAULT, lambda: self._finish(data.get("status"))
                )

        import threading

        thread = threading.Thread(
            target=lambda: self._updater.update(on_event), daemon=True
        )
        thread.start()

    def _status_text(self, text):
        self.status_bar_text = text

    def _on_cancel(self, button):
        if self._updater:
            self._updater.cancel()
        self._append_log("Cancelando...")

    def _finish(self, status):
        self.update_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        if status == "ok":
            self._pill_state("green")
            self.status_pill.set_text("ACTUALIZADO")
        elif status == "uptodate":
            self._pill_state("green")
            self.status_pill.set_text("AL DIA")
        elif status == "cancelled":
            self._pill_state("orange")
            self.status_pill.set_text("CANCELADO")
        else:
            self._pill_state("red")
            self.status_pill.set_text("ERROR")
        self._append_log("== Fin de la operacion ({0}) ==\n".format(status))
        self.set_db_status(check_database_status())
        try:
            window = self.get_toplevel()
            if hasattr(window, "pages") and "home" in window.pages:
                window.pages["home"].refresh()
        except Exception:
            pass

    def set_db_status(self, status):
        files = status["files"]
        db_dir = status["db_dir"]
        self.db_files_label.set_text("/".join(sorted(f.lower() for f in files)) or "ninguno")
        self.db_dir_label.set_text(db_dir)
        self.db_age_label.set_text(self._age_text(db_dir))
        self.last_check_label.set_text(self._last_check_text(status))

    def _age_text(self, db_dir):
        for name in ("daily.cvd", "daily.cld"):
            path = os.path.join(db_dir, name)
            if os.path.isfile(path):
                age = time.time() - os.path.getmtime(path)
                return self._human_age(age)
        return "No disponible"

    @staticmethod
    def _human_age(seconds):
        if seconds < 3600:
            return "{0} min".format(int(seconds // 60))
        if seconds < 86400:
            return "{0} h".format(int(seconds // 3600))
        return "{0} dias".format(int(seconds // 86400))

    def _last_check_text(self, status):
        daily = [f for f in status["files"] if f.lower().startswith("daily")]
        if not daily:
            return "Base diaria no presente"
        header = parse_cvd_header(os.path.join(status["db_dir"], daily[0]))
        if header and header["date"]:
            return "Compilada el {0}".format(header["date"])
        return "Version {0}".format(header["version"] if header else "?")

    def on_show_page(self):
        self.set_db_status(check_database_status())