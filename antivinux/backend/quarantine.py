# -*- coding: utf-8 -*-
"""Gestion de cuarentena para archivos detectados como infectados."""

import json
import os
import shutil
import time

from . import temp_scan_dir


class QuarantineManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "antivinux", "quarantine")
        self.base_dir = base_dir
        self.index_path = os.path.join(base_dir, "index.json")
        os.makedirs(base_dir, exist_ok=True)
        self._entries = self._load_index()

    def _load_index(self):
        if not os.path.isfile(self.index_path):
            return []
        try:
            with open(self.index_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _save_index(self):
        try:
            with open(self.index_path, "w", encoding="utf-8") as fh:
                json.dump(self._entries, fh, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def quarantine(self, file_path, signature, scan_id="", scanned_source=""):
        if not file_path or not os.path.exists(file_path):
            return None
        base = os.path.basename(file_path)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = os.path.join(self.base_dir, "{0}-{1}.quarantine".format(stamp, base))
        try:
            shutil.copy2(file_path, target)
        except (OSError, shutil.Error):
            return None
        entry = {
            "id": stamp,
            "original": os.path.abspath(file_path),
            "quarantined": target,
            "signature": signature,
            "scan_id": scan_id,
            "scanned_source": scanned_source,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": os.path.getsize(target),
        }
        self._entries.append(entry)
        self._save_index()
        return entry

    def list(self):
        return list(self._entries)

    def restore(self, entry_id):
        entry = self.find(entry_id)
        if not entry:
            return False
        src = entry["quarantined"]
        dst = entry["original"]
        if not os.path.isfile(src):
            return False
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
            os.remove(src)
        except (OSError, shutil.Error):
            return False
        self._entries.remove(entry)
        self._save_index()
        return True

    def delete(self, entry_id):
        entry = self.find(entry_id)
        if not entry:
            return False
        try:
            if os.path.isfile(entry["quarantined"]):
                os.remove(entry["quarantined"])
        except OSError:
            pass
        self._entries.remove(entry)
        self._save_index()
        return True

    def delete_all(self):
        self._entries.clear()
        self._save_index()
        tmp = temp_scan_dir()
        shutil.rmtree(tmp, ignore_errors=True)
        return True

    def find(self, entry_id):
        for entry in self._entries:
            if entry["id"] == entry_id:
                return entry
        return None


__all__ = ["QuarantineManager"]