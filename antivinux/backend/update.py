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


def freshclam_is_running():
    """Indica si hay otro proceso freshclam (servicio clamav-freshclam)."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "freshclam"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        if result.stdout.strip():
            return True
    except Exception:
        pass
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(os.path.join("/proc", entry, "comm"), "r") as fh:
                    comm = fh.read().strip()
            except (OSError, IOError):
                continue
            if comm == "freshclam":
                return True
    except Exception:
        pass
    return False


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

        if freshclam_is_running():
            age = check_database_age()
            if age is not None and age <= 48:
                text = (
                    "El servicio clamav-freshclam ya mantiene las definiciones "
                    "de virus al dia (ultima actualizacion hace {0:.0f} h). "
                    "No es necesario actualizar manualmente.".format(age)
                )
                self._emit(UPDATE_EVENT_STATUS, text=text)
                self._emit(UPDATE_EVENT_DONE, status="uptodate")
                return True
            self._emit(
                UPDATE_EVENT_ERROR,
                message="Hay otro proceso freshclam en marcha (el servicio "
                "clamav-freshclam) que bloquea el registro de actualizacion "
                "y la base de datos no esta al dia. Revisa "
                "/var/log/clamav/freshclam.log o reinicia el servicio con:\n"
                "sudo systemctl restart clamav-freshclam",
            )
            self._emit(UPDATE_EVENT_DONE, status="error")
            return False

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
        except (OSError, subprocess.SubprocessError, TypeError) as exc:
            self._emit(UPDATE_EVENT_ERROR, message=str(exc))
            self._emit(UPDATE_EVENT_DONE, status="error")
            return False

        recent_lines = []
        self._lines = []

        def drain():
            for line in iter(self._process.stdout.readline, ""):
                recent_lines.append(line)
                self._lines.append(line)

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
            if any("lock the log file" in line for line in self._lines):
                self._emit(
                    UPDATE_EVENT_ERROR,
                    message="El registro de actualizacion esta bloqueado por otro "
                    "proceso freshclam (servicio clamav-freshclam). Espera a que "
                    "termine o revisa /var/log/clamav/freshclam.log.",
                )
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
    "freshclam_is_running",
    "UPDATE_EVENT_STATUS",
    "UPDATE_EVENT_LINE",
    "UPDATE_EVENT_DONE",
    "UPDATE_EVENT_ERROR",
]