# -*- coding: utf-8 -*-
"""Pagina de analisis con seleccion de destino y resultados."""

import os
import threading
import time

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ...backend.clamav import Scanner, EVENT_START, EVENT_PROGRESS, EVENT_FOUND, EVENT_ERROR, EVENT_DONE  # noqa: E402
from ...backend.quarantine import QuarantineManager  # noqa: E402
from ...config import Config  # noqa: E402


class ScanPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._config = Config()
        self._quarantine = QuarantineManager(self._config["quarantine_dir"])
        self._scanner = None
        self._found_files = []

        self._build_header()
        self._build_target_selector()
        self._build_progress()
        self._build_results()

    def _make_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("category-title")
        label.set_halign(Gtk.Align.START)
        label.set_margin_bottom(6)
        return label

    def _build_header(self):
        self.pack_start(self._make_title("Analisis del sistema"), False, False, 0)

    def _build_target_selector(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("metric-card")
        card.set_margin_top(4)
        card.set_margin_start(10)
        card.set_margin_end(10)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(12)
        row.set_margin_top(12)
        row.set_margin_bottom(12)
        row.set_margin_end(12)

        self.target_entry = Gtk.Entry()
        self.target_entry.set_text(self._config["last_scan_path"] or os.path.expanduser("~"))
        self.target_entry.set_width_chars(48)
        row.pack_start(self.target_entry, True, True, 0)

        browse = Gtk.Button(label="Examinar")
        browse.connect("clicked", self._on_browse)
        row.pack_start(browse, False, False, 0)

        self.scan_button = Gtk.Button(label="Analizar ahora")
        self.scan_button.get_style_context().add_class("suggested-action")
        self.scan_button.connect("clicked", self._on_scan)
        row.pack_start(self.scan_button, False, False, 0)

        self.cancel_button = Gtk.Button(label="Cancelar")
        self.cancel_button.set_sensitive(False)
        self.cancel_button.connect("clicked", self._on_cancel)
        row.pack_start(self.cancel_button, False, False, 0)

        card.pack_start(row, False, False, 0)

        options = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        options.set_margin_start(12)
        options.set_margin_bottom(12)
        self.recursive_check = Gtk.CheckButton(label="Escaneo recursivo")
        self.recursive_check.set_active(True)
        options.pack_start(self.recursive_check, False, False, 0)
        self.follow_links_check = Gtk.CheckButton(label="Seguir enlaces")
        options.pack_start(self.follow_links_check, False, False, 0)
        card.pack_start(options, False, False, 0)

        self.pack_start(card, False, False, 0)

    def _build_progress(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(6)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_valign(Gtk.Align.CENTER)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_margin_start(12)
        self.progress_bar.set_margin_end(12)
        self.progress_bar.set_margin_top(12)
        card.pack_start(self.progress_bar, False, False, 0)

        self.scan_status = Gtk.Label(label="Listo para analizar.")
        self.scan_status.get_style_context().add_class("metric-label")
        self.scan_status.set_halign(Gtk.Align.START)
        self.scan_status.set_margin_start(12)
        self.scan_status.set_margin_bottom(12)
        card.pack_start(self.scan_status, False, False, 0)

        self.pack_start(card, False, False, 0)

    def _build_results(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(6)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label="Resultados del analisis")
        title.get_style_context().add_class("category-title")
        title.set_halign(Gtk.Align.START)
        header_row.pack_start(title, True, True, 0)

        self.result_pill = Gtk.Label(label="--")
        self.result_pill.get_style_context().add_class("statuspill")
        self.result_pill.set_halign(Gtk.Align.END)
        header_row.pack_end(self.result_pill, False, False, 0)

        header_row.set_margin_start(14)
        header_row.set_margin_top(12)
        card.pack_start(header_row, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(180)
        scroller.set_margin_start(12)
        scroller.set_margin_end(12)
        scroller.set_margin_top(6)

        self.store = Gtk.ListStore(str, str, str)
        self.results_view = Gtk.TreeView(model=self.store)
        for col_index, title_col in enumerate(("Archivo", "Firma", "Estado")):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title_col, renderer, text=col_index)
            column.set_expand(col_index == 0)
            self.results_view.append_column(column)
        self.results_view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        scroller.add(self.results_view)
        card.pack_start(scroller, True, True, 0)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_row.set_margin_start(12)
        action_row.set_margin_bottom(12)
        action_row.set_margin_top(6)

        self.quarantine_selected_button = Gtk.Button(label="Poner en cuarentena seleccionados")
        self.quarantine_selected_button.connect("clicked", self._on_quarantine_selected)
        action_row.pack_start(self.quarantine_selected_button, False, False, 0)

        self.export_button = Gtk.Button(label="Exportar informe")
        self.export_button.connect("clicked", self._on_export)
        action_row.pack_start(self.export_button, False, False, 0)

        card.pack_start(action_row, False, False, 0)
        self.pack_start(card, True, True, 0)

    def _pill_state(self, state):
        self.result_pill.get_style_context().remove_class("green")
        self.result_pill.get_style_context().remove_class("red")
        self.result_pill.get_style_context().remove_class("orange")
        self.result_pill.get_style_context().add_class(state)

    def _on_browse(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Selecciona un archivo o carpeta",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Abrir", Gtk.ResponseType.OK,
        )
        if dialog.run() == Gtk.ResponseType.OK:
            self.target_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _on_scan(self, button):
        target = self.target_entry.get_text().strip()
        if not target or not os.path.exists(target):
            self.scan_status.set_text("La ruta seleccionada no existe.")
            return
        self._config["last_scan_path"] = target
        self._found_files = []
        self.store.clear()
        self.scan_button.set_sensitive(False)
        self.cancel_button.set_sensitive(True)
        self.quarantine_selected_button.set_sensitive(False)
        self._pill_state("orange")
        self.result_pill.set_text("EN CURSO")
        self.scan_status.set_text("Analizando {0}...".format(target))

        self._scanner = Scanner()
        self._start_time = time.time()

        def on_event(event, data):
            if event == EVENT_FOUND:
                f = data.get("file", "")
                sig = data.get("signature", "FOUND")
                self._found_files.append({"file": f, "signature": sig})
                Gdk.threads_add_idle(
                    GLib.PRIORITY_DEFAULT,
                    lambda: self.store.append([f, sig, "INFECTADO"]),
                )
            elif event == EVENT_ERROR:
                Gdk.threads_add_idle(
                    GLib.PRIORITY_DEFAULT,
                    lambda: self.scan_status.set_text(str(data.get("message", ""))),
                )
            elif event == EVENT_DONE:
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, lambda: self._finish(data.get("result")))

        self._scanner.recursive = self.recursive_check.get_active()
        self._scanner.follow_links = self.follow_links_check.get_active()

        thread = threading.Thread(
            target=lambda: self._scanner.scan(target, on_event), daemon=True
        )
        thread.start()
        GLib.timeout_add(200, self._tick)

    def _tick(self):
        if self._scanner is None:
            return False
        elapsed = time.time() - self._start_time
        self.progress_bar.set_text("Analizando... {0:.0f}s".format(elapsed))
        self.progress_bar.pulse()
        return True

    def _on_cancel(self, button):
        if self._scanner:
            self._scanner.cancel()
        self.scan_status.set_text("Cancelando analisis...")

    def _finish(self, result):
        if self._scanner:
            self._scanner = None
        self.scan_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("")

        duration = getattr(result, "duration", 0.0)
        if result.infected:
            self._pill_state("red")
            self.result_pill.set_text("{0} AMENAZAS".format(result.infected))
            self.scan_status.set_text(
                "Analisis completado en {0:.1f}s: {1} archivos infectados.".format(
                    duration, result.infected
                )
            )
            self.quarantine_selected_button.set_sensitive(True)
        else:
            self._pill_state("green")
            self.result_pill.set_text("SIN AMENAZAS")
            self.scan_status.set_text(
                "Analisis completado en {0:.1f}s. No se encontraron amenazas.".format(duration)
            )

    def _on_quarantine_selected(self, button):
        model, paths = self.results_view.get_selection().get_selected_rows()
        if not paths and not self._found_files:
            return
        target = set()
        if paths:
            for path in paths:
                target.add(model[path][0])
        else:
            for item in self._found_files:
                target.add(item["file"])

        count = 0
        for file_path in target:
            signature = "FOUND"
            for item in self._found_files:
                if item["file"] == file_path:
                    signature = item["signature"]
                    break
            if self._quarantine.quarantine(file_path, signature):
                count += 1
        self.scan_status.set_text("{0} archivo(s) puestos en cuarentena.".format(count))
        self._notify_count(count)

    def _notify_count(self, count):
        if not count:
            return
        try:
            from ...notifier import notify

            notify("Antivinux", "{0} archivos movidos a cuarentena.".format(count))
        except Exception:
            pass

    def _on_export(self, button):
        from ... import __version__

        dialog = Gtk.FileChooserDialog(
            title="Guardar informe",
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Guardar", Gtk.ResponseType.OK,
        )
        dialog.set_current_name("antivinux-informe-{0}.txt".format(
            time.strftime("%Y%m%d-%H%M%S")
        ))
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("Informe de analisis Antivinux {0}\n".format(__version__))
                    fh.write("Fecha: {0}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                    fh.write("Objetivo: {0}\n\n".format(self.target_entry.get_text()))
                    if self._found_files:
                        for item in self._found_files:
                            fh.write("{0}  [{1}]\n".format(item["file"], item["signature"]))
                    else:
                        fh.write("No se detectaron amenazas.\n")
                self.scan_status.set_text("Informe guardado en {0}".format(path))
            except OSError as exc:
                self.scan_status.set_text("Error al guardar: {0}".format(exc))
        dialog.destroy()

    def on_show_page(self):
        self.target_entry.set_text(self._config["last_scan_path"] or os.path.expanduser("~"))