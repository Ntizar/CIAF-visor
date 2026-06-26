#!/usr/bin/env python3
"""
sync.py – Sincronización de informes CIAF desde la web
======================================================

Detecta nuevos informes en la web del CIAF, descarga los PDFs faltantes,
ejecuta el parser y regenera los JSONs.

Uso:
    python3 scripts/sync.py [--check-only]

Flujo:
    1. Scrapear la web de la CIAF por años
    2. Comparar con PDFs ya descargados
    3. Descargar nuevos PDFs
    4. Ejecutar parse_all.py
    5. Regenerar index.json
    6. Git commit + push (si hay cambios)
"""

import os
import re
import sys
import json
import time
import logging
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sync")

BASE_DIR = Path(__file__).resolve().parent.parent
PDFS_DIR = BASE_DIR / "pdfs"
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

# URLs de la web CIAF
CIAF_URLS = {
    "new": "https://www.transportes.gob.es/organos-colegiados/ciaf/informes-finales-de-sucesos-investigados/infofin-{year}",
    "old": "https://www.transportes.gob.es/MFOM/LANG_CASTELLANO/ORGANOS_COLEGIADOS/CIAF/INFORMES/{year}/",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_page(url: str) -> str:
    """Descarga una página web."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning(f"Error descargando {url}: {e}")
        return ""


def extract_pdf_links(html: str) -> list[str]:
    """Extrae enlaces a PDFs del HTML."""
    # Buscar patrones href="...pdf"
    pattern = r'href="([^"]*\.pdf)"'
    links = re.findall(pattern, html, re.IGNORECASE)
    # Normalizar URLs
    normalized = []
    for link in links:
        if link.startswith("/"):
            link = "https://www.transportes.gob.es" + link
        if link.startswith("http"):
            normalized.append(link)
    return list(set(normalized))


def download_pdf(url: str, dest: Path) -> bool:
    """Descarga un PDF."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(dest, "wb") as f:
                f.write(resp.read())
        log.info(f"  Descargado: {dest.name} ({dest.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        log.warning(f"  Error descargando {url}: {e}")
        return False


def check_year(year: int) -> list[str]:
    """Comprueba qué PDFs hay disponibles para un año."""
    # Intentar formato nuevo primero
    url = CIAF_URLS["new"].format(year=year)
    html = fetch_page(url)
    links = extract_pdf_links(html)
    
    if not links:
        # Intentar formato antiguo
        url = CIAF_URLS["old"].format(year=year)
        html = fetch_page(url)
        links = extract_pdf_links(html)
    
    return links


def sync_year(year: int, check_only: bool = False) -> int:
    """Sincroniza un año específico. Devuelve número de PDFs descargados."""
    log.info(f"Año {year}: comprobando...")
    
    # PDFs disponibles en la web
    web_links = check_year(year)
    if not web_links:
        log.info(f"  No se encontraron PDFs para {year}")
        return 0
    
    log.info(f"  PDFs en la web: {len(web_links)}")
    
    # PDFs ya descargados localmente
    year_dir = PDFS_DIR / str(year)
    local_files = set()
    if year_dir.exists():
        local_files = {f.name for f in year_dir.glob("*.pdf")}
    
    log.info(f"  PDFs locales: {len(local_files)}")
    
    # Enlaces nuevos (no descargados)
    new_links = []
    for link in web_links:
        fname = link.split("/")[-1]
        if fname not in local_files:
            new_links.append((link, fname))
    
    log.info(f"  PDFs nuevos: {len(new_links)}")
    
    if check_only or not new_links:
        return 0
    
    # Descargar nuevos PDFs
    downloaded = 0
    for url, fname in new_links:
        dest = year_dir / fname
        if download_pdf(url, dest):
            downloaded += 1
        time.sleep(1)  # Pausa entre descargas
    
    return downloaded


def main():
    log.info("=" * 60)
    log.info("Sincronización CIAF – Detección de nuevos informes")
    log.info("=" * 60)
    
    check_only = "--check-only" in sys.argv
    
    total_new = 0
    for year in range(2007, 2026):
        new = sync_year(year, check_only)
        total_new += new
        time.sleep(0.5)
    
    log.info(f"\nTotal nuevos descargados: {total_new}")
    
    if total_new > 0 and not check_only:
        log.info("Ejecutando parser...")
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "parse_all.py")],
            cwd=str(BASE_DIR)
        )
        
        log.info("Generando tracks ferroviarios...")
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "download-tracks.py")],
            cwd=str(BASE_DIR)
        )
        
        # Git commit
        log.info("Git commit...")
        subprocess.run(["git", "add", "-A"], cwd=str(BASE_DIR))
        subprocess.run(
            ["git", "commit", "-m", f"Sync CIAF: {total_new} nuevos informes ({datetime.now().strftime('%Y-%m-%d')})"],
            cwd=str(BASE_DIR)
        )
        log.info("¡Completado!")
    else:
        log.info("No hay nuevos informes.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
