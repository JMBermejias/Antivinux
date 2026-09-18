#!/bin/bash
#
# antivinux-self-update.sh - Instala una actualizacion de Antivinux.
#
# Se ejecuta con privilegios a traves de pkexec:
#   pkexec /usr/bin/antivinux-self-update /ruta/antivinux_X.Y.Z_all.deb
#
set -e

PKG_NAME="antivinux"
DEB="${1:-}"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: se requieren privilegios de administrador." >&2
    exit 1
fi

if [ -z "$DEB" ]; then
    echo "ERROR: falta la ruta del paquete .deb." >&2
    exit 1
fi

if [ ! -f "$DEB" ]; then
    echo "ERROR: no existe el archivo $DEB." >&2
    exit 1
fi

# Solo se permite instalar paquetes propios de Antivinux.
case "$(basename "$DEB")" in
    ${PKG_NAME}_*.deb)
        ;;
    *)
        echo "ERROR: el archivo no es un paquete valido de Antivinux." >&2
        exit 1
        ;;
esac

APT="$(command -v apt-get || command -v apt || true)"
if [ -z "$APT" ]; then
    echo "ERROR: no se encontro apt-get." >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> Instalando actualizacion de Antivinux desde $DEB..."
"$APT" install -y "$DEB"
echo "==> Actualizacion instalada correctamente."
exit 0
