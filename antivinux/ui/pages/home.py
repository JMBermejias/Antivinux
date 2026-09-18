# -*- coding: utf-8 -*-
"""Pagina de inicio con el estado general de proteccion."""

import os
import threading

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from ...backend import check_database_status, is_clamav_installed, parse_cvd_header, system_info  # noqa: E402
from ...backend.clamav import Scanner, EVENT_FOUND, EVENT_ERROR, EVENT_DONE  # noqa: E402
from ...config import Config  # noqa: E402
from ...backend.quarantine import QuarantineManager  # noqa: E402


class HomePage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)

        self._config = Config()
        self._build_title()
        self._build_status_card()
        self._build_metrics()
        self._build_actions()
        self._build_banner()

    def _make_title(self, text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("category-title")
        label.set_halign(Gtk.Align.START)
        label.set_margin_bottom(6)
        return label

    def _build_title(self):
        self._title = self._make_title("Panel de control")
        self.pack_start(self._title, False, False, 0)

    def _build_status_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.get_style_context().add_class("metric-card")
        card.set_margin_top(4)
        card.set_size_request(-1, 96)
        card.set_margin_start(10)
        card.set_margin_end(10)

        icon = Gtk.Image.new_from_icon_name("security-high-symbolic", Gtk.IconSize.DIALOG)
        icon.set_margin_start(16)
        card.pack_start(icon, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(8)
        vbox.set_margin_top(18)
        vbox.set_margin_bottom(18)

        self.status_title = Gtk.Label(label="Comprobando estado...")
        self.status_title.get_style_context().add_class("category-title")
        self.status_title.set_halign(Gtk.Align.START)
        vbox.pack_start(self.status_title, False, False, 0)

        self.status_detail = Gtk.Label(label="")
        self.status_detail.get_style_context().add_class("metric-label")
        self.status_detail.set_halign(Gtk.Align.START)
        self.status_detail.set_line_wrap(True)
        vbox.pack_start(self.status_detail, True, True, 0)

        card.pack_start(vbox, True, True, 0)

        self.status_pill = Gtk.Label(label="--")
        self.status_pill.get_style_context().add_class("statuspill")
        self.status_pill.set_halign(Gtk.Align.CENTER)
        self.status_pill.set_valign(Gtk.Align.CENTER)
        self.status_pill.set_margin_end(16)
        card.pack_end(self.status_pill, False, False, 0)

        self.pack_start(card, False, False, 0)

    def _build_metrics(self):
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)

        self.signatures_value = self._metric_card(grid, 0, 0, "0", "Firmas de virus")
        self.last_update_value = self._metric_card(grid, 0, 1, "--", "Actualizacion")
        self.infected_value = self._metric_card(grid, 1, 0, "0", "Amenazas en cuarentena")
        self.engine_value = self._metric_card(grid, 1, 1, "--", "Motor de deteccion")
        self.pack_start(grid, False, False, 0)

    def _metric_card(self, grid, row, col, value, label):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("metric-card")
        card.set_margin_top(4)
        card.set_margin_bottom(4)
        card.set_size_request(-1, 86)

        value_label = Gtk.Label(label=value)
        value_label.get_style_context().add_class("metric-value")
        value_label.set_halign(Gtk.Align.START)
        value_label.set_margin_start(16)
        value_label.set_margin_top(14)
        card.pack_start(value_label, False, False, 0)

        info_label = Gtk.Label(label=label)
        info_label.get_style_context().add_class("metric-label")
        info_label.set_halign(Gtk.Align.START)
        info_label.set_margin_start(16)
        info_label.set_margin_top(2)
        info_label.set_margin_bottom(10)
        card.pack_start(info_label, False, False, 0)

        grid.attach(card, col, row, 1, 1)
        return value_label

    def _build_actions(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_top(10)

        quick = Gtk.Button(label="Analisis rapido de la carpeta personal")
        quick.set_halign(Gtk.Align.START)
        quick.get_style_context().add_class("suggested-action")
        quick.connect("clicked", self._on_quick_scan)
        box.pack_start(quick, False, False, 0)

        scan_all = Gtk.Button(label="Analizar disco completo")
        scan_all.set_halign(Gtk.Align.START)
        scan_all.connect("clicked", self._on_full_scan)
        box.pack_start(scan_all, False, False, 0)
        self.pack_start(box, False, False, 0)

    def _build_banner(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(14)

        title = Gtk.Label(label="Ultimo analisis")
        title.get_style_context().add_class("category-title")
        title.set_halign(Gtk.Align.START)
        title.set_margin_start(14)
        title.set_margin_top(12)
        card.pack_start(title, False, False, 0)

        self.last_scan_label = Gtk.Label(label="No se ha realizado ningun analisis todavia.")
        self.last_scan_label.get_style_context().add_class("metric-label")
        self.last_scan_label.set_halign(Gtk.Align.START)
        self.last_scan_label.set_margin_start(14)
        self.last_scan_label.set_margin_bottom(12)
        self.last_scan_label.set_line_wrap(True)
        card.pack_start(self.last_scan_label, False, False, 0)
        self.pack_start(card, False, False, 0)

    def _pill_state(self, state):
        self.status_pill.get_style_context().remove_class("green")
        self.status_pill.get_style_context().remove_class("red")
        self.status_pill.get_style_context().remove_class("orange")
        self.status_pill.get_style_context().add_class(state)

    def _on_quick_scan(self, button):
        self._begin_scan(os.path.expanduser("~"))

    def _on_full_scan(self, button):
        self._begin_scan("/")

    def _begin_scan(self, target):
        status = check_database_status()
        if not status["files"]:
            self._pill_state("orange")
            self.status_pill.set_text("SIN DEFINICIONES")
            self.status_title.set_text("No se puede analizar")
            self.status_detail.set_text(
                "Faltan las definiciones de virus de ClamAV. Actualiza la base "
                "de datos desde la pestana de actualizaciones antes de analizar."
            )
            return
        self._pill_state("orange")
        self.status_pill.set_text("EN CURSO")
        self.status_title.set_text("Analizando...")
        self.status_detail.set_text("Objetivo: {0}".format(target))
        self._scanning = Scanner()
        found = []

        def on_event(event, data):
            if event == EVENT_FOUND:
                found.append(data.get("file", ""))
            elif event == EVENT_ERROR:
                Gdk.threads_add_idle(
                    GLib.PRIORITY_DEFAULT,
                    lambda: self.status_detail.set_text(
                        str(data.get("message", ""))
                    ),
                )
            elif event == EVENT_DONE:
                result = data.get("result")
                self._finish_scan(result, found)

        thread = threading.Thread(
            target=lambda: self._scanning.scan(target, on_event), daemon=True
        )
        thread.start()

    def _finish_scan(self, result, found):
        scanned = getattr(result, "scanned", 0) or 0
        dirs = getattr(result, "scanned_dirs", 0) or 0
        message = getattr(result, "error", None)

        def update_ui():
            self.infected_value.set_text(str(len(self._quarantine_count())))
            if result.infected:
                self._pill_state("red")
                self.status_pill.set_text("{0} AMENAZAS".format(result.infected))
                self.status_title.set_text("Amenazas detectadas")
                self.status_detail.set_text(
                    "Se detectaron {0} archivos infectados de {1} analizados. "
                    "Revisa la pestana Cuarentena para gestionarlos.".format(
                        result.infected, scanned
                    )
                )
            elif not scanned:
                self._pill_state("orange")
                self.status_pill.set_text("ATENCION")
                self.status_title.set_text("Verificacion incompleta")
                if message:
                    self.status_detail.set_text(message)
                else:
                    self.status_detail.set_text(
                        "El analisis no examino ningun archivo. Comprueba que "
                        "ClamAV y sus definiciones esten instalados y vuelve a "
                        "intentarlo."
                    )
            else:
                self._pill_state("green")
                self.status_pill.set_text("PROTEGIDO")
                self.status_title.set_text("Sistema limpio")
                self.status_detail.set_text(
                    "Se analizaron {0} archivos y {1} carpetas sin encontrar "
                    "amenazas.".format(scanned, dirs)
                )
            self.last_scan_label.set_text(
                "Objetivo: {0} | Archivos: {1} | Amenazas: {2} | Duracion: {3:.1f}s".format(
                    getattr(result, "target", ""), scanned, result.infected, result.duration
                )
            )

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, update_ui)

    def _quarantine_count(self):
        manager = QuarantineManager(self._config["quarantine_dir"])
        return manager.list()

    def refresh(self, status=None, clamav=None):
        status = status or check_database_status()
        clamav = is_clamav_installed() if clamav is None else clamav

        engine_ready = clamav and bool(status["files"])
        if engine_ready:
            self._pill_state("green")
            self.status_pill.set_text("PROTEGIDO")
            self.status_title.set_text("Proteccion activa")
            self.status_detail.set_text(
                "Motor ClamAV operativo con {0} firmas de virus.".format(status["signatures"])
            )
        else:
            self._pill_state("orange")
            self.status_pill.set_text("ATENCION")
            self.status_title.set_text("Instalacion incompleta")
            if not clamav:
                self.status_detail.set_text(
                    "ClamAV no esta instalado. Instala los paquetes clamav y "
                    "clamav-daemon, o usa el instalador de Antivinux."
                )
            else:
                self.status_detail.set_text(
                    "ClamAV esta instalado pero no se encontraron definiciones de virus "
                    "en {0}.".format(status["db_dir"])
                )

        self.signatures_value.set_text("{0:,}".format(status["signatures"]))

        daily = [f for f in status["files"] if f.lower().startswith("daily")]
        stamp = None
        if daily:
            header = parse_cvd_header(os.path.join(status["db_dir"], daily[0]))
            stamp = header["date"] if header else None
        self.last_update_value.set_text(stamp or "Sin base de datos")

        ant = system_info().get("Antivirus", "ClamAV")
        self.engine_value.set_text(ant if "Clam" in ant else "ClamAV {}".format(ant))
        self.infected_value.set_text(str(len(self._quarantine_count())))

    def on_show_page(self):
        self.refresh()