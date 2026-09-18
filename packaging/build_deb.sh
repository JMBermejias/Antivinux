#!/bin/bash
#
# build_deb.sh - Construye el paquete .deb de Antivinux.
#
# Uso:
#   ./build_deb.sh
#
# Genera: dist/antivinux_<version>_all.deb
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PACKAGING_DIR="${PROJECT_DIR}/packaging"
BUILD_DIR="${PACKAGING_DIR}/build"
DIST_DIR="${PROJECT_DIR}/dist"
PKG_NAME="antivinux"

# ---------------------------------------------------------------------------
# Comprobaciones previas
# ---------------------------------------------------------------------------
HAVE_DPKG_DEB=0
if command -v dpkg-deb >/dev/null 2>&1; then
    HAVE_DPKG_DEB=1
else
    echo "AVISO: no se encontro 'dpkg-deb'; se usara el generador interno en Python." >&2
    echo "       Para un paquete nativo instala dpkg: sudo apt install dpkg" >&2
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: se requiere python3." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Version del paquete desde antivinux/__init__.py
# ---------------------------------------------------------------------------
VERSION="$(python3 - "${PROJECT_DIR}/antivinux/__init__.py" <<'PY'
import re, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    match = re.search(r'__version__\s*=\s*"([^"]+)"', fh.read())
print(match.group(1) if match else "0.0.0")
PY
)"

echo "==> Construyendo ${PKG_NAME} ${VERSION}"

# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${DIST_DIR}"

ROOT="${BUILD_DIR}"
install -d "${ROOT}/usr/bin"
install -d "${ROOT}/usr/lib/${PKG_NAME}"
install -d "${ROOT}/usr/share/applications"
install -d "${ROOT}/usr/share/metainfo"
install -d "${ROOT}/usr/share/icons/hicolor/scalable/apps"
install -d "${ROOT}/usr/share/pixmaps"
install -d "${ROOT}/usr/share/polkit-1/actions"
install -d "${ROOT}/usr/share/doc/${PKG_NAME}"

# ---------------------------------------------------------------------------
# Codigo de la aplicacion
# ---------------------------------------------------------------------------
cp -r "${PROJECT_DIR}/antivinux" "${ROOT}/usr/lib/${PKG_NAME}/antivinux"
cp "${PROJECT_DIR}/antivinux-launcher.py" "${ROOT}/usr/lib/${PKG_NAME}/antivinux-launcher.py"
find "${ROOT}/usr/lib/${PKG_NAME}" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "${ROOT}/usr/lib/${PKG_NAME}" -name '*.pyc' -delete 2>/dev/null || true

# ---------------------------------------------------------------------------
# Lanzador /usr/bin/antivinux
# ---------------------------------------------------------------------------
cat > "${ROOT}/usr/bin/${PKG_NAME}" <<'EOF'
#!/bin/sh
# Lanzador de Antivinux
exec python3 /usr/lib/antivinux/antivinux-launcher.py "$@"
EOF
chmod 0755 "${ROOT}/usr/bin/${PKG_NAME}"

# Script auxiliar de actualizacion de la base de datos
install -m 0755 "${PROJECT_DIR}/data/antivinux-update-db.sh" \
    "${ROOT}/usr/bin/antivinux-update-db"

# Asistente privilegiado de autoactualizacion
install -m 0755 "${PROJECT_DIR}/data/antivinux-self-update.sh" \
    "${ROOT}/usr/bin/antivinux-self-update"

# ---------------------------------------------------------------------------
# Datos de escritorio, iconos y politicas
# ---------------------------------------------------------------------------
install -m 0644 "${PROJECT_DIR}/data/org.antivinux.app.desktop" \
    "${ROOT}/usr/share/applications/org.antivinux.app.desktop"
install -m 0644 "${PROJECT_DIR}/data/org.antivinux.app.appdata.xml" \
    "${ROOT}/usr/share/metainfo/org.antivinux.app.appdata.xml"
