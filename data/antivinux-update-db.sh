#!/bin/bash
#
# antivinux-update-db.sh - Actualiza la base de datos de virus de ClamAV
# mediante freshclam (main.cvd, daily.cvd, bytecode.cvd).
#
# Uso:
#   sudo antivinux-update-db.sh
#
set -e

LOG_FILE="/var/log/antivinux-update.log"
FRESHCLAM="$(command -v freshclam || true)"

if [ -z "$FRESHCLAM" ]; then
    echo "ERROR: freshclam no esta instalado." >&2
    echo "Instalalo con: sudo apt install clamav-freshclam" >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: se requieren privilegios de administrador." >&2
    echo "Ejecuta: sudo $0" >&2
    exit 1
fi

echo "==> Actualizando definiciones de virus con freshclam..."
echo "==> Registro: ${LOG_FILE}"

# Ejecutar freshclam actualizando el registro del sistema.
"$FRESHCLAM" --no-warnings --verbose 2>&1 | tee -a "$LOG_FILE"

STATUS="${PIPESTATUS[0]:-0}"
if [ "$STATUS" -eq 0 ]; then
    echo "==> Base de datos actualizada correctamente."
elif [ "$STATUS" -eq 1 ]; then
    echo "==> Las definiciones ya estaban actualizadas."
else
    echo "==> freshclam finalizo con codigo ${STATUS}." >&2
    exit "$STATUS"
fi

exit 0