#!/usr/bin/env python3
"""
parse_all.py – Parser integral de informes CIAF
=================================================
Procesa todos los PDFs de accidentes ferroviarios del CIAF y genera archivos
JSON estructurados. Soporta tres formatos de informe:

  - Formato 1 (pre-RD 810/2007): informes de 2007
  - Formato 2 (RD 810/2007): informes de 2008–2013
  - Formato 3 (RD 623/2014): informes de 2014–2025

Uso:
    python3 scripts/parse_all.py

Salida:
    data/reports/YYYY.json     – informes por año
    data/index.json            – índice global
    data/relations.json        – relaciones entre informes
    data/images/               – imágenes extraídas de los PDFs
"""

import os
import re
import sys
import json
import time
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
PDFS_DIR = BASE_DIR / "pdfs"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
IMAGES_DIR = DATA_DIR / "images"
SCRIPTS_DIR = BASE_DIR / "scripts"

MEMORIA_URL_TEMPLATE = "https://www.transportes.gob.es/organos-colegiados/ciaf/memorias-anuales/memoriasanuales" 
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CIAF-Visor/1.0"

# Años con PDFs de informes (excluyendo normativa y memorias)
YEARS_WITH_REPORTS = list(range(2007, 2026))

# Número de intentos para geocodificación
GEOCODE_RETRIES = 2
GEOCODE_DELAY = 1.1  # segundos entre peticiones a Nominatim
GEOCODE_ENABLED = True  # Se puede desactivar con --no-geocode

# Coordenadas locales de estaciones (sin necesidad de Nominatim)
STATION_COORDS: dict = {}
try:
    _coords_path = BASE_DIR / "data" / "station-coords.json"
    if _coords_path.exists():
        with open(_coords_path, encoding='utf-8') as _f:
            STATION_COORDS = json.load(_f)
        log.info(f"Cargadas {len(STATION_COORDS)} estaciones con coordenadas locales")
except Exception:
    pass

# Herramientas del sistema (poppler-utils)
PDFTEXT_BIN = "/usr/bin/pdftotext"
PDFIMAGES_BIN = "/usr/bin/pdfimages"
PDFTOPPM_BIN = "/usr/bin/pdftoppm"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("parse_all")


# ===========================================================================
# Utilidades
# ===========================================================================

def md5_of_file(filepath: Path) -> str:
    """Calcula el MD5 de un archivo."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(text: str) -> str:
    """Limpia texto extraído de PDF: normaliza espacios, elimina headers repetidos."""
    if not text:
        return ""
    # Reemplazar múltiples espacios por uno solo (pero preservar saltos de línea)
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Eliminar líneas solo con espacios
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Eliminar headers de CIAF repetidos
    header_patterns = [
        r'(?:A\s+)?MINISTERIO\s+DE\s+FOMENTO.*?FERROVIARIOS',
        r'SUBSECRETAR[ÍI]A.*?FERROVIARIOS',
        r'COMISI[ÓO]N\s+DE\s+INVESTIGACI[ÓO]N\s+DE\s+ACCIDENTES\s+FERROVIARIOS',
        r'CIAF\s*Comisión de Investigación de.*?Ferroviarios',
    ]
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Normaliza espacios múltiples en una línea."""
    return re.sub(r' {2,}', ' ', text.strip())


# ===========================================================================
# Extracción de texto con markitdown
# ===========================================================================

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrae texto de un PDF usando PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        log.warning(f"PyMuPDF falló para {pdf_path.name}: {e}")
        # Fallback a markitdown
        return extract_text_markitdown(pdf_path)


def extract_text_markitdown(pdf_path: Path) -> str:
    """Fallback: extrae texto con markitdown."""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(pdf_path))
        return result.text_content if result else ""
    except Exception as e:
        log.warning(f"markitdown falló para {pdf_path.name}: {e}")
        return ""


# ===========================================================================
# Extracción de imágenes
# ===========================================================================

def extract_images_from_pdf(pdf_path: Path, report_id: str, year: int) -> list[str]:
    """Extrae imágenes de un PDF usando PyMuPDF. Devuelve lista de rutas."""
    img_dir = IMAGES_DIR / str(year) / report_id
    img_dir.mkdir(parents=True, exist_ok=True)
    extracted = []

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        img_count = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extraer imágenes incrustadas
            images = page.get_images(full=True)
            for img_index, img_info in enumerate(images):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        ext = base_image.get("ext", "png")
                        img_bytes = base_image["image"]
                        img_name = f"fig{img_count:02d}.{ext}"
                        img_path = img_dir / img_name
                        with open(img_path, "wb") as f:
                            f.write(img_bytes)
                        extracted.append(str(img_path.relative_to(BASE_DIR)))
                        img_count += 1
                except Exception:
                    continue
        
        doc.close()
        
        # Si no se encontraron imágenes incrustadas, renderizar páginas como imagen
        if not extracted:
            doc = fitz.open(str(pdf_path))
            for page_num in range(min(len(doc), 3)):  # Primeras 3 páginas
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_name = f"page{page_num+1:02d}.png"
                img_path = img_dir / img_name
                pix.save(str(img_path))
                extracted.append(str(img_path.relative_to(BASE_DIR)))
            doc.close()
            
    except Exception as e:
        log.warning(f"Extracción de imágenes falló para {pdf_path.name}: {e}")

    return extracted


# ===========================================================================
# Geocodificación
# ===========================================================================

# Cache global para no repetir peticiones
_geo_cache: dict[str, tuple[Optional[float], Optional[float]]] = {}


def _normalize_station_name(name: str) -> str:
    """Normaliza nombre de estación para matching contra station-coords.json."""
    import unicodedata
    n = name.strip().upper()
    # Quitar tildes
    n = ''.join(c for c in unicodedata.normalize('NFD', n) if unicodedata.category(c) != 'Mn')
    # Quitar guiones/espacios extra
    n = re.sub(r'[\s\-]+', ' ', n).strip()
    return n


def _lookup_local_coords(station_name: str, province: str = "") -> tuple:
    """Busca coordenadas en station-coords.json con fuzzy matching."""
    if not STATION_COORDS:
        return None, None
    
    norm = _normalize_station_name(station_name)
    
    # 1. Match exacto
    for key, coords in STATION_COORDS.items():
        if _normalize_station_name(key) == norm:
            return coords['lat'], coords['lng']
    
    # 2. Match sin espacios (GRANOLLERS-CENTRE → GRANOLLERS CENTRE)
    norm_nospace = norm.replace(' ', '')
    for key, coords in STATION_COORDS.items():
        if _normalize_station_name(key).replace(' ', '') == norm_nospace:
            return coords['lat'], coords['lng']
    
    # 3. Match parcial: la estación empieza o termina con la clave
    for key, coords in STATION_COORDS.items():
        kn = _normalize_station_name(key)
        if kn.startswith(norm) or norm.startswith(kn):
            return coords['lat'], coords['lng']
        # "MADRID CHAMARTÍN" vs "CHAMARTÍN"
        if len(norm) > 4 and kn in norm:
            return coords['lat'], coords['lng']
        if len(kn) > 4 and norm in kn:
            return coords['lat'], coords['lng']
    
    return None, None


