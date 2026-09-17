# -*- coding: utf-8 -*-
"""Pagina de cuarentena."""

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ...backend.quarantine import QuarantineManager  # noqa: E402
from ...config import Config  # noqa: E402


class QuarantinePage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._config = Config()
        self._quarantine = QuarantineManager(self._config["quarantine_dir"])

        self._build_header()
        self._build_list()
        self._build_actions()

    def _make_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("category-title")
        label.set_halign(Gtk.Align.START)
        label.set_margin_bottom(6)
        return label

    def _build_header(self):
        self.pack_start(self._make_title("Cuarentena"), False, False, 0)

    def _build_list(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(4)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(360)
        scroller.set_margin_start(12)
        scroller.set_margin_end(12)
        scroller.set_margin_top(12)
        scroller.set_margin_bottom(6)

        self.store = Gtk.ListStore(str, str, str, str)
        self.view = Gtk.TreeView(model=self.store)
        self.view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        for idx, title in enumerate(("Archivo original", "Firma", "Fecha", "Tamano")):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=idx)
            column.set_expand(idx == 0)
            self.view.append_column(column)
        scroller.add(self.view)
        card.pack_start(scroller, True, True, 0)

        empty = Gtk.Label(label="La cuarentena esta vacia.")
        empty.get_style_context().add_class("metric-label")
        self._empty_label = empty
        card.pack_start(empty, False, False, 0)
        self.pack_start(card, True, True, 0)

    def _build_actions(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(4)

        self.restore_button = Gtk.Button(label="Restaurar seleccionados")
        self.restore_button.connect("clicked", self._on_restore)
        row.pack_start(self.restore_button, False, False, 0)

        self.delete_button = Gtk.Button(label="Eliminar seleccionados")
        self.delete_button.get_style_context().add_class("destructive-action")
        self.delete_button.connect("clicked", self._on_delete)
        row.pack_start(self.delete_button, False, False, 0)

        self.delete_all_button = Gtk.Button(label="Vaciar cuarentena")
        self.delete_all_button.connect("clicked", self._on_delete_all)
        row.pack_start(self.delete_all_button, False, False, 0)

        self.pack_start(row, False, False, 0)

    def _selected_ids(self):
        model, paths = self.view.get_selection().get_selected_rows()
        ids = []
        for path in paths:
            row = model[path]
            ids.append(row[2])  # fecha/time usado como id unico
        return ids

    def refresh(self):
        self.store.clear()
        entries = self._quarantine.list()
        for entry in entries:
            self.store.append([
                entry.get("original", ""),
                entry.get("signature", ""),
                entry.get("date", ""),
                self._human_size(entry.get("size", 0)),
            ])
        self._empty_label.set_visible(not entries)

    @staticmethod
    def _human_size(size):
        size = float(size)
        for unit in ("B", "KiB", "MiB", "GiB"):
            if size < 1024:
                return "{0:.1f} {1}".format(size, unit)
            size /= 1024.0
        return "{0:.1f} GiB".format(size)

    def _on_restore(self, button):
        entries = self._quarantine.list()
        model, paths = self.view.get_selection().get_selected_rows()
        restored = 0
        for path in paths:
            idx = path.get_indices()[0]
            if idx < len(entries):
                if self._quarantine.restore(entries[idx]["id"]):
                    restored += 1
        self._message("Se restauraron {0} archivo(s).".format(restored))
        self.refresh()

    def _on_delete(self, button):
        entries = self._quarantine.list()
        model, paths = self.view.get_selection().get_selected_rows()
        deleted = 0
        for path in paths:
            idx = path.get_indices()[0]
            if idx < len(entries):
                if self._quarantine.delete(entries[idx]["id"]):
                    deleted += 1
        self._message("Se eliminaron {0} archivo(s).".format(deleted))
        self.refresh()

    def _on_delete_all(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="¿Vaciar la cuarentena?",
        )
        dialog.format_secondary_text(
            "Se eliminaran definitivamente todos los archivos en cuarentena. "
            "Esta accion no se puede deshacer."
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self._quarantine.delete_all()
            self._message("Cuarentena vaciada.")
            self.refresh()

    def _message(self, text):
        try:
            from ...notifier import notify

            notify("Antivinux", text)
        except Exception:
            pass

    def on_show_page(self):
        self.refresh()