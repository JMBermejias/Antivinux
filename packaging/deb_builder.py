#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constructor ligero de paquetes .deb sin depender de dpkg-deb.

Se usa como alternativa cuando 'dpkg-deb' no esta disponible (por ejemplo,
en entornos de desarrollo que no son Debian). El paquete resultante es un
archivo 'ar' con la estructura estandar de Debian:

    debian-binary
    control.tar.gz
    data.tar.gz

Uso:
    python3 deb_builder.py <directorio_raiz> <salida.deb>

El directorio raiz debe contener una carpeta 'DEBIAN' con 'control' y los
scripts de mantenimiento, y el arbol de ficheros a instalar (usr/, etc.).
"""

import io
import os
import sys
import tarfile
import time


AR_MAGIC = b"!<arch>\n"


def _ar_header(name, size, mode=0o100644):
    header = "{0:<16}{1:<12}{2:<6}{3:<6}{4:<8o}{5:<10}`\n".format(
        name,
        int(time.time()),
        0,
        0,
        mode,
        size,
    )
    return header.encode("ascii")


def _add_ar_member(out, name, data):
    out.write(_ar_header(name, len(data)))
    out.write(data)
    if len(data) % 2:
        out.write(b"\n")


def _add_tree(tar, root, arc_prefix):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel_dir = os.path.relpath(dirpath, root)
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.join(rel_dir, name) if rel_dir != "." else name
            arcname = os.path.join(arc_prefix, rel)
            info = tar.gettarinfo(full, "./" + arcname)
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            with open(full, "rb") as fh:
                tar.addfile(info, fh)
        if rel_dir == ".":
            dir_arc = arc_prefix
        else:
            dir_arc = os.path.join(arc_prefix, rel_dir)
        dir_info = tarfile.TarInfo("./" + dir_arc.rstrip("/") + "/")
        dir_info.type = tarfile.DIRTYPE
        dir_info.mode = 0o755
        dir_info.uid = 0
        dir_info.gid = 0
        dir_info.uname = "root"
        dir_info.gname = "root"
        tar.addfile(dir_info)


def build_deb(root, output):
    debian_dir = os.path.join(root, "DEBIAN")
    if not os.path.isdir(debian_dir):
        raise SystemExit("No existe el directorio DEBIAN en {0}".format(root))

    control_members = sorted(os.listdir(debian_dir))
    # Empaquetar control.tar.gz con rutas ./control, ./postinst, ...
    control_buffer = io.BytesIO()
    with tarfile.open(fileobj=control_buffer, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        for name in control_members:
            full = os.path.join(debian_dir, name)
            if not os.path.isfile(full):
                continue
            info = tar.gettarinfo(full, "./" + name)
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            with open(full, "rb") as fh:
                tar.addfile(info, fh)
    control_tar = control_buffer.getvalue()

    tree = [name for name in sorted(os.listdir(root)) if name != "DEBIAN"]
    data_buffer = io.BytesIO()
    with tarfile.open(fileobj=data_buffer, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        for name in tree:
            full = os.path.join(root, name)
            if os.path.isfile(full):
                info = tar.gettarinfo(full, "./" + name)
                info.uid = info.gid = 0
                info.uname = info.gname = "root"
                with open(full, "rb") as fh:
                    tar.addfile(info, fh)
            else:
                _add_tree(tar, full, name)
    data_tar = data_buffer.getvalue()

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "wb") as out:
        out.write(AR_MAGIC)
        _add_ar_member(out, "debian-binary", b"2.0\n")
        _add_ar_member(out, "control.tar.gz", control_tar)
        _add_ar_member(out, "data.tar.gz", data_tar)
    return output


def main(argv):
    if len(argv) != 3:
        print("Uso: deb_builder.py <directorio_raiz> <salida.deb>", file=sys.stderr)
        return 2
    build_deb(argv[1], argv[2])
    print("Paquete generado: {0}".format(argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