install -m 0644 "${PROJECT_DIR}/data/antivinux.svg" \
    "${ROOT}/usr/share/icons/hicolor/scalable/apps/antivinux.svg"
install -m 0644 "${PROJECT_DIR}/data/antivinux.svg" \
    "${ROOT}/usr/share/pixmaps/antivinux.svg"
install -m 0644 "${PROJECT_DIR}/data/org.antivinux.policy" \
    "${ROOT}/usr/share/polkit-1/actions/org.antivinux.policy"

# ---------------------------------------------------------------------------
# Documentacion
# ---------------------------------------------------------------------------
install -m 0644 "${PROJECT_DIR}/README.md" \
    "${ROOT}/usr/share/doc/${PKG_NAME}/README.md"
gzip -9n -c "${PROJECT_DIR}/debian/changelog" > \
    "${ROOT}/usr/share/doc/${PKG_NAME}/changelog.Debian.gz"
chmod 0644 "${ROOT}/usr/share/doc/${PKG_NAME}/changelog.Debian.gz"

cat > "${ROOT}/usr/share/doc/${PKG_NAME}/copyright" <<EOF
Copyright (C) 2026 Jose Manuel Bernabeu Mejias
Calle Medico Rafael Navarro 2 2C
Novelda 03660 Alicante, Espana

Antivinux se distribuye bajo los terminos de la Licencia Publica General
de GNU, version 3 (GPL-3.0).

En sistemas Debian, el texto completo de la licencia se encuentra en
/usr/share/common-licenses/GPL-3.

Este paquete utiliza ClamAV como motor de deteccion. ClamAV es un
proyecto independiente distribuido bajo GPL-2.0.
EOF
chmod 0644 "${ROOT}/usr/share/doc/${PKG_NAME}/copyright"

# ---------------------------------------------------------------------------
# Metadata DEBIAN
# ---------------------------------------------------------------------------
INSTALLED_SIZE="$(du -sk "${ROOT}/usr" | cut -f1)"
sed -e "s/@VERSION@/${VERSION}/g" \
    -e "s/@SIZE@/${INSTALLED_SIZE}/g" \
    "${PACKAGING_DIR}/control.in" > "${ROOT}/DEBIAN/control"
# dpkg-deb exige un salto de linea final en el campo Description.
if [ -n "$(tail -c 1 "${ROOT}/DEBIAN/control")" ]; then
    printf '\n' >> "${ROOT}/DEBIAN/control"
fi

install -m 0755 "${PACKAGING_DIR}/postinst" "${ROOT}/DEBIAN/postinst"
install -m 0755 "${PACKAGING_DIR}/prerm" "${ROOT}/DEBIAN/prerm"
install -m 0755 "${PACKAGING_DIR}/postrm" "${ROOT}/DEBIAN/postrm"

# ---------------------------------------------------------------------------
# Construccion
# ---------------------------------------------------------------------------
OUTPUT="${DIST_DIR}/${PKG_NAME}_${VERSION}_all.deb"
if [ "${HAVE_DPKG_DEB}" -eq 1 ]; then
    # -Zgzip garantiza compatibilidad con versiones antiguas de dpkg
    # (Zorin 16/17, Debian 11, Ubuntu 20.04), que no soportan zstd.
    if dpkg-deb --help 2>&1 | grep -q -- '--root-owner-group'; then
        dpkg-deb -Zgzip --root-owner-group --build "${ROOT}" "${OUTPUT}"
    else
        dpkg-deb -Zgzip --build "${ROOT}" "${OUTPUT}"
    fi
else
    python3 "${PACKAGING_DIR}/deb_builder.py" "${ROOT}" "${OUTPUT}"
fi

echo
echo "==> Paquete generado: ${OUTPUT}"
echo "    Instalacion:   sudo apt install ./${PKG_NAME}_${VERSION}_all.deb"
echo "    o bien:        sudo dpkg -i ${OUTPUT} && sudo apt -f install"
echo
if [ "${HAVE_DPKG_DEB}" -eq 1 ]; then
    dpkg-deb --info "${OUTPUT}" || true
fi