def geocode_station(station_name: str, province: str = "") -> tuple[Optional[float], Optional[float]]:
    """Geocodifica una estación de tren. Primero local, luego Nominatim."""
    if not station_name:
        return None, None
    
    cache_key = f"{station_name}|{province}".lower().strip()
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]
    
    # 1. Lookup local (instantáneo, sin API)
    lat, lng = _lookup_local_coords(station_name, province)
    if lat is not None:
        _geo_cache[cache_key] = (lat, lng)
        return lat, lng
    
    # 2. Nominatim (solo si no encontrado localmente y habilitado)
    if not GEOCODE_ENABLED:
        _geo_cache[cache_key] = (None, None)
        return None, None
    
    import urllib.request
    import urllib.parse as _urlparse
    
    clean_name = station_name.strip()
    clean_name = re.sub(r'\s+', ' ', clean_name)
    
    queries = [f"{clean_name} España"]
    if province:
        queries.append(f"{clean_name} {province}")
    simplified = re.sub(r'\b(Clasificación|Clasificacion|Terminal|Central|Norte|Sur|Este|Oeste)\b', '', clean_name).strip()
    if simplified and simplified != clean_name:
        queries.append(f"{simplified} España")
    
    for query in queries:
        try:
            params = _urlparse.urlencode({
                'q': query, 'format': 'json', 'limit': 5, 'countrycodes': 'es',
            })
            url = f"{NOMINATIM_URL}?{params}"
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=10)
            raw = resp.read()
            resp.close()
            data = json.loads(raw.decode())
            
            if data:
                best = None
                for d in data:
                    t = d.get('type', '')
                    c = d.get('class', '')
                    if t in ('station', 'train_station') and c in ('railway', 'building'):
                        best = d
                        break
                    if c == 'railway':
                        best = d
                        break
                if not best:
                    best = data[0]
                lat = float(best['lat'])
                lng = float(best['lon'])
                _geo_cache[cache_key] = (lat, lng)
                time.sleep(GEOCODE_DELAY)
                return lat, lng
        except Exception as e:
            log.warning(f"Geo failed for '{query}': {e}")
            time.sleep(0.5)
    
    _geo_cache[cache_key] = (None, None)
    return None, None


# ===========================================================================
# Detección de formato
# ===========================================================================

def detect_format(text: str, year: int) -> int:
    """
    Detecta el formato del informe:
      1 = pre-RD 810/2007 (2007)
      2 = RD 810/2007 (2008-2013)
      3 = RD 623/2014 (2014-2025)
    """
    if year <= 2007:
        return 1
    if year <= 2013:
        return 2
    return 3

    # Verificación adicional basada en contenido
    # (ya retornamos por año, pero por si acaso)


# ===========================================================================
# Parsing de metadatos básicos (común a todos los formatos)
# ===========================================================================

def extract_expediente(text: str) -> str:
    """Extrae número de expediente/informe."""
    patterns = [
        r'IF\s+(\d+/\d{4})',                                    # IF 64/2024
        r'IF\)\s*(\d+/\d{4})',                                  # IF) 64/2024
        r'n[º°]\s*(\d+/\d{4})',                                 # nº 065/2007
        r'N[º°]\s*(\d+/\d{4})',                                 # Nº 065/2007
        r'(?:accidente|incidente)\s+(?:ferroviario\s+)?n[º°]\s*(\d+/\d{4})',
        r'(\d{3,4})/(\d{4})',                                   # 0011/2009
    ]
    for pat in patterns:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def extract_tipo(text: str, filename: str) -> str:
    """Determina si es accidente, incidente o avería."""
    text_lower = text[:3000].lower()
    filename_lower = filename.lower()

    # Check for "accidente"
    if re.search(r'accidente\s+ferroviario', text_lower):
        return "accidente"
    if "accidente" in text_lower:
        return "accidente"

    # Check for "incidente"
    if re.search(r'incidente\s+ferroviario', text_lower):
        return "incidente"
    if "incidente" in text_lower:
        return "incidente"

    # Check for "avería"
    if "avería" in text_lower or "averia" in text_lower:
        return "avería"

    # Por defecto basado en severidad del contenido
    return "accidente"


