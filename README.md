# Antivinux

Antivirus gráfico para **Zorin OS** y cualquier distribución basada en **Debian/Ubuntu**,
construido sobre el motor de detección de **ClamAV**.

![Antivinux](data/antivinux.svg)

## Características

- Interfaz gráfica GTK con **botones de navegación** (Inicio, Análisis, Actualizaciones,
  Cuarentena, Ajustes, Acerca de).
- **Análisis** de archivos, carpetas o del disco completo con resultados en tiempo real.
- **Cuarentena** para aislar, restaurar o eliminar archivos detectados.
- **Base de datos de virus de ClamAV**: `main.cvd`, `daily.cvd` y `bytecode.cvd`.
- **Actualizaciones gestionadas por `freshclam`** (servicio `clamav-freshclam`).
- Notificaciones de escritorio y exportación de informes de análisis.
- Empaquetado en formato **`.deb`** con todas sus dependencias declaradas.
- Repositorio: <https://github.com/jmbermejias/Antivinux>

## Requisitos

- Zorin OS 16/17, Ubuntu 20.04+, Debian 11+ (o derivados).
- Python 3.6 o superior con PyGObject (`python3-gi`).
- ClamAV (`clamav`, `clamav-base`, `clamav-freshclam`).
- `pkexec` (PolicyKit) para las actualizaciones con privilegios.

Todas las dependencias se resuelven automáticamente al instalar el paquete `.deb`.

## Instalación

### Opción 1: Paquete `.deb` (recomendado)

```bash
git clone https://github.com/jmbermejias/Antivinux.git
cd Antivinux
./packaging/build_deb.sh
sudo apt install ./dist/antivinux_1.0.0_all.deb
```

`apt` instalará automáticamente ClamAV, `freshclam` y las dependencias de Python/GTK.

También puedes instalar el `.deb` ya compilado desde la sección
[Releases](https://github.com/jmbermejias/Antivinux/releases):

```bash
sudo apt install ./antivinux_1.0.0_all.deb
```

### Opción 2: Ejecución directa desde el código fuente

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-notify-0.7 \
                 clamav clamav-freshclam clamav-base policykit-1
python3 antivinux-launcher.py
```

### Opción 3: Instalación con pip (solo la aplicación)

```bash
pip3 install .
antivinux
```

## Uso

Inicia la aplicación desde el menú de aplicaciones (busca **Antivinux**) o ejecuta:

```bash
antivinux
```

Acciones rápidas de línea de comandos:

```bash
antivinux --scan-home   # abre la aplicación en la pantalla de análisis
antivinux --update      # abre la pantalla de actualizaciones
antivinux --version
```

### Actualización de la base de datos

La base de datos de virus se compone de los archivos oficiales de ClamAV:

| Archivo         | Contenido                                    |
|-----------------|----------------------------------------------|
| `main.cvd`      | Firmas principales de virus                  |
| `daily.cvd`     | Firmas diarias y detecciones recientes       |
| `bytecode.cvd`  | Reglas de bytecode para detecciones avanzadas|

Se actualizan mediante **`freshclam`**, que se ejecuta:

1. Como servicio del sistema (`clamav-freshclam`) tras instalar Antivinux.
2. Manualmente desde la aplicación, usando `pkexec` para solicitar privilegios.
3. Desde la terminal con `sudo freshclam`.

Los archivos se almacenan en `/var/lib/clamav`.

## Estructura del proyecto

```
Antivinux/
├── antivinux/                 # Código de la aplicación
│   ├── __main__.py            # Punto de entrada
│   ├── backend/               # Integración con ClamAV, freshclam y cuarentena
│   │   ├── __init__.py        # Utilidades de definiciones de virus
│   │   ├── clamav.py          # Escaneo con clamscan
│   │   ├── update.py          # Actualizaciones con freshclam
│   │   └── quarantine.py      # Gestión de cuarentena
│   ├── ui/
│   │   ├── window.py          # Ventana principal con navegación
│   │   └── pages/             # Páginas de la interfaz
│   └── config.py              # Configuración del usuario
├── data/                      # Lanzador, iconos y políticas polkit
├── debian/                    # Empaquetado Debian (dpkg-buildpackage)
├── packaging/
│   ├── build_deb.sh           # Constructor del paquete .deb
│   ├── control.in             # Plantilla de metadatos
│   ├── postinst / prerm / postrm
├── setup.py
└── README.md
```

## Construcción del paquete Debian

Con el script incluido (no requiere `debhelper`):

```bash
./packaging/build_deb.sh
```

O con el flujo estándar de Debian:

```bash
sudo apt install debhelper dh-python python3-all python3-setuptools
dpkg-buildpackage -us -uc -b
```

## Releases automáticas

El repositorio incluye el flujo de trabajo
[`.github/workflows/build-deb.yml`](.github/workflows/build-deb.yml) que, en cada
`push` a `main`/`master`:

1. Ejecuta las pruebas del núcleo.
2. Construye el paquete `.deb`.
3. Publica una **nueva release** con el `.deb` adjunto, generando
   automáticamente las notas a partir de los cambios.

La versión se incrementa de forma automática (`1.0.<nº de ejecución>`). Si se
empuja una etiqueta `vX.Y.Z`, se usa esa versión para la release.

## Contribuir

Las contribuciones son bienvenidas. Abre un *issue* o envía un *pull request* en
<https://github.com/jmbermejias/Antivinux>.

## Licencia

Antivinux se distribuye bajo la **GNU General Public License v3.0**.
ClamAV es un proyecto independiente bajo GPL-2.0.
