# -*- coding: utf-8 -*-
"""Comprobacion y aplicacion de actualizaciones de la propia aplicacion.

Las versiones se publican como releases en GitHub; cada release adjunta el
paquete ``antivinux_<version>_all.deb``. Este modulo consulta la ultima
release, compara versiones, descarga el paquete y lo instala con privilegios
a traves de ``pkexec``.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from . import which

try:
    from .. import __version__
except ImportError:  # pragma: no cover - ejecucion directa
    __version__ = "0.0.0"


REPO = "JMBermejias/Antivinux"
RELEASES_LATEST_API = "https://api.github.com/repos/{0}/releases/latest".format(REPO)
USER_AGENT = "Antivinux/{0}".format(__version__)
DOWNLOAD_CHUNK = 65536
INSTALL_TIMEOUT = 600


def parse_version(text):
    """Convierte 'v1.0.10' o '1.0.10' en una tupla comparable (1, 0, 10)."""
    parts = []
    for piece in str(text).strip().lstrip("vV").split("."):
        match = re.match(r"\d+", piece.strip())
        parts.append(int(match.group()) if match else 0)
    return tuple(parts)


def is_newer(candidate, current):
    """Indica si ``candidate`` es una version posterior a ``current``."""
    return parse_version(candidate) > parse_version(current)


def _request(url, timeout):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    return urllib.request.urlopen(request, timeout=timeout)


def check_for_update(current_version=None, timeout=10):
    """Consulta la ultima release y devuelve un dict con el resultado.

    Nunca lanza excepciones: ante cualquier fallo devuelve ``error`` con el
    motivo. Las claves son:
        available, current, latest, download_url, asset_name, html_url,
        notes, error
    """
    current = current_version or __version__
    result = {
        "available": False,
        "current": current,
        "latest": None,
        "download_url": None,
        "asset_name": None,
        "html_url": None,
        "notes": "",
        "error": None,
    }
    try:
        with _request(RELEASES_LATEST_API, timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        result["error"] = "GitHub respondio con el codigo {0}.".format(exc.code)
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result

    tag = (data.get("tag_name") or "").strip()
    latest = tag.lstrip("vV")
    result["latest"] = latest
    result["html_url"] = data.get("html_url")
    result["notes"] = data.get("body") or ""
    for asset in data.get("assets") or []:
        name = asset.get("name") or ""
        if name.endswith(".deb"):
            result["download_url"] = asset.get("browser_download_url")
            result["asset_name"] = name
            break

    result["available"] = bool(
        latest and result["download_url"] and is_newer(latest, current)
    )
    return result


def download_update(info, dest_dir=None, progress_cb=None, timeout=30):
    """Descarga el paquete .deb de la release indicada y devuelve su ruta."""
    url = (info or {}).get("download_url")
    if not url:
        raise RuntimeError("La release no incluye un paquete .deb.")

    dest_dir = dest_dir or tempfile.mkdtemp(prefix="antivinux-update-")
    filename = (info.get("asset_name")
                or os.path.basename(urllib.parse.urlparse(url).path)
                or "antivinux.deb")
    path = os.path.join(dest_dir, filename)

    with _request(url, timeout) as response, open(path, "wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(DOWNLOAD_CHUNK)
            if not chunk:
                break
            handle.write(chunk)
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
    return path


def install_package(deb_path):
    """Instala el paquete .deb con privilegios. Devuelve (ok, mensaje)."""
    if not deb_path or not os.path.isfile(deb_path):
        return False, "No se encontro el paquete descargado."

    pkexec = which("pkexec")
    if not pkexec:
        return False, "No se encontro pkexec para elevar privilegios."

    helper = which("antivinux-self-update")
    if helper:
        command = [pkexec, helper, deb_path]
    else:
        apt = which("apt-get") or which("apt")
        if not apt:
            return False, "No se encontro apt-get ni el asistente de actualizacion."
        command = [pkexec, apt, "install", "-y", deb_path]

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=INSTALL_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, "La instalacion tardo demasiado y se cancelo."
    except Exception as exc:
        return False, str(exc)

    output = (completed.stdout or "").strip()
    if completed.returncode == 0:
        return True, output
    return False, output or "La instalacion finalizo con errores."


def default_download_dir():
    """Directorio temporal reutilizable para las descargas."""
    return os.path.join(tempfile.gettempdir(), "antivinux-update")


def cleanup(path):
    """Elimina el directorio de descarga si es temporal."""
    directory = path if os.path.isdir(path) else os.path.dirname(path or "")
    if directory and directory.startswith(tempfile.gettempdir()):
        shutil.rmtree(directory, ignore_errors=True)


__all__ = [
    "REPO",
    "parse_version",
    "is_newer",
    "check_for_update",
    "download_update",
    "install_package",
    "default_download_dir",
    "cleanup",
]
