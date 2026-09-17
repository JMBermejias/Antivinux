# -*- coding: utf-8 -*-
"""Utilidades para gestionar definiciones de virus y contexto del sistema."""

import os
import subprocess
import tempfile
import shutil


CLAMAV_DB_CANDIDATES = (
    "/var/lib/clamav",
    "/var/opt/clamav",
    "/usr/local/share/clamav",
    "/var/lib/clamav/clamonacc",
)


def find_database_dir():
    """Devuelve el directorio donde residen las bases de datos de ClamAV."""
    for candidate in CLAMAV_DB_CANDIDATES:
        try:
            if os.path.isdir(candidate) and os.access(candidate, os.R_OK):
                return candidate
        except OSError:
            continue
    try:
        result = subprocess.run(
            ["clamd", "--config-dir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "/var/lib/clamav"


def database_files(db_dir=None):
    """Devuelve la lista de archivos de base de datos (cvd/cld) presentes."""
    db_dir = db_dir or find_database_dir()
    if not os.path.isdir(db_dir):
        return []
    try:
        entries = sorted(os.listdir(db_dir))
    except OSError:
        return []
    return [f for f in entries if f.lower().endswith((".cvd", ".cld"))]


def parse_cvd_header(path):
    """Analiza la cabecera textual de un archivo .cvd/.cld.

    La primera linea sigue el formato:
        ClamAV-VDB:<fecha>:<version>:<firmas>:<nivel funcional>:<md5>:...
    Por ejemplo:
        ClamAV-VDB:17 Sep 2026 06-24 +0000:28126:355666:90:d11370...
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            header = fh.readline(512)
    except OSError:
        return None
    if not header.startswith(b"ClamAV-VDB:"):
        return None

    try:
        line = header.decode("latin-1").strip()
    except (UnicodeDecodeError, AttributeError):
        return None
    # La fecha usa guiones en lugar de dos puntos para no colisionar con el
    # separador de campos, de modo que dividir por ':' es seguro.
    parts = line.split(":")
    if len(parts) < 5:
        return None

    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "date": parts[1].strip(),
        "version": parts[2].strip(),
        "signatures": _to_int(parts[3]),
        "functional_level": _to_int(parts[4]),
    }


def check_database_status():
    """Devuelve un dict con el estado de la base de datos de ClamAV."""
    db_dir = find_database_dir()
    files = database_files(db_dir)
    entries = {}
    for name in files:
        full = os.path.join(db_dir, name)
        try:
            st = os.stat(full)
        except OSError:
            continue
        header = parse_cvd_header(full)
        entries[name] = {
            "size": st.st_size,
            "mtime": st.st_mtime,
            "version": header["version"] if header else None,
            "build_date": header["date"] if header else None,
            "signatures": header["signatures"] if header else None,
        }
    return {
        "db_dir": db_dir,
        "files": entries,
        "signatures": count_signatures(entries),
    }


def count_signatures(entries):
    """Cuenta las firmas a partir de las cabeceras, con respaldo por tamano."""
    total = 0
    estimated = 0.0
    found_header = False
    for name, info in entries.items():
        sigs = info.get("signatures")
        if sigs:
            total += sigs
            found_header = True
        else:
            estimated += info["size"] / 1024.0 / 8.0 * 5.0
    if found_header:
        # Las cabeceras ya incluyen el total real de firmas; el respaldo por
        # tamano solo se usa para los archivos sin cabecera reconocible.
        total += int(estimated)
        return total
    return int(estimated)


def detect_count_total(entries):
    """Compatibilidad: estimacion del numero de firmas de la base de datos."""
    return count_signatures(entries)


def which(binary):
    return shutil.which(binary)


def is_clamav_installed():
    return which("clamscan") is not None and which("freshclam") is not None


def system_info():
    fields = {}
    for key, path in (
        ("OS", "/etc/os-release"),
        ("Hostname", "/proc/sys/kernel/hostname"),
    ):
        try:
            with open(path, "r") as fh:
                content = fh.read()
        except OSError:
            continue
        if key == "OS":
            for line in content.splitlines():
                if line.startswith("PRETTY_NAME="):
                    fields[key] = line.split("=", 1)[1].strip().strip('"')
                    break
        else:
            fields[key] = content.strip()
    try:
        kernel_src = open("/proc/version", "r")
        fields["Kernel"] = kernel_src.read().split(" (", 1)[0]
        kernel_src.close()
    except OSError:
        pass
    try:
        fields["Antivirus"] = "ClamAV " + subprocess.run(
            ["clamscan", "--version"],
            stdout=subprocess.PIPE,
            text=True,
            timeout=5,
        ).stdout.splitlines()[0].split("ClamAV ")[1].split("/")[0]
    except Exception:
        fields["Antivirus"] = "ClamAV (desconocido)"
    return fields


def temp_scan_dir():
    """Crea un directorio temporal para un escaneo."""
    return tempfile.mkdtemp(prefix="antivinux-scan-")


def remove_tree(path, ignore_errors=True):
    shutil.rmtree(path, ignore_errors=ignore_errors)


__all__ = [
    "find_database_dir",
    "database_files",
    "parse_cvd_header",
    "check_database_status",
    "count_signatures",
    "detect_count_total",
    "which",
    "is_clamav_installed",
    "system_info",
    "temp_scan_dir",
    "remove_tree",
]