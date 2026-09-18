# -*- coding: utf-8 -*-
"""Pagina acerca de Antivinux."""

import shutil
import subprocess

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ... import (  # noqa: E402
    __version__,
    __author__,
    __address__,
    __city__,
    __copyright__,
    __homepage__,
    __license__,
)


class AboutPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._build_body()

    def _build_body(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("metric-card")
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(4)

        icon = Gtk.Image.new_from_icon_name(
            "security-high-symbolic", Gtk.IconSize.DIALOG
        )
        icon.set_margin_top(22)
        card.pack_start(icon, False, False, 0)

        name = Gtk.Label(label="Antivinux")
        name.get_style_context().add_class("category-title")
        name.set_margin_top(8)
        card.pack_start(name, False, False, 0)

        desc = Gtk.Label(
            label="Antivirus grafico para Zorin OS y sistemas basados en Debian.\n"
            "Motor de deteccion: ClamAV"
        )
        desc.get_style_context().add_class("metric-label")
        desc.set_margin_top(2)
        card.pack_start(desc, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_margin_top(14)

        def add_row(grid, row, key, value):
            key_label = Gtk.Label(label=key)
            key_label.get_style_context().add_class("metric-label")
            key_label.set_halign(Gtk.Align.END)
            val_label = Gtk.Label(label=value)
            val_label.set_halign(Gtk.Align.START)
            grid.attach(key_label, 0, row, 1, 1)
            grid.attach(val_label, 1, row, 1, 1)

        add_row(grid, 0, "Version", __version__)
        add_row(grid, 1, "Autor", __author__)
        add_row(grid, 2, "Direccion", __address__)
        add_row(grid, 3, "Poblacion", __city__)
        add_row(grid, 4, "Licencia", __license__)
        add_row(grid, 5, "Copyright", __copyright__)
        add_row(grid, 6, "Base de datos", "main.cvd, daily.cvd, bytecode.cvd")
        add_row(grid, 7, "Actualizaciones", "freshclam")
        card.pack_start(grid, False, False, 0)

        href_label = Gtk.Label(label=__homepage__)
        href_label.set_halign(Gtk.Align.CENTER)
        href_label.set_margin_top(12)
        href_label.set_margin_bottom(8)
        card.pack_start(href_label, False, False, 0)

        open_home = Gtk.Button(label="Abrir repositorio en GitHub")
        open_home.set_halign(Gtk.Align.CENTER)
        open_home.connect("clicked", self._on_open_homepage)
        card.pack_start(open_home, False, False, 0)

        license_text = Gtk.Label(
            label="{0}\n"
            "Antivinux es software libre distribuido bajo los terminos de la "
            "Licencia Publica General de GNU, version 3 (GPL-3.0).\n"
            "ClamAV y freshclam son proyectos independientes mantenidos por la "
            "comunidad ClamAV.".format(__copyright__)
        )
        license_text.get_style_context().add_class("metric-label")
        license_text.set_margin_top(14)
        license_text.set_margin_bottom(16)
        license_text.set_margin_start(16)
        license_text.set_margin_end(16)
        license_text.set_justify(Gtk.Justification.CENTER)
        license_text.set_line_wrap(True)
        license_text.set_max_width_chars(70)
        card.pack_start(license_text, False, False, 0)

        self.pack_start(card, True, True, 0)

    def _on_open_homepage(self, button):
        xdg_open = shutil.which("xdg-open")
        if xdg_open:
            subprocess.Popen([xdg_open, __homepage__])

    def on_show_page(self):
        pass