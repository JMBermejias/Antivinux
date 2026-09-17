#!/bin/sh
#
# install_deps.sh - Instala las dependencias del sistema necesarias
# para ejecutar y construir Antivinux en Zorin OS / Debian / Ubuntu.
#
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Este script debe ejecutarse con privilegios de administrador:"
    echo "    sudo $0"
    exit 1
fi

echo "==> Actualizando indices de paquetes..."
apt-get update

echo "==> Instalando dependencias de ejecucion..."
apt-get install -y \
    python3 \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-notify-0.7 \
    gir1.2-gdkpixbuf-2.0 \
    clamav \
    clamav-base \
    clamav-freshclam \
    clamav-daemon \
    policykit-1

echo "==> Instalando herramientas de empaquetado (opcional)..."
apt-get install -y dpkg debhelper dh-python python3-setuptools || true

echo
echo "==> Dependencias instaladas."
echo "    Descarga ahora las definiciones de virus con: sudo freshclam"
echo "    y ejecuta la aplicacion con: python3 antivinux-launcher.py"