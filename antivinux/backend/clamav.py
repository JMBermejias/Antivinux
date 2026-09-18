# -*- coding: utf-8 -*-
"""Motor de escaneo basado en clamscan."""

import os
import re
import shutil
import subprocess
import threading
import time

from . import which, is_clamav_installed


EVENT_START = "start"
EVENT_PROGRESS = "progress"
EVENT_FOUND = "found"
EVENT_CLEAN = "clean"
EVENT_ERROR = "error"
EVENT_DONE = "done"
EVENT_CANCELLED = "cancelled"


FOUND_RE = re.compile(r"^(.*?):\s+(\S+\s+)?FOUND\s*$", re.IGNORECASE)

SUMMARY_RE = re.compile(r"Infected files:\s*(\d+)", re.IGNORECASE)
SCANNED_FILES_RE = re.compile(r"Scanned files:\s*(\d+)", re.IGNORECASE)
SCANNED_DIRS_RE = re.compile(r"Scanned directories:\s*(\d+)", re.IGNORECASE)
KNOWN_VIRUSES_RE = re.compile(r"Known viruses:\s*(\S+)", re.IGNORECASE)
ENGINE_RE = re.compile(r"Engine version:\s*(\S+)", re.IGNORECASE)


class ScanResult:
    def __init__(self):
        self.infected = 0
        self.scanned = 0
        self.scanned_dirs = 0
        self.known_viruses = None
        self.engine = None
        self.clean = True
        self.found = []
        self.error = None
        self.duration = 0.0
        self.cancelled = False
        self.target = ""


class Scanner:
    def __init__(self, callback=None):
        self.callback = callback
        self._process = None
        self._cancelled = False
        self.recursive = True
        self.follow_links = False
        self._configure_defaults()

    def _configure_defaults(self):
        self.default_args = [
            "--no-banner",
            "--infected",
            "--stdout",
            "--bell",
        ]

    def build_args(self):
        args = list(self.default_args)
        if self.recursive:
            args.append("--recursive")
        if self.follow_links:
            args.append("--follow-links")
        return args


    def emit(self, event, **data):
        if self.callback:
            self.callback(event, data)

    def cancel(self):
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def scan(self, target, callback=None):
        if callback is not None:
            self.callback = callback
        if not is_clamav_installed():
            result = ScanResult()
            result.error = "ClamAV no esta instalado. Ejecuta: sudo apt install clamav clamav-daemon"
            self.emit(EVENT_ERROR, message=result.error)
            self.emit(EVENT_DONE, result=result)
            return result

        result = ScanResult()
        result.target = target
        start = time.time()
        self._cancelled = False
        self.emit(EVENT_START, target=target)

        clamscan = which("clamscan")
        if not clamscan:
            result.error = (
                "clamscan no esta instalado. Instala el paquete clamav."
            )
            self.emit(EVENT_ERROR, message=result.error)
            self.emit(EVENT_DONE, result=result)
            return result

        cmd = [clamscan] + self.build_args() + [target]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except (OSError, subprocess.SubprocessError, TypeError) as exc:
            result.error = str(exc)
            self.emit(EVENT_ERROR, message=result.error)
            self.emit(EVENT_DONE, result=result)
            return result

        stdout_lines = []
        stderr_lines = []
        threads = []

        def read_stream(stream, sink):
            for line in iter(stream.readline, ""):
                sink.append(line)

        for stream, sink in (
            (self._process.stdout, stdout_lines),
            (self._process.stderr, stderr_lines),
        ):
            thread = threading.Thread(target=read_stream, args=(stream, sink))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # Seguimiento de la salida mientras el proceso corre.
        last_found_index = 0
        while True:
            if self._cancelled:
                try:
                    self._process.terminate()
                except Exception:
                    pass
                result.cancelled = True
                break
            if self._process.poll() is not None:
                break
            new_found = self._extract_findings(stdout_lines[last_found_index:])
            for finding in new_found:
                result.found.append(finding)
                result.infected += 1
                self.emit(EVENT_FOUND, file=finding["file"], signature=finding["signature"])
            last_found_index = len(stdout_lines)
            time.sleep(0.15)

        try:
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self._process.kill()

        # Esperar a que los hilos terminen de drenar la salida del proceso.
        for thread in threads:
            thread.join(timeout=5)

        new_found = self._extract_findings(stdout_lines[last_found_index:])
        for finding in new_found:
            result.found.append(finding)
            result.infected += 1
            self.emit(EVENT_FOUND, file=finding["file"], signature=finding["signature"])

        summary_blob = "\n".join(stdout_lines + stderr_lines)
        stats = self._summary_stats(summary_blob)
        if not result.infected and stats["infected"]:
            result.infected = stats["infected"]
        if stats["scanned"] is not None:
            result.scanned = stats["scanned"]
        else:
            result.scanned = self._count_scanned(stdout_lines)
        result.scanned_dirs = stats["scanned_dirs"]
        result.known_viruses = stats["known_viruses"]
        result.engine = stats["engine"]

        result.clean = result.infected == 0
        for line in stderr_lines:
            if "ERROR" in line or "error" in line:
                result.error = line.strip()
                self.emit(EVENT_ERROR, message=line.strip())
                break

        result.duration = time.time() - start
        self.emit(EVENT_DONE, result=result)
        return result

    @staticmethod
    def _summary_stats(blob):
        stats = {
            "infected": 0,
            "scanned": None,
            "scanned_dirs": 0,
            "known_viruses": None,
            "engine": None,
        }
        for key, regex in (
            ("infected", SUMMARY_RE),
            ("scanned", SCANNED_FILES_RE),
            ("scanned_dirs", SCANNED_DIRS_RE),
            ("known_viruses", KNOWN_VIRUSES_RE),
            ("engine", ENGINE_RE),
        ):
            match = regex.search(blob)
            if match:
                value = match.group(1).strip()
                if key in ("infected", "scanned", "scanned_dirs"):
                    stats[key] = int(value)
                else:
                    stats[key] = value
        return stats

    def _count_scanned(self, lines):
        count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if " FOUND" in line or " OK" in line or line.endswith(":"):
                count += 1
        return count

    @staticmethod
    def _extract_findings(lines):
        findings = []
        for line in lines:
            stripped = line.strip()
            match = FOUND_RE.match(stripped)
            if not match:
                continue
            file_path = match.group(1).strip()
            signature = (match.group(2) or "FOUND").strip()
            findings.append({"file": file_path, "signature": signature})
        return findings


def scan_path(path, callback=None):
    scanner = Scanner(callback)
    scanner.scan(path, callback=callback)
    return scanner


__all__ = [
    "Scanner",
    "ScanResult",
    "scan_path",
    "EVENT_START",
    "EVENT_PROGRESS",
    "EVENT_FOUND",
    "EVENT_CLEAN",
    "EVENT_ERROR",
    "EVENT_DONE",
    "EVENT_CANCELLED",
]