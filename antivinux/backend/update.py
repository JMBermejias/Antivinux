# -*- coding: utf-8 -*-
"""Gestion de actualizaciones de definiciones de virus mediante freshclam."""

import os
import subprocess
import threading
import time

from . import which, find_database_dir, check_database_status, parse_cvd_header


POLL_INTERVAL = 0.2
UPDATE_EVENT_STATUS = "status"
UPDATE_EVENT_LINE = "line"
UPDATE_EVENT_DONE = "done"
UPDATE_EVENT_ERROR = "error"


class Updater:
    def __init__(self, callback=None):
        self.callback = callback
        self._process = None
        self._cancelled = False

    def _emit(self, event, **data):
        if self.callback:
            self.callback(event, data)

    def cancel(self):
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def database_status(self):
        return check_database_status()

    def update(self, callback=None, use_pkexec=True, custom_args=None):
        """Ejecuta freshclam y emite eventos de progreso."""
        if callback is not None:
            self.callback = callback
        self._cancelled = False

        freshclam = which("freshclam")
        if not freshclam:
            self._emit(UPDATE_EVENT_ERROR, message="freshclam no esta instalado.")
            self._emit(UPDATE_EVENT_DONE, status="error")
            return False

        if os.geteuid() == 0:
            use_pkexec = False

        base_cmd = [
            freshclam,
            "--no-warnings",
            "--verbose",
        ]
        if custom_args:
            base_cmd.extend(custom_args)

        exec_cmd = base_cmd
        if use_pkexec:
            pkexec = which("pkexec")
            if not pkexec:
                self._emit(
                    UPDATE_EVENT_ERROR,
                    message="No se permite ejecutar freshclam como usuario normal. "
                    "Instala pkexec o ejecuta la aplicacion con elevacion de privilegios.",
                )
                self._emit(UPDATE_EVENT_DONE, status="error")
                return False
            exec_cmd = [pkexec] + base_cmd

        self._emit(UPDATE_EVENT_STATUS, text="Iniciando actualizacion de definiciones...")

        try:
            self._process = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self._emit(UPDATE_EVENT_ERROR, message=str(exc))
            self._emit(UPDATE_EVENT_DONE, status="error")
            return False

        recent_lines = []

        def drain():
            for line in iter(self._process.stdout.readline, ""):
                recent_lines.append(line)

        thread = threading.Thread(target=drain)
        thread.daemon = True
        thread.start()

        while self._process.poll() is None:
            if self._cancelled:
                try:
                    self._process.terminate()
                except Exception:
                    pass
                self._emit(UPDATE_EVENT_STATUS, text="Actualizacion cancelada.")
                break
            if recent_lines:
                self._emit(UPDATE_EVENT_LINE, lines=list(recent_lines))
                recent_lines.clear()
            time.sleep(POLL_INTERVAL)

        if recent_lines:
            self._emit(UPDATE_EVENT_LINE, lines=list(recent_lines))

        try:
            self._process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self._process.kill()

        code = self._process.returncode
        ok = code in (0,) if not self._cancelled else False
        if self._cancelled:
            self._emit(UPDATE_EVENT_DONE, status="cancelled")
            return False
        if code == 1:
            self._emit(
                UPDATE_EVENT_STATUS,
                text="Definiciones ya actualizadas o comprobadas conforme a los "
                "parametros de freshclam.conf.",
            )
            self._emit(UPDATE_EVENT_DONE, status="uptodate")
        elif code == 0:
            self._emit(
                UPDATE_EVENT_STATUS, text="Base de datos de virus actualizada correctamente."
            )
            self._emit(UPDATE_EVENT_DONE, status="ok")
        else:
            self._emit(
                UPDATE_EVENT_ERROR,
                message="freshclam finalizo con codigo de error {}.".format(code),
            )
            self._emit(UPDATE_EVENT_DONE, status="error")
        return ok or code == 1


def check_database_age():
    """Devuelve antiguedad en horas de la base de datos diaria."""
    db_dir = find_database_dir()
    for name in ("daily.cvd", "daily.cld"):
        path = os.path.join(db_dir, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        age_hours = (time.time() - st.st_mtime) / 3600.0
        return age_hours
    return None


__all__ = [
    "Updater",
    "check_database_age",
    "UPDATE_EVENT_STATUS",
    "UPDATE_EVENT_LINE",
    "UPDATE_EVENT_DONE",
    "UPDATE_EVENT_ERROR",
]