"""Genera el paquete ZIP de entrega de Mi Botiquín Digital.

Incluye solo el código fuente (nada de base de datos, entornos virtuales,
archivos subidos ni compilados) para que el paquete se pueda entregar y
ejecutar en otro equipo.

Uso:
    python scripts/empaquetar_entrega.py
    python scripts/empaquetar_entrega.py --salida otro.zip
"""
import argparse
import os
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

#: Archivos y carpetas que nunca entran al paquete.
EXCLUIDOS_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "staticfiles",
    "media",
    "logs",
    "node_modules",
    ".idea",
    ".vscode",
}

EXCLUIDOS_SUFIJOS = {".pyc", ".pyo", ".sqlite3", ".log", ".zip"}

EXCLUIDOS_NOMBRES = {".env", "db.sqlite3", "MiBotiquinDigital-entrega.zip"}

#: Contenido que sí se entrega.
ARCHIVOS_RAIZ = [
    ".env.example",
    ".gitignore",
    "README.md",
    "manage.py",
    "requirements.txt",
    "run_lan.ps1",
    "run_lan.sh",
    "run_recordatorios.ps1",
    "verificar_lan.py",
]

CARPETAS = [
    "botiquin",
    "botiquin_project",
    "cuentas",
    "publico",
    "templates",
    "static",
    "scripts",
    "docs",
    "contexto",
]


def _excluido(ruta: Path) -> bool:
    """True si la ruta no debe entrar al paquete."""
    if any(parte in EXCLUIDOS_DIRS for parte in ruta.parts):
        return True
    if ruta.name in EXCLUIDOS_NOMBRES:
        return True
    if ruta.suffix.lower() in EXCLUIDOS_SUFIJOS:
        return True
    if ruta.name.startswith(".") and ruta.name not in EXCLUIDOS_NOMBRES:
        # Solo se conservan los archivos "vacíos" que versiona Git.
        if ruta.name != ".gitkeep":
            return True
    return False


def _archivos_a_empaquetar():
    """Rutas (relativas a la raíz) que componen el paquete."""
    rutas = []

    for nombre in ARCHIVOS_RAIZ:
        ruta = RAIZ / nombre
        if ruta.is_file():
            rutas.append(ruta)

    for carpeta in CARPETAS:
        base = RAIZ / carpeta
        if not base.is_dir():
            continue
        for ruta in sorted(base.rglob("*")):
            if not ruta.is_file():
                continue
            relativa = ruta.relative_to(RAIZ)
            if _excluido(relativa):
                continue
            rutas.append(ruta)

    return rutas


def empaquetar(salida: Path) -> Path:
    """Crea el ZIP de entrega y devuelve su ruta."""
    rutas = _archivos_a_empaquetar()
    salida.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zip:
        for ruta in rutas:
            relativa = ruta.relative_to(RAIZ).as_posix()
            zip.write(ruta, arcname=relativa)

    print(f"Paquete generado: {salida} ({len(rutas)} archivos)")
    return salida


def main():
    parser = argparse.ArgumentParser(description="Empaqueta la entrega de Mi Botiquín Digital.")
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "MiBotiquinDigital-entrega.zip"),
        help="Ruta del ZIP a generar (por defecto en la raíz del proyecto).",
    )
    args = parser.parse_args()
    empaquetar(Path(args.salida).resolve())


if __name__ == "__main__":
    os.chdir(RAIZ)
    main()