def extract_fecha_suceso(text: str) -> str:
    """Extrae la fecha del suceso en formato YYYY-MM-DD."""
    # Patrón principal: "OCURRIDO EL DÍA DD.MM.YYYY"
    patterns = [
        r'OCURRIDO\s+EL\s+(?:D[ÍI]A\s+)?(\d{1,2})[./](\d{1,2})[./](\d{4})',
        r'ocurrido\s+el\s+(?:d[íi]a\s+)?(\d{1,2})[./](\d{1,2})[./](\d{4})',
        r'fecha\s+del\s+(?:suceso|accidente|incidente)[.:]*\s*(\d{1,2})[./](\d{1,2})[./](\d{4})',
        r'el\s+d[íi]a\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) == 3:
                day, month, year = groups
                # Si el mes es texto, convertir
                if not month.isdigit():
                    meses = {
                        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                    }
                    month = meses.get(month.lower(), '01')
                try:
                    d = int(day)
                    mo = int(month)
                    y = int(year)
                    return f"{y:04d}-{mo:02d}-{d:02d}"
                except ValueError:
                    continue
    return ""


def extract_hora_suceso(text: str) -> str:
    """Extrae la hora del suceso."""
    patterns = [
        r'(?:a\s+las?\s+)?(\d{1,2})[:.](\d{2})\s*(?:horas?|h\.?)',
        r'hora[s]?\s*(?:del\s+suceso)?[:.]?\s*(\d{1,2})[:.](\d{2})',
        r'D[ÍI]A\s*/\s*HORA[:.]?\s*\d{1,2}[./]\d{1,2}[./]\d{2,4}\.?\s*/?\s*(\d{1,2})[:.](\d{2})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
    return ""


def extract_estacion(text: str) -> str:
    """Extrae nombre de estación o ubicación limpio."""
    MAX_STATION_LEN = 35

    # Stop phrases/words that mark the end of a station name
    # Order matters: longer patterns first
    _STOP = (
        r'procedente\s+de|con\s+destino|que\s+cubr[íi]a|en\s+condiciones'
        r'|desde\s+donde|donde\s+no|donde\s+se|donde\s+hab[íi]a'
        r'|observa\s+que|en\s+la\s+que|en\s+el\s+que|en\s+la\s+cual'
        r'|en\s+el\s+cual|que\s+realiz[óa]|que\s+prest[óa]|que\s+circul'
        r'|con\s+ocasi[oó]n|como\s+consecuencia|a\s+causa\s+de'
        r'|sin\s+prescri|en\s+traz|en\s+zona|en\s+el\s+interior'
        r'|donde\s+en|donde\s+se\s+encontr|donde\s+produ|donde\s+ten'
        r'|en\s+su\s+tramo|del\s+trazado|del\s+carril|en\s+sentido'
        r'|que\s+afect[óa]|con\s+motivo|en\s+punto|en\s+el\s+punto'
    )

    # Boundary: sentence-ending or structural markers
    _BOUND = r'(?:[.,;:!?]|\s+(?:' + _STOP + r')|\s*\n|\s*\(|\s*$)'

    patterns = [
        # RD 623/2014: "en la estación de X"
        r'(?:en\s+la\s+)?estaci[oó]n\s+de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s\-]*?)' + _BOUND,
        # RD 810/2007: "Lugar: Estación de X"
        r'[Ll]ugar:\s*(?:[Ee]stación\s+de\s+)?([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s\-]*?)' + _BOUND,
        # Pre-RD: "Apeadero de X" or "Estación de X"
        r'(?:Apeadero|Estación| apeadero| estación)\s+de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s\-]*?)' + _BOUND,
        # "EN LA ESTACIÓN DE X"
        r'(?:EN\s+LA\s+)?ESTACI[ÓO]N\s+DE\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\-]*?)' + _BOUND,
        # "estación de X (PK"
        r'estaci[oó]n\s+de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s\-]+?)\s*\(?\s*[Pp]\.?[Kk]',
    ]

    # Trailing words to strip (prepositions, conjunctions, articles, etc.)
    _TRAIL = re.compile(
        r'\s+(?:de|del|en|el|la|los|las|al|a|con|por|para|desde|hasta|sobre'
        r'|donde|observa|procedente|condiciones|sentido|trazado|tramo'
        r'|interior|prescrita|punto|motivo|consecuencia|afect|produ|cubr'
        r'|prest|realiz|circul|encontr|tenía|había|se)\s*$',
        re.IGNORECASE
    )

    for pat in patterns:
        m = re.search(pat, text[:10000], re.IGNORECASE)
        if m:
            est = m.group(1).strip()
            # Normalise whitespace
            est = re.sub(r'\s+', ' ', est).strip()
            # Remove trailing parens content and punctuation
            est = re.sub(r'\(.*', '', est).strip()
            est = est.strip('.,;:!?')
            # Strip trailing prepositions / conjunctions
            for _ in range(3):  # repeat a few times for nested cases
                new_est = _TRAIL.sub('', est).strip('.,;:!?')
                if new_est == est:
                    break
                est = new_est
            # Enforce max length
            if len(est) > MAX_STATION_LEN:
                # Try to cut at a word boundary
                cut = est[:MAX_STATION_LEN].rfind(' ')
                if cut > 10:
                    est = est[:cut].strip()
                else:
                    est = est[:MAX_STATION_LEN].strip()
            # Final validation: must be 3+ chars, must start with a letter
            if len(est) >= 3 and est[0].isalpha():
                return est
    return ""


def extract_provincia(text: str) -> str:
    """Extrae la provincia."""
    # Lista de provincias españolas
    provincias = [
        "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila",
        "Badajoz", "Barcelona", "Bizkaia", "Burgos", "Cáceres", "Cádiz",
        "Cantabria", "Castellón", "Ciudad Real", "Córdoba", "A Coruña",
        "Cuenca", "Gipuzkoa", "Girona", "Granada", "Guadalajara",
        "Huelva", "Huesca", "Illes Balears", "Jaén", "León", "Lleida",
        "Lugo", "Madrid", "Málaga", "Murcia", "Navarra", "Ourense",
        "Palencia", "Las Palmas", "Pontevedra", "La Rioja", "Salamanca",
        "Santa Cruz de Tenerife", "Segovia", "Sevilla", "Soria",
        "Tarragona", "Teruel", "Toledo", "Valencia", "Valladolid",
        "Zamora", "Zaragoza", "Vizcaya"
    ]
    
    # 1. Buscar "Provincia: X" (más específico)
    patterns = [
        r'[Pp]rovincia\s*[:\.]?\s*([A-ZÁÉÍÓÚÑ][a-zA-Záéíóúñ]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text[:10000], re.IGNORECASE)
        if m:
            prov = m.group(1).strip()
            for p in provincias:
                if prov.lower() == p.lower():
                    return p
    
    # 2. Inferir provincia del nombre de estación
    # Ejemplo: "Cuenca-Fernando" → Cuenca, "León Clasificación" → León
    estacion_match = re.search(r'estaci[oó]n\s+de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s\-]+?)(?:\s*\(|\.\s|\,\s|\n)', text[:10000], re.IGNORECASE)
    if estacion_match:
        estacion_nombre = estacion_match.group(1).strip()
        for p in provincias:
            if p.lower() in estacion_nombre.lower():
                return p
    
    # 3. Buscar la PRIMERA provincia en el cuerpo del texto
    # Excluir headers (primeros 500 chars) y firma final ("Madrid, a XX de...")
    text_body = text[500:] if len(text) > 500 else text
    # Excluir la firma final
    text_body = re.sub(r'Madrid,\s+a\s+\d+.*$', '', text_body, flags=re.DOTALL)
    
    first_pos = len(text_body)
    first_prov = ""
    for prov in provincias:
        m = re.search(rf'\b{re.escape(prov)}\b', text_body, re.IGNORECASE)
        if m and m.start() < first_pos:
            first_pos = m.start()
            first_prov = prov
    
    return first_prov


def extract_trenes(text: str) -> list[dict]:
    """Extrae información de trenes implicados."""
    trenes = []
    seen = set()
    
    # Patrón principal: "tren de viajeros 8604", "tren 18079", "tren de mercancías"
    patterns = [
        r'tren\s+(?:de\s+(?:viajeros|mercanc[ií]as|man[io]bras|pasajeros)\s+)?([A-Z]?\d{3,6}[A-Z]?)\b',
        r'tren\s+(?:de\s+(?:viajeros|mercanc[ií]as|man[io]bras|pasajeros)\s+)?(\d{3,6})\b',
        r'tren\s+n[uú]mero\s+(\d{3,6})',
    ]
    
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            t = m.group(1).strip()
            # Filtrar: solo números de tren (3+ dígitos) o IDs alfanuméricos
            if t and t not in seen and (len(t) >= 3 or (t.isdigit() and int(t) > 100)):
                seen.add(t)
                # Intentar capturar tipo de tren
                ctx = text[max(0, m.start()-50):m.end()+50]
                tipo = ""
                if re.search(r'viajeros', ctx, re.IGNORECASE):
                    tipo = "viajeros"
                elif re.search(r'mercanc', ctx, re.IGNORECASE):
                    tipo = "mercancías"
                elif re.search(r'manio[bp]ras', ctx, re.IGNORECASE):
                    tipo = "maniobras"
                trenes.append({"id_tren": t, "tipo": tipo, "descripcion": ""})
    
    return trenes


def extract_entidades(text: str) -> list[str]:
    """Extrae entidades ferroviarias mencionadas con normalización precisa."""
    entidades = set()

    known = [
        "Renfe Viajeros", "Renfe Mercancías", "Renfe Operadora",
        "ADIF AV", "ADIF", "FCC", "Ferrocarriles de la Generalitat",
        "FGC", "TRAP", "Euskotren", "FEVE",
        "Administrador de Infraestructuras Ferroviarias",
        "Agencia Estatal de Seguridad Ferroviaria",
        "Metro de Madrid", "Metro de Barcelona",
        "FGV", "TRAM", "TMB",
    ]

    text_lower = text.lower()

    # Detectar variantes específicas (orden importa: más específico primero)
    renfe_variants = [
        (r'renfe\s+viajeros', 'Renfe Viajeros'),
        (r'renfe\s+mercanc', 'Renfe Mercancías'),
        (r'renfe\s+operadora', 'Renfe Operadora'),
        (r'renfe\s+media\s+distancia', 'Renfe Media Distancia'),
        (r'renfe', 'RENFE'),
    ]
    adif_variants = [
        (r'adif\s+av\b', 'ADIF AV'),
        (r'adif\s+alta\s+velocidad', 'ADIF AV'),
        (r'adif\s+construcc', 'ADIF Construcciones'),
        (r'adif', 'ADIF'),
    ]
    other_variants = [
        (r'ferrocarriles?\s+de\s+la\s+generalitat', 'FGC'),
        (r'euskotren', 'Euskotren'),
        (r'feve\b', 'FEVE'),
        (r'continental\s+rail', 'Continental Rail'),
        (r'low\s+cost\s+rail', 'Low Cost Rail'),
        (r'transfesa', 'Transfesa Rail'),
        (r'comsa\s+rail', 'COMSA Rail Transport'),
        (r'tracci[oó]n\s+rail', 'Tracción Rail'),
        (r'logitren|logirail', 'Logitren'),
        (r'captrain', 'CAPTRAIN'),
        (r'activa\s+rail', 'Activa Rail'),
        (r'flota\s+bus', 'Flota Bus'),
        (r'metro\s+de\s+madrid', 'Metro de Madrid'),
        (r'metro\s+de\s+barcelona', 'Metro de Barcelona'),
        (r'tmb\b', 'TMB'),
        (r'fgv\b', 'FGV'),
        (r'tram\b', 'TRAM'),
        (r'sevillana\s+de\s+electricidad', 'Sevillana de Electricidad'),
    ]

    # Buscar variantes (orden: más específico primero)
    for pattern, name in renfe_variants:
        if re.search(pattern, text_lower):
            entidades.add(name)
            break  # Solo la más específica

    for pattern, name in adif_variants:
        if re.search(pattern, text_lower):
            entidades.add(name)
            break

    for pattern, name in other_variants:
        if re.search(pattern, text_lower):
            entidades.add(name)

    # Buscar "empresa ferroviaria X" con límite de palabras
    emp_pattern = r'empresa\s+ferroviaria\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-Za-záéíóúñ]{2,}){0,3})'
    for m in re.finditer(emp_pattern, text):
        emp = m.group(1).strip()
        if len(emp) > 3 and len(emp) < 50:
            emp_lower = emp.lower()
            if not any(emp_lower in e.lower() or e.lower() in emp_lower for e in entidades):
                entidades.add(emp)

    # Limpiar: quitar saltos de línea, texto extra, y limitar a 30 chars
    cleaned = set()
    trash_suffixes = [
        'que había', 'que cubría', 'que procedía', 'que realizaba',
        'debían cruzarse', 'hacía su', 'se encuentra', 'dispone de',
        'procedente de', 'procedió en', 'realizaba el', 'cubría el',
        'operaba el', 'prestaba el', 'ejecutaba el',
    ]
    for ent in entidades:
        c = re.sub(r'\s+', ' ', ent).strip()
        c = c.split('\n')[0].strip()
        for suffix in trash_suffixes:
            if c.lower().endswith(suffix):
                c = c[:-len(suffix)].strip()
        if len(c) > 30:
            c = c[:30].rsplit(' ', 1)[0]
        if len(c) > 3:
            cleaned.add(c)

    # Fusionar variantes case-insensitive (RENFE/Renfe → RENFE)
    FINAL_MAP = {
        'renfe': 'RENFE',
        'renfe viajeros': 'Renfe Viajeros',
        'renfe mercancías': 'Renfe Mercancías',
        'renfe operadora': 'Renfe Operadora',
    }
    result = set()
    for c in cleaned:
        cl = c.lower().strip()
        if cl in FINAL_MAP:
            result.add(FINAL_MAP[cl])
        else:
            result.add(c)

    return sorted(result)


def extract_severity(text: str, filename: str) -> str:
    """Determina la gravedad del suceso."""
    text_lower = text[:5000].lower()

    # Buscar víctimas mortales
    victimas_mortales = len(re.findall(
        r'v[íi]ctima[s]?\s+mortal(?:es)?|fallec(?:imiento|i[oó])|muert[oa]',
        text_lower
    ))
    heridos = len(re.findall(r'herido[s]?|lesionado[s]?', text_lower))

    if victimas_mortales > 0:
        return "fatal"
    if heridos > 0:
        return "grave"

    # Verificar si es solo material
    if re.search(r'sin\s+v[íi]ctimas|sin\s+heridos|sin\s+personal\s+afectado', text_lower):
        if re.search(r'da[ñn]os?\s+material|descarrilamiento', text_lower):
            return "leve"
        return "leve"

    return "leve"


def extract_victims_count(text: str) -> int:
    """Extrae número de víctimas mortales."""
    # Primero verificar si NO hay víctimas
    text_lower = text.lower()
    if re.search(r'sin\s+v[íi]ctimas?\s+mortales|no\s+se\s+produjeron?\s+v[íi]ctimas|sin\s+fallec', text_lower):
        return 0
    if re.search(r'se\s+produce[rn]?\s+el\s+fallecimiento\s+de\s+una?\s+persona', text_lower):
        return 1
    
    patterns = [
        r'(\d+)\s+v[íi]ctima[s]?\s+mortal(?:es)',
        r'(\d+)\s+fallec(?:imiento|idos)',
        r'una?\s+fallecida',
        r'una?\s+persona\s+(?:fallecida|muerta)',
        r'resultando\s+fallecida',
        r'resultando\s+muerta',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            if m.lastindex and m.group(1):
                return int(m.group(1))
            return 1
    return 0


def extract_heridos_count(text: str) -> int:
    """Extrae número de heridos."""
    patterns = [
        r'(\d+)\s+herido[s]?',
        r'(\d+)\s+lesionado[s]?',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 0


# ===========================================================================
# Parsing por secciones
# ===========================================================================

def split_sections(text: str) -> dict[str, str]:
    """Divide el texto en secciones numeradas."""
    sections = {}
    # Limpiar headers de CIAF repetidos
    cleaned = re.sub(
        r'(?:SUBSECRETAR[ÍI]A|MINISTERIO|SECRETAR[ÍI]A|COMISI[ÓO]N|FERROVIARIOS|'
        r'Informe\s+(?:final|definitivo)|Investigaci[óo]n\s+del\s+(?:accidente|incidente)|'
        r'P[aá]g\.\s*\d+\s+de\s*\d+|NIPO[:\s]+\d[\d\-]+|Comisi[oó]n\s+de\s+Investigaci[oó]n).*?\n',
        '', text, flags=re.IGNORECASE
    )

    # Buscar patrones de sección: "N. TÍTULO" o "N.TÍTULO" o "N TÍTULO"
    section_pattern = re.compile(
        r'^(\d+(?:\.\d+)*)\.\s*([A-ZÁÉÍÓÚÑ][^\n]{3,80})',
        re.MULTILINE
    )

    matches = list(section_pattern.finditer(cleaned))

    if not matches:
        # Intentar con formato alternativo
        section_pattern = re.compile(
            r'^(\d+)\s+([A-ZÁÉÍÓÚÑ][^\n]{3,80})',
            re.MULTILINE
        )
        matches = list(section_pattern.finditer(cleaned))

    for i, match in enumerate(matches):
        section_num = match.group(1)
        section_title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
        section_text = cleaned[start:end].strip()
        # Eliminar pies de página y headers
        section_text = re.sub(
            r'\d{6,8}-\d{6}-IF[-\w]*.*?(?:\n|$)', '', section_text
        )
        section_text = re.sub(r'P[aá]g\.\s*\d+\s+de\s*\d+.*?\n', '', section_text)
        sections[section_num] = f"[{section_title}] {section_text}"

    return sections


def extract_resumen(sections: dict[str, str], text: str) -> str:
    """Extrae el resumen del informe buscando en el texto crudo."""
    
    # ESTRATEGIA 1: Buscar "RESUMEN DEL ANÁLISIS" (RD 623/2014 format)
    # Evitar el TOC: buscar contenido real (después del header CIAF)
    for pattern in [
        r'RESUMEN\s+DEL\s+AN[AÁ]LISIS\s+Y\s+CONCLUSIONES\s+RELACIONADAS\s+CON\s+EL\s+SUCESO\s*\n\s*(.*?)(?:\n\s*\d+\.\d|\n\s*5\.|\n\s*OBSERVACIONES|\n\s*RECOMENDACIONES)',
        r'RESUMEN\s+DEL\s+AN[AÁ]LISIS\s*\n\s*(.*?)(?:\n\s*\d+\.\d|\n\s*\d+\s*\.|\n\s*CONCLUSIONES)',
        r'1\.\s*RESUMEN\s+(?:DEL\s+AN[AÁ]LISIS\s*)?\n\s*(.*?)(?:\n\s*2\.|\n\s*HECHOS)',
    ]:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Filtrar líneas del TOC (solo puntos y números)
            lines = candidate.split('\n')
            real_lines = []
            for line in lines:
                line_stripped = line.strip()
                # Saltar líneas del TOC (solo ".....37" o "SECCIÓN ......... 5")
                if re.match(r'^[.\.·]+\s*\d+\s*$', line_stripped):
                    continue
                if re.match(r'^[A-ZÁÉÍÓÚÑ\s]+[.\.·]+\d+', line_stripped):
                    continue
                if len(line_stripped) > 10:
                    real_lines.append(line_stripped)
            if real_lines:
                result = ' '.join(real_lines)[:2000]
                # Verificar que no es basura del TOC ni texto en inglés
                if '.....' not in result and len(result) > 50:
                    # Filtrar si empieza con inglés
                    if re.match(r'^[a-z\s]*(?:the |a |an |this |that |there |it |in |on )', result.strip(), re.IGNORECASE):
                        continue
                    return result
    
    # ESTRATEGIA 2: Buscar primer párrafo significativo después de la introducción
    # Evitar headers CIAF (MINISTERIO, SUBSECRETARÍA, etc.)
    intro_end = re.search(r'\n\s*\d+\.\s+[A-Z]', text[2000:15000])
    if intro_end:
        start = 2000 + intro_end.end()
        candidate = text[start:start+2000]
        paragraphs = [p.strip() for p in candidate.split('\n\n') if len(p.strip()) > 50]
        # Filtrar párrafos del TOC
        real_paragraphs = []
        for p in paragraphs:
            if '.....' not in p and 'Pág.' not in p and not re.match(r'^[\d.]+\s', p):
                real_paragraphs.append(p)
                if len(' '.join(real_paragraphs)) > 200:
                    break
        if real_paragraphs:
            return ' '.join(real_paragraphs)[:2000]
    
    # ESTRATEGIA 3: Secciones
    for key in ['1', '0.1', '0']:
        if key in sections:
            sec = sections[key]
            content = re.sub(r'^\[.*?\]\s*', '', sec)
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 20]
            if paragraphs:
                return '\n\n'.join(paragraphs[:3])[:2000]
    
    return 


def extract_factores_humanos(sections: dict[str, str], text: str) -> str:
    """Extrae factores humanos del análisis."""
    result_parts = []

    # Buscar secciones relevantes
    for key, content in sections.items():
        title_match = re.match(r'^\[(.*?)\]', content)
        if title_match:
            title = title_match.group(1).lower()
            if any(kw in title for kw in [
                'factor', 'humano', 'personal', 'interfaz hombre',
                'organización', 'organizacion', 'procedimiento'
            ]):
                text_part = re.sub(r'^\[.*?\]\s*', '', content)
                if len(text_part.strip()) > 30:
                    result_parts.append(text_part.strip()[:1000])

    if result_parts:
        return '\n\n'.join(result_parts)[:2000]

    # Fallback
    m = re.search(
        r'(?:FACTORES?\s+HUMANOS?|INTERFAZ\s+HOMBRE).*?\n(.*?)(?:\n\s*\d+\.\d|\n\s*CONCLUSIONES)',
        text, re.DOTALL | re.IGNORECASE
    )
    if m:
        return m.group(1).strip()[:2000]

    return ""


def extract_infraestructura(sections: dict[str, str], text: str) -> str:
    """Extrae información sobre infraestructura."""
    result_parts = []

    for key, content in sections.items():
        title_match = re.match(r'^\[(.*?)\]', content)
        if title_match:
            title = title_match.group(1).lower()
            if any(kw in title for kw in [
                'infraestructura', 'instalación', 'instalacion', 'vía', 'via',
                'material rodante', 'instalaciones técnicas'
            ]):
                text_part = re.sub(r'^\[.*?\]\s*', '', content)
                if len(text_part.strip()) > 30:
                    result_parts.append(text_part.strip()[:1000])

    if result_parts:
        return '\n\n'.join(result_parts)[:2000]

    return ""


def extract_conclusiones(sections: dict[str, str], text: str) -> str:
    """Extrae las conclusiones."""
    # Buscar sección 4.3 o "CONCLUSIONES"
    for key in sorted(sections.keys()):
        content = sections[key]
        if re.search(r'CONCLUSIONES', content, re.IGNORECASE):
            text_part = re.sub(r'^\[.*?\]\s*', '', content)
            # También incluir subsecciones posteriores
            parts = [text_part.strip()]
            next_keys = [k for k in sections.keys() if k.startswith(key + '.') and 'CONCLUSIONES' not in sections[k]]
            for nk in sorted(next_keys)[:3]:
                nc = re.sub(r'^\[.*?\]\s*', '', sections[nk])
                if len(nc.strip()) > 20:
                    parts.append(nc.strip()[:500])
            return '\n\n'.join(parts)[:2000]

    # Fallback
    m = re.search(
        r'(?:CONCLUSIONES|4\.3\.\s*CONCLUSIONES).*?\n(.*?)(?:\n\s*5\.|\n\s*MEDIDAS|\n\s*RECOMENDACIONES)',
        text, re.DOTALL | re.IGNORECASE
    )
    if m:
        return m.group(1).strip()[:2000]

    return ""


def extract_recomendaciones(sections: dict[str, str], text: str) -> list[dict]:
    """Extrae las recomendaciones directamente del texto crudo del PDF."""
    recomendaciones = []
    
    # ESTRATEGIA 1: Buscar la ÚLTIMA ocurrencia de "RECOMENDACIONES FINALES" en el texto
    rec_section = ""
    all_matches = list(re.finditer(r'RECOMENDACIONES\s+FINALES', text, re.IGNORECASE))
    for m in all_matches:
        start = m.end()
        # Buscar hasta el siguiente número de sección principal o 5000 chars
        end_candidate = min(start + 5000, len(text))
        next_section = re.search(r'\n\s*\d+\s*\.\s+[A-ZÁÉÍÓÚÑ]{3,}', text[start:end_candidate])
        if next_section:
            end_candidate = start + next_section.start()
        candidate = text[start:end_candidate].strip()
        # Si contiene tabla (Destinatario/Número), es la buena
        if 'Destinatario' in candidate or 'Número' in candidate or re.search(r'\d{2,}/\d{2}[-–]\d', candidate):
            rec_section = candidate
            break
    
    # ESTRATEGIA 2: Si no, buscar "RECOMENDACIONES" con tabla de datos
    if not rec_section:
        all_matches2 = list(re.finditer(r'\d+\.\s*RECOMENDACIONES', text, re.IGNORECASE))
        for m in all_matches2:
            start = m.end()
            end_candidate = min(start + 5000, len(text))
            next_section = re.search(r'\n\s*\d+\s*\.\s+[A-ZÁÉÍÓÚÑ]{3,}', text[start:end_candidate])
            if next_section:
                end_candidate = start + next_section.start()
            candidate = text[start:end_candidate].strip()
            if 'Destinatario' in candidate or re.search(r'\d{2,}/\d{2}[-–]\d', candidate):
                rec_section = candidate
                break
    
    # ESTRATEGIA 3: Buscar patrón de tabla con "Destinatario" + "Número" + "Recomendación"
    if not rec_section:
        table_match = re.search(
            r'(?:Destinatario.*?Recomendaci[oó]n)(.*?)(?:\n\s*\d+\s*\.\s+[A-ZÁÉÍÓÚÑ]{3,}|$)',
            text, re.DOTALL | re.IGNORECASE
        )
        if table_match:
            rec_section = table_match.group(1).strip()
    
    if not rec_section:
        return recomendaciones
    
    # Limpiar headers de tabla y basura
    rec_section = re.sub(r'Destinatario\s+(?:Implementador\s+(?:final\s+)?)?N[uú]mero\s+Recomendaci[oó]n', '', rec_section, flags=re.IGNORECASE)
    rec_section = re.sub(r'Implementador\s+final', '', rec_section, flags=re.IGNORECASE)
    # Eliminar líneas TOC (solo puntos y números)
    rec_section = re.sub(r'^[.\.·]+\s*\d+\s*$', '', rec_section, flags=re.MULTILINE)
    rec_section = re.sub(r'^[A-ZÁÉÍÓÚÑ\s]+[.\.·]+\d+', '', rec_section, flags=re.MULTILINE)
    # Eliminar "APPENDIX: ENGLISH..." y todo lo que venga después
    rec_section = re.sub(r'APPENDIX.*$', '', rec_section, flags=re.DOTALL | re.IGNORECASE)
    # Eliminar líneas vacías múltiples
    rec_section = re.sub(r'\n{3,}', '\n\n', rec_section)
    
    if len(rec_section.strip()) < 20:
        return recomendaciones
    
    # Normalizar saltos de línea
    rec_clean = re.sub(r'\n\s*\n', '\n', rec_section)
    
    # Encontrar TODOS los números de recomendación y dividir el texto
    num_pattern = re.compile(r'((?:IF[-\s]?)?\d+/\d{2,4}[-–]\d+)')
    all_nums = list(num_pattern.finditer(rec_clean))
    
    if all_nums:
        for i, m in enumerate(all_nums):
            num = m.group(1).strip()
            # Texto desde después de este número hasta el siguiente
            text_start = m.end()
            text_end = all_nums[i+1].start() if i+1 < len(all_nums) else len(rec_clean)
            texto = rec_clean[text_start:text_end].strip()
            # Limpiar: quitar saltos de línea dobles, headers de página, números de página
            texto = re.sub(r'Comisión de Investigación.*?\n', '', texto, flags=re.IGNORECASE)
            texto = re.sub(r'\n\s*\d+\s*\n', ' ', texto)  # números de página
            texto = re.sub(r'Madrid,\s+a\s+\d+.*$', '', texto, flags=re.DOTALL)  # firma final
            texto = re.sub(r'\s+', ' ', texto).strip()
            
            # Extraer implementador del contexto anterior al número
            ctx_start = max(0, m.start() - 300)
            ctx = rec_clean[ctx_start:m.start()]
            implementador = ""
            ent_match = re.findall(r'(AESF|ADIF|ADIF AV|RENFE|Renfe|CAF|FEVE|FGC|Euskotren|TMB|ACTREN|FCC|Administrador)', ctx, re.IGNORECASE)
            if ent_match:
                implementador = ent_match[-1]
            
            if len(texto) > 10:
                recomendaciones.append({
                    "numero": num,
                    "implementador": implementador,
                    "destinatarios": "",
                    "texto": texto[:800],
                })
    
    if not recomendaciones:
            # ESTRATEGIA C: Fallback - tratar todo como una recomendación
            cleaned = re.sub(r'\s+', ' ', rec_section).strip()
            if len(cleaned) > 20 and 'no se establecen' not in cleaned.lower():
                recomendaciones.append({
                    "numero": "",
                    "implementador": "",
                    "destinatarios": "",
                    "texto": cleaned[:2000],
                })
    
    return recomendaciones


def extract_consecuencias(text: str) -> dict:
    """Extrae información sobre víctimas y daños."""
    victimas_mortales = extract_victims_count(text)
    heridos = extract_heridos_count(text)

    # Daños materiales: buscar si se mencionan, no capturar TOC
    danos = False
    # Buscar "DAÑOS MATERIALES: Sí" o similar en secciones de datos
    danos_header = re.search(
        r'DA[ÑN]OS?\s+MATERIALES\s*[:\n]\s*(S[ií]|No|\w+)',
        text, re.IGNORECASE
    )
    if danos_header:
        val = danos_header.group(1).strip().lower()
        danos = val in ('sí', 'si', 's', 'yes')
    else:
        # Buscar mención de daños materiales en el cuerpo
        danos_body = re.search(
            r'se\s+produjeron?\s+da[ñn]os?\s+material',
            text, re.IGNORECASE
        )
        danos = bool(danos_body)

    return {
        "victimas_mortales": victimas_mortales,
        "heridos": heridos,
        "danos_materiales": danos,
    }


def extract_tags(text: str, tipo: str, severity: str) -> list[str]:
    """Extrae tags relevantes del informe."""
    tags = set()
    tags.add(tipo)
    tags.add(severity)

    # Buscar tipo de suceso específico
    tipo_patterns = [
        (r'descarrilamiento', 'descarrilamiento'),
        (r'colisi[óo]n', 'colisión'),
        (r'atropello', 'atropello'),
        (r'arrollamiento', 'arrollamiento'),
        (r'incendio', 'incendio'),
        (r'v[íi]a\s+obstruida', 'vía obstruida'),
        (r'paso\s+a\s+nivel', 'paso a nivel'),
        (r'se[ñn]alizaci[óo]n', 'señalización'),
        (r'fallo\s+de\s+tracción', 'fallo de tracción'),
        (r'fallo\s+de\s+frenado', 'fallo de frenado'),
        (r'sobrecarga', 'sobrecarga'),
        (r'mercanc[ií]as?\s+peligrosas', 'mercadancías peligrosas'),
        (r'mmpp', 'mercadancías peligrosas'),
        (r'tierra', 'caída de tierra'),
        (r'alud', 'alud'),
        (r'inundaci[óo]n', 'inundación'),
        (r'condicion(?:es)?\s+clim', 'condiciones climatológicas'),
        (r'obras?\s+(?:en|cercan)', 'obras en cercanías'),
        (r'personal', 'factor humano'),
        (r'mantenimiento', 'mantenimiento'),
        (r'procedimiento', 'procedimiento'),
        (r'formación', 'formación'),
        (r'fatiga', 'fatiga'),
        (r'distraction|distraer', 'distraer'),
        (r'organizaci[óo]n', 'factor organizativo'),
    ]

    text_lower = text.lower()
    for pat, tag in tipo_patterns:
        if re.search(pat, text_lower):
            tags.add(tag)

    return sorted(tags)


def extract_tipo_suceso(text: str) -> str:
    """Extrae el tipo específico de suceso."""
    text_lower = text[:5000].lower()

    tipo_patterns = [
        (r'descarrilamiento', 'Descarrilamiento'),
        (r'colisi[óo]n(?:\s+entre\s+trenes?)?', 'Colisión'),
        (r'atropello', 'Atropello'),
        (r'arrollamiento', 'Arrollamiento'),
        (r'incendio', 'Incendio'),
        (r'v[íi]a\s+obstruida', 'Vía obstruida'),
        (r'paso\s+a\s+nivel', 'Paso a nivel'),
        (r'fallo\s+de\s+tracción', 'Fallo de tracción'),
        (r'fallo\s+de\s+frenado', 'Fallo de frenado'),
        (r'escape\s+de\s+material', 'Escape de material'),
        (r'se[ñn]alizaci[óo]n', 'Fallo de señalización'),
        (r'fallo\s+de\s+se[ñn]al', 'Fallo de señalización'),
        (r'obstrucci[óo]n\s+de\s+v[íi]a', 'Obstrucción de vía'),
    ]

    for pat, tipo in tipo_patterns:
        if re.search(pat, text_lower):
            return tipo

    return "Otro"


# ===========================================================================
# Parser principal por formato
# ===========================================================================

def parse_report(pdf_path: Path, year: int) -> Optional[dict]:
    """Parsea un informe PDF y devuelve un diccionario estructurado."""
    filename = pdf_path.name
    log.info(f"Procesando: {year}/{filename}")

    # Extraer texto
    text = extract_text_from_pdf(pdf_path)
    if not text or len(text.strip()) < 100:
        log.warning(f"Texto insuficiente para {filename} ({len(text)} chars)")
        # Intentar con pdftotext directamente
        text = extract_text_pdftotext(pdf_path)
        if not text or len(text.strip()) < 100:
            log.error(f"No se pudo extraer texto de {filename}")
            text = ""

    cleaned = clean_text(text)
    sections = split_sections(cleaned)

    # Detectar formato
    fmt = detect_format(cleaned, year)

    # Generar ID único
    report_id = f"{year}-{filename.replace('.pdf', '').replace('/', '-')}"

    # Extraer campos
    expediente = extract_expediente(cleaned)
    tipo = extract_tipo(cleaned, filename)
    tipo_suceso = extract_tipo_suceso(cleaned)
    fecha_suceso = extract_fecha_suceso(cleaned)
    hora_suceso = extract_hora_suceso(cleaned)
    estacion = extract_estacion(cleaned)
    provincia = extract_provincia(cleaned)
    severity = extract_severity(cleaned, filename)
    victims = extract_victims_count(cleaned)
    heridos = extract_heridos_count(cleaned)
    trenes = extract_trenes(cleaned)
    entidades = extract_entidades(cleaned)

    # Geocodificación (local siempre, Nominatim solo si habilitado)
    lat, lng = None, None
    if estacion:
        lat, lng = geocode_station(estacion, provincia)

    # Secciones de análisis
    resumen = extract_resumen(sections, cleaned)
    factores_humanos = extract_factores_humanos(sections, cleaned)
    infraestructura = extract_infraestructura(sections, cleaned)
    conclusiones = extract_conclusiones(sections, cleaned)
    recomendaciones = extract_recomendaciones(sections, cleaned)
    consecuencias = extract_consecuencias(cleaned)
    tags = extract_tags(cleaned, tipo, severity)

    # Extraer imágenes
    images = extract_images_from_pdf(pdf_path, report_id, year)

    # Construir objeto del informe
    report = {
        "id": report_id,
        "expediente": expediente,
        "tipo": tipo,
        "tipo_suceso": tipo_suceso,
        "fecha_suceso": fecha_suceso,
        "hora_suceso": hora_suceso,
        "year": year,
        "ubicacion": {
            "estacion": estacion,
            "provincia": provincia,
            "lat": lat,
            "lng": lng,
        },
        "trenes": trenes,
        "entidades": entidades,
        "gravedad": severity,
        "analisis": {
            "resumen": resumen,
            "factores_humanos": factores_humanos,
            "infraestructura": infraestructura,
        },
        "conclusiones": conclusiones,
        "recomendaciones": recomendaciones,
        "consecuencias": {
            "victimas_mortales": consecuencias["victimas_mortales"],
            "heridos": consecuencias["heridos"],
            "total_victimas": consecuencias["victimas_mortales"] + consecuencias["heridos"],
            "danos_materiales": consecuencias["danos_materiales"],
        },
        "tags": tags,
        "imagenes": images,
        "enlaces": {
            "pdf_original": f"pdfs/{year}/{filename}",
            "pagina_ciaf": f"https://www.transportes.gob.es/recursos_mfom/paginabasica/recursos/{pdf_path.name}",
        },
        "formato_normativo": {
            1: "Pre-RD 810/2007",
            2: "RD 810/2007",
            3: "RD 623/2014",
        }.get(fmt, "Desconocido"),
        "hash_pdf": md5_of_file(pdf_path),
        "fecha_parseo": datetime.now().isoformat(),
    }

    return report


# ===========================================================================
# Generación de salidas
# ===========================================================================

def generate_per_year_files(reports_by_year: dict[int, list[dict]]):
    """Genera archivos JSON por año."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for year, reports in sorted(reports_by_year.items()):
        output_path = REPORTS_DIR / f"{year}.json"
        # Ordenar por fecha
        reports_sorted = sorted(reports, key=lambda r: r.get("fecha_suceso", ""))

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(reports_sorted, f, ensure_ascii=False, indent=2)

        log.info(f"Generado {output_path.name}: {len(reports)} informes")


def generate_index(reports_by_year: dict[int, list[dict]]):
    """Genera el archivo index.json global."""
    all_reports = []
    for reports in reports_by_year.values():
        all_reports.extend(reports)

    total_victims = sum(
        r["consecuencias"]["victimas_mortales"] for r in all_reports
    )
    total_heridos = sum(
        r["consecuencias"]["heridos"] for r in all_reports
    )

    # Tipos de informe
    tipos = list(set(r["tipo"] for r in all_reports if r["tipo"]))

    # Entidades únicas
    entidades_set = set()
    for r in all_reports:
        entidades_set.update(r["entidades"])

    # Severidades
    severidades = list(set(r["gravedad"] for r in all_reports if r["gravedad"]))

    index = {
        "title": "CIAF - Centro de Información de Accidentes Ferroviarios",
        "description": "Visor de datos del Centro de Información de Accidentes Ferroviarios de España",
        "years_available": sorted(reports_by_year.keys()),
        "total_reports": len(all_reports),
        "total_victims": total_victims,
        "total_heridos": total_heridos,
        "report_types": sorted(tipos),
        "severities": sorted(severidades),
        "entities": sorted(entidades_set),
        "fecha_generacion": datetime.now().isoformat(),
        "estadisticas_por_anio": {
            str(y): {
                "total": len(reports),
                "victimas": sum(r["consecuencias"]["victimas_mortales"] for r in reports),
                "heridos": sum(r["consecuencias"]["heridos"] for r in reports),
            }
            for y, reports in sorted(reports_by_year.items())
        },
    }

    output_path = DATA_DIR / "index.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    log.info(f"Generado {output_path}: {len(all_reports)} informes totales")


def generate_relations(reports_by_year: dict[int, list[dict]]):
    """Genera relaciones entre informes (entidades compartidas, ubicaciones, etc.)."""
    all_reports = []
    for reports in reports_by_year.values():
        all_reports.extend(reports)

    # Relaciones por entidad
    entity_reports: dict[str, list[str]] = {}
    for r in all_reports:
        for ent in r["entidades"]:
            if ent not in entity_reports:
                entity_reports[ent] = []
            entity_reports[ent].append(r["id"])

    # Relaciones por estación
    station_reports: dict[str, list[str]] = {}
    for r in all_reports:
        est = r["ubicacion"]["estacion"]
        if est:
            station_reports[est] = station_reports.get(est, [])
            station_reports[est].append(r["id"])

    # Relaciones por tipo de suceso
    suceso_reports: dict[str, list[str]] = {}
    for r in all_reports:
        ts = r["tipo_suceso"]
        if ts:
            suceso_reports[ts] = suceso_reports.get(ts, [])
            suceso_reports[ts].append(r["id"])

    # Relaciones por provincia
    provincia_reports: dict[str, list[str]] = {}
    for r in all_reports:
        prov = r["ubicacion"]["provincia"]
        if prov:
            provincia_reports[prov] = provincia_reports.get(prov, [])
            provincia_reports[prov].append(r["id"])

    relations = {
        "por_entidad": entity_reports,
        "por_estacion": station_reports,
        "por_tipo_suceso": suceso_reports,
        "por_provincia": provincia_reports,
        "fecha_generacion": datetime.now().isoformat(),
    }

    output_path = DATA_DIR / "relations.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)

    log.info(f"Generado {output_path}")


# ===========================================================================
# Main
# ===========================================================================

def main():
    """Punto de entrada principal."""
    log.info("=" * 60)
    log.info("CIAF Parser – Inicio del procesamiento")
    log.info("=" * 60)

    # Crear directorios de salida
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    reports_by_year: dict[int, list[dict]] = {}
    errors: list[dict] = []
    total_pdfs = 0
    processed = 0

    for year in YEARS_WITH_REPORTS:
        year_dir = PDFS_DIR / str(year)
        if not year_dir.exists():
            log.warning(f"Directorio no encontrado: {year_dir}")
            continue

        pdfs = sorted(year_dir.glob("*.pdf"))
        if not pdfs:
            log.warning(f"No hay PDFs en {year_dir}")
            continue

        log.info(f"Año {year}: {len(pdfs)} PDFs encontrados")
        total_pdfs += len(pdfs)
        reports_by_year[year] = []

        for pdf_path in pdfs:
            try:
                report = parse_report(pdf_path, year)
                if report:
                    reports_by_year[year].append(report)
                    processed += 1
            except Exception as e:
                log.error(f"Error procesando {pdf_path.name}: {e}")
                errors.append({
                    "archivo": f"{year}/{pdf_path.name}",
                    "error": str(e),
                })

    # Generar salidas
    log.info("=" * 60)
    log.info("Generando archivos de salida...")
    log.info("=" * 60)

    generate_per_year_files(reports_by_year)
    generate_index(reports_by_year)
    generate_relations(reports_by_year)

    # Resumen
    total_reports = sum(len(r) for r in reports_by_year.values())
    total_victims = sum(
        r["consecuencias"]["victimas_mortales"]
        for reports in reports_by_year.values()
        for r in reports
    )

    log.info("=" * 60)
    log.info("RESUMEN DEL PROCESAMIENTO")
    log.info("=" * 60)
    log.info(f"PDFs encontrados:        {total_pdfs}")
    log.info(f"Informes procesados:     {processed}")
    log.info(f"Informes con errores:    {len(errors)}")
    log.info(f"Total víctimas mortales: {total_victims}")
    log.info(f"Años procesados:         {sorted(reports_by_year.keys())}")

    if errors:
        log.warning("Errores encontrados:")
        for err in errors:
            log.warning(f"  - {err['archivo']}: {err['error']}")

    # Guardar log de errores
    if errors:
        error_log_path = DATA_DIR / "parse_errors.json"
        with open(error_log_path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        log.info(f"Log de errores guardado en {error_log_path}")

    log.info("Procesamiento completado.")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
