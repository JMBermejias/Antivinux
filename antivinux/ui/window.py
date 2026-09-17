# -*- coding: utf-8 -*-
"""Ventana principal con barra de navegacion lateral."""

import sys

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from ..config import Config  # noqa: E402
from ..backend import check_database_status, is_clamav_installed  # noqa: E402
from ..backend.quarantine import QuarantineManager  # noqa: E402
from .pages.home import HomePage  # noqa: E402
from .pages.scan import ScanPage  # noqa: E402
from .pages.update import UpdatePage  # noqa: E402
from .pages.quarantine import QuarantinePage  # noqa: E402
from .pages.settings import SettingsPage  # noqa: E402
from .pages.about import AboutPage  # noqa: E402


CSS = """
window {
    background-color: #f5f6f7;
}

.nav-sidebar {
    background-color: #1c2233;
    border-right: 1px solid #0f1320;
}

.nav-sidebar button.ant-navigation {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #c7cbd6;
    font-weight: 600;
    padding: 12px 16px;
    margin: 2px 8px;
    box-shadow: none;
}

.nav-sidebar button.ant-navigation:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
}

.nav-sidebar button.ant-navigation:active,
.nav-sidebar button.ant-navigation:checked {
    background-color: #2f6fed;
    color: #ffffff;
}

.ant-brand {
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
}

.category-title {
    font-size: 18px;
    font-weight: 700;
    color: #1c2233;
}

.metric-card {
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: none;
    border: 1px solid #e1e6ee;
}

.metric-value {
    font-size: 26px;
    font-weight: 800;
    color: #1c2233;
}

.metric-label {
    font-size: 12px;
    color: #6b7280;
}

.statuspill {
    border-radius: 999px;
    padding: 4px 12px;
    font-weight: 700;
}

.statuspill.green {
    background-color: #e6f6ec;
    color: #1f7a3d;
}

.statuspill.red {
    background-color: #fde8e8;
    color: #b91c1c;
}

.statuspill.orange {
    background-color: #fff4e5;
    color: #b45309;
}

.log-textview {
    font-family: monospace;
    font-size: 12px;
}
"""


class AntivinuxWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Antivinux")
        self.set_default_size(1100, 700)
        self.config = Config()
        self.quarantine = QuarantineManager(self.config["quarantine_dir"])

        self._install_css()
        self._build_header()
        self._build_body()
        self._build_sidebar()

        status = check_database_status()
        self.pages["home"].refresh(status=status, clamav=is_clamav_installed())
        self.pages["update"].set_db_status(status)

    def _install_css(self):
        provider = Gtk.CssProvider()
        try:
            try:
                provider.load_from_data(CSS.encode("utf-8"))
            except TypeError:
                # PyGObject antiguo espera texto en lugar de bytes.
                provider.load_from_data(CSS)
        except Exception as exc:
            # Un error de estilos no debe impedir abrir la aplicacion.
            sys.stderr.write("Antivinux: aviso de estilos: {0}\n".format(exc))
            return
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_header(self):
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Antivinux")
        header.set_subtitle("Proteccion para Zorin / Debian")
        self.set_titlebar(header)

    def _build_body(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(main_box)

        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_box.set_size_request(210, -1)
        self.sidebar_box.get_style_context().add_class("nav-sidebar")
        main_box.pack_start(self.sidebar_box, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_margin_top(14)
        self.stack.set_margin_bottom(14)
        self.stack.set_margin_start(14)
        self.stack.set_margin_end(14)
        main_box.pack_start(self.stack, True, True, 0)

        self.pages = {}
        self.pages["home"] = HomePage()
        self.pages["scan"] = ScanPage()
        self.pages["update"] = UpdatePage()
        self.pages["quarantine"] = QuarantinePage()
        self.pages["settings"] = SettingsPage()
        self.pages["about"] = AboutPage()
        for name, page in self.pages.items():
            self.stack.add_named(page, name)

    def _build_sidebar(self):
        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        brand.set_margin_top(18)
        brand.set_margin_bottom(14)
        brand.set_margin_left(14)
        brand.set_margin_right(14)
        brand.set_spacing(2)

        icon = self._brand_icon()
        brand.pack_start(icon, False, False, 0)

        name = Gtk.Label(label="Antivinux")
        name.get_style_context().add_class("ant-brand")
        name.set_halign(Gtk.Align.START)
        name.set_margin_top(6)
        brand.pack_start(name, False, False, 0)

        subtitle = Gtk.Label(label="version {0}".format(__version__))
        subtitle.set_halign(Gtk.Align.START)
        subtitle.get_style_context().add_class("metric-label")
        brand.pack_start(subtitle, False, False, 0)

        self.sidebar_box.pack_start(brand, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        nav.set_margin_top(8)
        self.sidebar_box.pack_start(nav, False, False, 0)

        items = [
            ("home", "Inicio"),
            ("scan", "Analisis"),
            ("update", "Actualizaciones"),
            ("quarantine", "Cuarentena"),
            ("settings", "Ajustes"),
            ("about", "Acerca de"),
        ]

        self.sidebar_buttons = {}
        group_leader = None
        for stack_name, label in items:
            button = Gtk.RadioButton()
            button.set_label(label)
            # set_mode(False) hace que el RadioButton se dibuje como un
            # boton normal (sin el circulo indicador).
            button.set_mode(False)
            button.get_style_context().add_class("ant-navigation")
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.set_can_focus(False)
            if group_leader is None:
                group_leader = button
            else:
                button.join_group(group_leader)
            button.connect("toggled", self._on_nav_toggled, stack_name)
            nav.pack_start(button, False, False, 0)
            self.sidebar_buttons[stack_name] = button

        footer = Gtk.Label(label="Motor de deteccion: ClamAV")
        footer.set_halign(Gtk.Align.START)
        footer.set_margin_top(18)
        footer.set_margin_left(16)
        footer.get_style_context().add_class("metric-label")
        self.sidebar_box.pack_end(footer, False, False, 0)

        self.sidebar_buttons["home"].set_active(True)

    def _brand_icon(self):
        try:
            icon_theme = Gtk.IconTheme.get_default()
            icon_names = ("org.antivinux", "security-high-symbolic", "system-security-symbolic")
            for name in icon_names:
                if icon_theme.has_icon(name):
                    return Gtk.Image.new_from_icon_name(name, Gtk.IconSize.DIALOG)
            return Gtk.Image.new_from_icon_name("system-security-symbolic", Gtk.IconSize.DIALOG)
        except Exception:
            return Gtk.Image.new_from_icon_name("system-security-symbolic", Gtk.IconSize.DIALOG)

    def _on_nav_toggled(self, button, stack_name):
        if not button.get_active():
            # Al ser RadioButton, el boton anterior se desactiva solo; aqui
            # solo reaccionamos al boton que pasa a activo.
            return
        self.stack.set_visible_child_name(stack_name)
        page = self.stack.get_visible_child()
        if hasattr(page, "on_show_page"):
            page.on_show_page()

    def navigate_to(self, name):
        button = self.sidebar_buttons.get(name)
        if button is None:
            return
        if not button.get_active():
            button.set_active(True)
        else:
            self.stack.set_visible_child_name(name)
            page = self.stack.get_visible_child()
            if hasattr(page, "on_show_page"):
                page.on_show_page()

    def notify(self, title, message):
        from ..notifier import notify

        notify(title, message)