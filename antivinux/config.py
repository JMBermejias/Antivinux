# -*- coding: utf-8 -*-
"""Gestion de la configuracion persistente de Antivinux."""

import configparser
import os

from . import __version__


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "antivinux")
CONFIG_FILE = os.path.join(CONFIG_DIR, "antivinux.conf")
LOG_FILE = os.path.join(CONFIG_DIR, "antivinux.log")


DEFAULTS = {
    "log_enabled": "true",
    "quarantine_dir": os.path.join(
        os.path.expanduser("~"), ".local", "share", "antivinux", "quarantine"
    ),
    "last_scan_path": os.path.expanduser("~"),
    "scan_archive": "true",
    "update_on_start": "false",
    "show_notifications": "true",
}


class Config:
    def __init__(self, path=CONFIG_FILE):
        self.path = path
        self.parser = configparser.ConfigParser()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.parser["antivinux"] = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            if os.path.isfile(self.path):
                self.parser.read(self.path)
        except (OSError, configparser.Error):
            pass
        if not self.parser.has_section("antivinux"):
            self.parser["antivinux"] = dict(DEFAULTS)

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                self.parser.write(fh)
        except OSError:
            pass

    def __getitem__(self, key):
        section = self.parser["antivinux"]
        return section.get(key, DEFAULTS.get(key, ""))

    def __setitem__(self, key, value):
        self.parser["antivinux"][key] = str(value)
        self.save()

    def get_bool(self, key):
        return self[key].strip().lower() in ("1", "true", "yes", "on")

    def get_float(self, key, default=0.0):
        try:
            return float(self[key])
        except (TypeError, ValueError):
            return default

    def get_version(self):
        return __version__


__all__ = ["Config", "CONFIG_DIR", "CONFIG_FILE", "LOG_FILE", "DEFAULTS"]