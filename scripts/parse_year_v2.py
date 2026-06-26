#!/usr/bin/env python3
"""
parse_year_v2.py — Parser mejorado de informes CIAF por año
===========================================================

Extrae JSON de alta calidad de cada PDF, enfocado en:
- Título correcto del informe
- Resumen limpio (sin headers/footers)
- Conclusiones estructuradas (lista de puntos)
- Recomendaciones con implementador/destinatario/texto
- Áreas de mejora
- Enlace al PDF original

Uso: python3 parse_year_v2.py 2024 [--pdf-dir /root/workspace/CIAF] [--output-dir /root/workspace/CIAF-visor/data/reports]
"""

import sys
import os
import re
import json
import logging
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: pip install PyMuPDF")
    sys.exit(1)

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("parse_year_v2")

# ── Constants ────────────────────────────────────────────────────────────
PDF_DIR = Path("/root/workspace/CIAF")
OUTPUT_DIR = Path("/root/workspace/CIAF-visor/data/reports")
STATION_COORDS: dict = {}
try:
    _coords_path = Path("/root/workspace/CIAF-visor/data/station-coords.json")
    if _coords_path.exists():
        STATION_COORDS = json.loads(_coords_path.read_text())
except Exception:
    pass

# Province list
PROVINCIAS = [
    "Álava","Albacete","Alicante","Almería","Asturias","Ávila","Badajoz","Barcelona",
    "Burgos","Cáceres","Cádiz","Cantabria","Castellón","Ciudad Real","Córdoba",
    "Cuenca","Gerona","Granada","Guadalajara","Guipúzcoa","Huelva","Huesca",
    "Islas Baleares","Jaén","León","Lérida","Lugo","Madrid","Málaga","Murcia",
    "Navarra","Orense","Palencia","Las Palmas","Pontevedra","La Rioja","Salamanca",
    "Santa Cruz de Tenerife","Segovia","Sevilla","Soria","Tarragona","Teruel",
    "Toledo","Valencia","Valladolid","Vizcaya","Zamora","Zaragoza","Ceuta","Melilla"
]


# ── Text Extraction ──────────────────────────────────────────────────────
def extract_full_text(pdf_path: str) -> str:
    """Extrae texto limpio de un PDF usando PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


# ── Title Extraction ─────────────────────────────────────────────────────
def extract_title(text: str, filename: str, year: int) -> str:
    """Extrae el título del informe de la primera página."""
    # Pattern 1: 2014+ format — "INFORME FINAL DE LA CIAF (IF) XX/XXXX"
    m = re.search(r'INFORME\s+FINAL\s+DE\s+LA\s+CIAF\s*\(IF\)\s*(\d+/\d{4})', text, re.IGNORECASE)
    if m:
        # Next line is usually the subtitle
        after = text[m.end():m.end()+500]
        subtitle = ""
        for line in after.split("\n"):
            line = line.strip()
            if line and len(line) > 10 and not line.startswith("(") and "cuya finalidad" not in line.lower():
                subtitle = line
                break
        if subtitle:
            return f"IF {m.group(1)} — {subtitle}"
        return f"Informe {m.group(1)}"

    # Pattern 2: 2009-2013 format — "INFORME FINAL SOBRE EL INCIDENTE/ACCIDENTE"
    m = re.search(r'INFORME\s+(?:DEFINITIVO\s+)?(?:FINAL\s+)?SOBRE\s+(?:LA\s+)?(?:EL\s+)?(?:INVESTIGACIÓN\s+DEL\s+)?(?:ACCIDENTE|INCIDENTE)\s*(?:FERROVIARIO)?\s*(?:N[ºo°]\s*)?(\d+/\d{4})', text, re.IGNORECASE)
    if m:
        # Look for "EN LA ESTACIÓN DE..." after
        station_match = re.search(r'EN\s+LA\s+ESTACIÓN\s+DE\s+([^\n]+)', text, re.IGNORECASE)
        if station_match:
            return f"{m.group(1)} — Estación de {station_match.group(1).strip()}"
        # Look for "OCURRIDO EL DÍA..."
        return f"Informe {m.group(1)}"

    # Pattern 3: 2007-2008 format — "Investigación del accidente nº XXXX/XXXX"
    m = re.search(r'[Ii]nvestigación\s+del\s+(?:accidente|incidente)\s*(?:n[ºo°]\s*)?(\d+/\d{4})', text)
    if m:
        return f"Informe {m.group(1)}"

    # Fallback: use filename
    return Path(filename).stem


# ── Page-Based Section Extraction ─────────────────────────────────────
def extract_pages(pdf_path: str) -> list[str]:
    """Extrae texto de cada página por separado."""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


def find_section_pages(pages: list[str]) -> dict[int, int]:
    """Encuentra en qué página empieza cada sección (saltando TOC)."""
    section_pages = {}
    for i, text in enumerate(pages):
        if i < 2:  # Skip cover + warning/advertencia
            continue
        # Skip TOC pages (lines with lots of dots)
        if re.search(r'\.{10,}', text):
            continue
        for m in re.finditer(r'(?:^|\n)\s*(\d+)\.\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,40})', text):
            num = int(m.group(1))
            if num not in section_pages:
                section_pages[num] = i
    return section_pages


def get_pages_text(pages: list[str], start_page: int, end_page: int) -> str:
    """Concatena texto de páginas, limpiando headers/footers."""
    text = ""
    for i in range(start_page, min(end_page, len(pages))):
        page_text = pages[i]
        # Remove common headers/footers
        page_text = re.sub(r'Comisión de Investigación de\s*Accidentes Ferroviarios', '', page_text)
        page_text = re.sub(r'Informe Final de la CIAF\s+\d+/\d{4}', '', page_text)
        page_text = re.sub(r'Informe (?:Definitivo|Final)\s*(?:de la\s*)?CIAF', '', page_text, flags=re.IGNORECASE)
        page_text = re.sub(r'INFRAESTRUCTURAS\s+A\s+DE\s+FOMENTO\s+INVESTIGACIÓN\s+DE\s+ACCIDENTES', '', page_text, flags=re.IGNORECASE)
        page_text = re.sub(r'SECRETARÍA\s+GENERAL\s+DE\s+INFRAESTRUCTURAS', '', page_text, flags=re.IGNORECASE)
        page_text = re.sub(r'MINISTERIO\s+DE\s+FOMENTO', '', page_text, flags=re.IGNORECASE)
        page_text = re.sub(r'COMISIÓN\s+DE\s+INVESTIGACIÓN\s+DE\s+ACCIDENTES\s+FERROVIARIOS', '', page_text, flags=re.IGNORECASE)
        page_text = re.sub(r'SECRETARIA\s+DE\s+ESTADO\s+DE\s+INFRAESTRUCTURAS', '', page_text, flags=re.IGNORECASE)
        page_text = re.sub(r'ID-\d{6}-\d{6}-CIAF', '', page_text)
        page_text = re.sub(r'IF-\d{6}-\d{6}-CIAF', '', page_text)
        # Remove page numbers
        page_text = re.sub(r'^\s*\d{1,2}\s*$', '', page_text, flags=re.MULTILINE)
        page_text = re.sub(r'Pág\.\s*\d+\s+de\s+\d+', '', page_text)
        # Remove lines that are just dots (TOC remnants)
        page_text = re.sub(r'^.*\.{10,}.*$', '', page_text, flags=re.MULTILINE)
        text += page_text + "\n"
    return text.strip()


def extract_summary_pages(pages: list[str], section_pages: dict) -> str:
    """Extrae resumen de las páginas de la sección 1."""
    if 1 not in section_pages:
        return ""
    start = section_pages[1]
    end = section_pages.get(2, start + 3)
    text = get_pages_text(pages, start, end)
    # Remove section header
    text = re.sub(r'^\s*1\.\s+RESUMEN\s*\n?', '', text)
    # Clean up
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # Remove lines that are just numbers or very short
    lines = [l for l in lines if len(l) > 5 and not re.match(r'^\d+$', l)]
    return '\n'.join(lines)[:800]


def extract_conclusions_pages(pages: list[str], section_pages: dict) -> list[str]:
    """Extrae conclusiones de las páginas de la sección 5."""
    if 5 not in section_pages:
        # Try section 4 (older format has "ANÁLISIS Y CONCLUSIONES")
        if 4 not in section_pages:
            return []
        start = section_pages[4]
        end = section_pages.get(5, start + 5)
    else:
        start = section_pages[5]
        end = section_pages.get(6, start + 5)

    text = get_pages_text(pages, start, end)
    # Remove section header
    text = re.sub(r'^\s*5\.\s+CONCLUSIONES\s*\n?', '', text)
    text = re.sub(r'^\s*4\.\s+ANÁLISIS\s+Y\s+CONCLUSIONES\s*\n?', '', text)

    conclusions = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        # Skip headers/footers
        if any(skip in line.upper() for skip in ['CIAF', 'MINISTERIO', 'PÁG.', 'INFRAESTRUCTURAS']):
            continue
        # Skip sub-section headers
        if re.match(r'^\d+\.\d+\s', line):
            continue
        # Skip figure references
        if re.match(r'^Figura\s+\d+', line, re.IGNORECASE):
            continue
        # Bullet points
        if line.startswith('•') or line.startswith('-') or line.startswith('–'):
            conclusions.append(line.lstrip('•-– ').strip())
        # Numbered items
        elif re.match(r'^\d+[\.\)]\s', line):
            conclusions.append(re.sub(r'^\d+[\.\)]\s*', '', line).strip())
        # Regular text
        elif len(line) > 20:
            conclusions.append(line)

    # Deduplicate and limit
    seen = set()
    result = []
    for c in conclusions:
        c = c.strip()
        if c and c not in seen and len(c) > 10:
            seen.add(c)
            result.append(c)
    return result[:20]


def extract_recommendations_pages(pages: list[str], section_pages: dict) -> list[dict]:
    """Extrae recomendaciones de las páginas de la sección 6."""
    if 6 not in section_pages:
        # Try section 5 (older format)
        if 5 not in section_pages:
            return []
        start = section_pages[5]
        end = len(pages)
    else:
        start = section_pages[6]
        # Stop before English section (look for "SAFETY RECOMMENDATIONS" or "English")
        end = start + 3  # Max 3 pages for recommendations
        for i in range(start + 1, min(start + 5, len(pages))):
            if re.search(r'SAFETY\s+RECOMMENDATIONS|English\s+summary', pages[i], re.IGNORECASE):
                end = i
                break

    text = get_pages_text(pages, start, end)
    # Remove section header
    text = re.sub(r'^\s*6\.\s+RECOMENDACIONES\s+FINALES?\s*\n?', '', text)
    text = re.sub(r'^\s*5\.\s+RECOMENDACIONES\s*\n?', '', text)

    recs = []
    # Pattern: "Número\nRecomendación\n..." or "R.X/Y-Z: texto"
    # Table format: "64/2024-1\nRealizar estudios..." or "11/09-1\nCumplimiento..."
    rec_pattern = r'(\d+/\d{2,4}-\d+)\s*\n\s*(.+?)(?=\d+/\d{2,4}-\d+|\Z)'
    matches = re.findall(rec_pattern, text, re.DOTALL)

    if matches:
        for num_str, body in matches:
            body = re.sub(r'\s+', ' ', body).strip()
            # Remove trailing artifacts
            body = re.sub(r'\s*(?:AESF|ADIF|EMPRESAS?\s+FERROVIARIAS?|Madrid,?\s+a\s+\d+).*$', '', body, flags=re.IGNORECASE)
            body = re.sub(r'\s*(?:DESTINATARIO|IMPLEMENTADOR|FINAL|NÚMERO).*$', '', body, flags=re.IGNORECASE)
            if len(body) > 10:
                recs.append({
                    "numero": num_str.strip(),
                    "texto": body[:500],
                    "implementador": ""
                })
    else:
        # Fallback: extract numbered items
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            if any(skip in line.upper() for skip in ['CIAF', 'MINISTERIO', 'PÁG.', 'DESTINATARIO', 'IMPLEMENTADOR', 'SAFETY', 'ENGLISH']):
                continue
            m = re.match(r'^(\d+/\d{4}-\d+)\s+(.+)', line)
            if m:
                recs.append({
                    "numero": m.group(1),
                    "texto": m.group(2).strip()[:500],
                    "implementador": ""
                })

    return recs[:15]


# ── Legacy Fallback: Section Regex ─────────────────────────────────────
def extract_sections_old(text: str) -> dict:
    """Fallback: extrae secciones por regex (menos preciso)."""
    sections = {}
    patterns = [
        (r'(?:^|\n)\s*(\d+)\.\s*\n?\s*(RESUMEN)', 'resumen'),
        (r'(?:^|\n)\s*(\d+)\.\s*\n?\s*(HECHOS\s+INMEDIATOS)', 'hechos'),
        (r'(?:^|\n)\s*(\d+)\.\s*\n?\s*(CONCLUSIONES)', 'conclusiones'),
        (r'(?:^|\n)\s*(\d+)\.\s*\n?\s*(RECOMENDACIONES)', 'recomendaciones'),
        (r'(?:^|\n)\s*(\d+)\.\s*\n?\s*(DESCRIPCIÓN\s+DEL\s+SUCESO)', 'descripcion'),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            sections[key] = int(m.group(1))
    return sections


def get_section_text_old(text: str, section_num: int, next_section_num: int = None) -> str:
    """Fallback: extrae texto de una sección por número."""
    pattern = rf'(?:^|\n)\s*{section_num}\.\s*\n?\s*[A-ZÁÉÍÓÚÑ]'
    m = re.search(pattern, text)
    if not m:
        return ""
    start = m.start()
    if next_section_num:
        next_pattern = rf'(?:^|\n)\s*{next_section_num}\.\s*\n?\s*[A-ZÁÉÍÓÚÑ]'
        next_m = re.search(next_pattern, text[start + 10:])
        if next_m:
            return text[start:start + 10 + next_m.start()].strip()
    return text[start:start + 5000].strip()


def extract_summary_old(text: str) -> str:
    """Fallback: extrae resumen de texto completo."""
    # Find "1. RESUMEN" and take next 500 chars
    m = re.search(r'1\.\s+RESUMEN\s*\n', text)
    if m:
        after = text[m.end():m.end()+1000]
        lines = [l.strip() for l in after.split('\n') if l.strip()]
        lines = [l for l in lines if len(l) > 5 and not re.match(r'^\d+$', l)]
        return '\n'.join(lines)[:500]
    return ""


# ── Clean Text ──────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    """Limpia texto extraído de PDF."""
    # Remove page numbers
    text = re.sub(r'Pág\.\s*\d+\s+de\s+\d+', '', text)
    # Remove CIAF header/footer patterns
    text = re.sub(r'nº\s*\d+/\d{4}\s*ocurrido\s+el\s+[\d.]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'ID-\d{6}-\d{6}-CIAF', '', text)
    text = re.sub(r'IF-\d{6}-\d{6}-CIAF', '', text)
    text = re.sub(r'SECRETARÍA\s+GENERAL\s+DE\s+INFRAESTRUCTURAS', '', text, flags=re.IGNORECASE)
    text = re.sub(r'MINISTERIO\s+DE\s+FOMENTO', '', text, flags=re.IGNORECASE)
    text = re.sub(r'COMISIÓN\s+DE\s+INVESTIGACIÓN\s+DE\s+ACCIDENTES\s+FERROVIARIOS', '', text, flags=re.IGNORECASE)
    text = re.sub(r'INFRAESTRUCTURAS\s+A\s+DE\s+FOMENTO\s+INVESTIGACIÓN\s+DE\s+ACCIDENTES', '', text, flags=re.IGNORECASE)
    text = re.sub(r'SECRETARIA\s+DE\s+ESTADO\s+DE\s+INFRAESTRUCTURAS', '', text, flags=re.IGNORECASE)
    # Remove multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()


def clean_section_header(text: str) -> str:
    """Quita el header de sección del texto."""
    text = re.sub(r'^\d+\.\s*\n?\s*[A-ZÁÉÍÓÚÑ\s]+\n', '', text)
    return text.strip()


# ── Conclusions Extraction ─────────────────────────────────────────────
def extract_conclusions(text: str, sections: dict) -> list[str]:
    """Extrae conclusiones como lista estructurada."""
    conclusions = []

    # Find conclusiones section
    if 'conclusiones' in sections:
        num = sections['conclusiones']
        # Find next section number
        next_num = None
        for k, v in sections.items():
            if v > num and (next_num is None or v < next_num):
                next_num = v

        section_text = get_section_text_old(text, num, next_num)
        section_text = clean_section_header(section_text)
        section_text = clean_text(section_text)

        # Extract bullet points
        for line in section_text.split('\n'):
            line = line.strip()
            # Skip empty, headers, footers
            if not line or len(line) < 10:
                continue
            if any(skip in line.upper() for skip in [
                'PÁG.', 'CIAF', 'MINISTERIO', 'INFRAESTRUCTURAS',
                'COMISIÓN', 'INVESTIGACIÓN DE ACCIDENTES'
            ]):
                continue
            # Bullet points
            if line.startswith('-') or line.startswith('•') or line.startswith('–'):
                conclusions.append(line.lstrip('-•– ').strip())
            # Numbered items
            elif re.match(r'^\d+[\.\)]\s', line):
                conclusions.append(re.sub(r'^\d+[\.\)]\s*', '', line).strip())
            # Regular text that looks like a conclusion
            elif len(line) > 20 and not line.startswith('4.') and not line.startswith('5.'):
                conclusions.append(line)

    # Also check "analisis_conclusiones" section for older format
    elif 'analisis_conclusiones' in sections:
        num = sections['analisis_conclusiones']
        next_num = None
        for k, v in sections.items():
            if v > num and (next_num is None or v < next_num):
                next_num = v

        section_text = get_section_text_old(text, num, next_num)
        # Look for "CONCLUSIONES" sub-section within
        m = re.search(r'(?:4\.2|CONCLUSIONES)\s*\n', section_text, re.IGNORECASE)
        if m:
            sub_text = section_text[m.end():m.end()+3000]
            sub_text = clean_text(sub_text)
            for line in sub_text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    conclusions.append(line.lstrip('-•– ').strip())
                elif len(line) > 20 and not re.match(r'^\d+\.\d', line):
                    conclusions.append(line)

    # Limit and deduplicate
    seen = set()
    result = []
    for c in conclusions:
        c = c.strip()
        if c and c not in seen and len(c) > 10:
            seen.add(c)
            result.append(c)
    return result[:20]  # Max 20 conclusions


# ── Recommendations Extraction ──────────────────────────────────────────
def extract_recommendations(text: str, sections: dict) -> list[dict]:
    """Extrae recomendaciones estructuradas."""
    recs = []

    if 'recomendaciones' not in sections:
        return recs

    num = sections['recomendaciones']
    # Find next section (or end of document)
    next_num = None
    for k, v in sections.items():
        if v > num and (next_num is None or v < next_num):
            next_num = v

    section_text = get_section_text_old(text, num, next_num)
    section_text = clean_section_header(section_text)
    section_text = clean_text(section_text)

    # Pattern: "Recomendación X.Y.Z: texto" or "R.X.Y.Z: texto"
    rec_pattern = r'(?:Recomendación|R\.?)\s*(\d+[\.\d]*)\s*[:\.]?\s*(.+?)(?=(?:Recomendación|R\.?)\s*\d|\Z)'
    matches = re.findall(rec_pattern, section_text, re.DOTALL | re.IGNORECASE)

    if matches:
        for num_str, body in matches:
            body = clean_text(body)
            # Extract implementador if present
            impl = ""
            impl_match = re.search(r'(?:Implementador|Responsable|Destinatario)[:\s]+([^\n]+)', body, re.IGNORECASE)
            if impl_match:
                impl = impl_match.group(1).strip()
                body = body[:impl_match.start()].strip()

            recs.append({
                "numero": num_str.strip(),
                "texto": body.strip()[:500],
                "implementador": impl
            })
    else:
        # Fallback: extract numbered items
        for line in section_text.split('\n'):
            line = line.strip()
            m = re.match(r'^(\d+[\.\d]*)\s*[:\.]?\s+(.+)', line)
            if m and len(m.group(2)) > 15:
                recs.append({
                    "numero": m.group(1),
                    "texto": m.group(2).strip()[:500],
                    "implementador": ""
                })

    return recs[:15]  # Max 15 recommendations


# ── Summary Extraction ─────────────────────────────────────────────────
def extract_summary(text: str, sections: dict) -> str:
    """Extrae resumen limpio de la sección 1."""
    if 'resumen' not in sections:
        # Fallback: first 500 chars after title
        return clean_text(text[:800])[:500]

    num = sections['resumen']
    next_num = None
    for k, v in sections.items():
        if v > num and (next_num is None or v < next_num):
            next_num = v

    section_text = get_section_text_old(text, num, next_num)
    section_text = clean_section_header(section_text)
    section_text = clean_text(section_text)

    # Take first 500 chars
    return section_text[:500]


# ── Description Extraction ─────────────────────────────────────────────
def extract_description(text: str, sections: dict) -> str:
    """Extrae descripción del suceso."""
    # Try "descripcion" first (2014+), then "hechos" (2009-2013)
    key = 'descripcion' if 'descripcion' in sections else 'hechos'
    if key not in sections:
        return ""

    num = sections[key]
    next_num = None
    for k, v in sections.items():
        if v > num and (next_num is None or v < next_num):
            next_num = v

    section_text = get_section_text_old(text, num, next_num)
    section_text = clean_section_header(section_text)
    section_text = clean_text(section_text)

    return section_text[:1000]


# ── Metadata Extraction ────────────────────────────────────────────────
def extract_metadata(text: str, filename: str, year: int) -> dict:
    """Extrae metadatos del informe."""
    meta = {}

    # Expediente
    m = re.search(r'(?:nº|número|expediente)\s*(\d+/\d{4})', text, re.IGNORECASE)
    if m:
        meta['expediente'] = m.group(1)
    else:
        m = re.search(r'(\d{2,4}/\d{4})', text)
        if m:
            meta['expediente'] = m.group(1)

    # Fecha del suceso
    m = re.search(r'(?:ocurrido\s+el|fecha\s+del\s+suceso)[\s:]*(\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{2,4})', text, re.IGNORECASE)
    if m:
        fecha = m.group(1).replace('.', '-').replace('/', '-')
        parts = fecha.split('-')
        if len(parts) == 3:
            if len(parts[2]) == 2:
                parts[2] = f"20{parts[2]}" if int(parts[2]) < 50 else f"19{parts[2]}"
            meta['fecha_suceso'] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    else:
        # Try "día XX de MONTH de YYYY"
        m = re.search(r'(?:día|dia)\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', text, re.IGNORECASE)
        if m:
            month_map = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }
            month = month_map.get(m.group(2).lower(), '01')
            meta['fecha_suceso'] = f"{m.group(3)}-{month}-{m.group(1).zfill(2)}"

    # Tipo de suceso
    if re.search(r'accidente\s+ferroviario', text, re.IGNORECASE):
        meta['tipo'] = 'accidente'
    elif re.search(r'incidente\s+(?:ferroviario|operacional)', text, re.IGNORECASE):
        meta['tipo'] = 'incidente'
    elif re.search(r'avería', text, re.IGNORECASE):
        meta['tipo'] = 'avería'
    else:
        meta['tipo'] = 'accidente'

    # Gravedad
    if re.search(r'(?:sin\s+víctimas\s+mortales|no\s+hubo\s+víctimas)', text, re.IGNORECASE):
        meta['gravedad'] = 'leve'
    elif re.search(r'víctima[s]?\s+mortal', text, re.IGNORECASE):
        victims_match = re.search(r'(\d+)\s+víctima[s]?\s+mortal', text, re.IGNORECASE)
        if victims_match:
            n = int(victims_match.group(1))
            meta['gravedad'] = 'fatal' if n >= 1 else 'leve'
        else:
            meta['gravedad'] = 'fatal'
    elif re.search(r'herido[s]?\s+grave', text, re.IGNORECASE):
        meta['gravedad'] = 'grave'
    else:
        meta['gravedad'] = 'leve'

    # Estación
    station = extract_station(text)
    meta['estacion'] = station

    # Provincia
    province = extract_province(text, station)
    meta['provincia'] = province

    # Entidades
    entidades = extract_entities(text)

    # Víctimas
    victims = 0
    m = re.search(r'(\d+)\s+víctima[s]?\s+mortal', text, re.IGNORECASE)
    if m:
        victims = int(m.group(1))
    meta['victimas_mortales'] = victims

    heridos = 0
    m = re.search(r'(\d+)\s+herido[s]?', text, re.IGNORECASE)
    if m:
        heridos = int(m.group(1))
    meta['heridos'] = heridos

    # Daños materiales
    meta['danos_materiales'] = bool(re.search(r'daño[s]?\s+material', text, re.IGNORECASE))

    return meta


def extract_station(text: str) -> str:
    """Extrae nombre de estación."""
    # Pattern: "EN LA ESTACIÓN DE X"
    m = re.search(r'EN\s+LA\s+ESTACIÓN\s+DE\s+([^\n,]+)', text, re.IGNORECASE)
    if m:
        return clean_station_name(m.group(1))

    # Pattern: "estación de X"
    m = re.search(r'estación\s+de\s+([^\n,]+)', text, re.IGNORECASE)
    if m:
        return clean_station_name(m.group(1))

    # Pattern: "en la estación de X"
    m = re.search(r'en\s+la\s+estación\s+de\s+([^\n,]+)', text, re.IGNORECASE)
    if m:
        return clean_station_name(m.group(1))

    # Pattern: "estación de X el día"
    m = re.search(r'estación\s+de\s+(\w[\w\s]{2,30})\s+el\s+día', text, re.IGNORECASE)
    if m:
        return clean_station_name(m.group(1))

    return ""


def clean_station_name(name: str) -> str:
    """Limpia nombre de estación."""
    name = name.strip()
    # Remove trailing junk
    name = re.sub(r'\s+(?:el\s+día|ocurrido|cuando|donde|procedente|con\s+destino).*', '', name, flags=re.IGNORECASE)
    # Limit length
    if len(name) > 50:
        name = name[:50].rsplit(' ', 1)[0]
    return name.strip()


def extract_province(text: str, station: str) -> str:
    """Extrae provincia, priorizando la del nombre de estación."""
    # First: check if station name contains a province
    if station:
        for prov in PROVINCIAS:
            if prov.upper() in station.upper():
                return prov

    # Direct match from province list (skip first 500 chars to avoid header matches)
    search_text = text[500:] if len(text) > 500 else text
    for prov in PROVINCIAS:
        if re.search(rf'\b{re.escape(prov)}\b', search_text, re.IGNORECASE):
            return prov
    return ""


def extract_entities(text: str) -> list[str]:
    """Extrae entidades ferroviarias."""
    entities = set()

    known = [
        "Renfe Viajeros", "Renfe Mercancías", "Renfe Operadora",
        "ADIF AV", "ADIF", "FEVE", "TRAM",
        "Acciona Rail Services", "Activa Rail", "CAPTRAIN",
        "COMSA Rail Transport", "Continental Rail", "Logitren",
        "Low Cost Rail", "Tracción Rail", "Transfesa Rail", "Transitia Rail",
    ]

    for ent in known:
        if re.search(rf'\b{re.escape(ent)}\b', text, re.IGNORECASE):
            entities.add(ent)

    # Generic "renfe" catch
    if not entities and re.search(r'\brenfe\b', text, re.IGNORECASE):
        entities.add("RENFE")

    # Generic "adif" catch
    if not entities and re.search(r'\badif\b', text, re.IGNORECASE):
        entities.add("ADIF")

    return sorted(entities)


# ── Similar Reports Linking ────────────────────────────────────────────
def find_similar_reports(report: dict, all_reports: list[dict]) -> list[str]:
    """Encuentra informes similares por estación, tipo o entidad."""
    similar = []
    for other in all_reports:
        if other['id'] == report['id']:
            continue
        score = 0
        # Same station
        if report.get('ubicacion', {}).get('estacion') and \
           report['ubicacion']['estacion'] == other.get('ubicacion', {}).get('estacion'):
            score += 3
        # Same province
        if report.get('ubicacion', {}).get('provincia') and \
           report['ubicacion']['provincia'] == other.get('ubicacion', {}).get('provincia'):
            score += 1
        # Same type
        if report.get('tipo') == other.get('tipo'):
            score += 1
        # Same entities (at least one in common)
        if set(report.get('entidades', [])) & set(other.get('entidades', [])):
            score += 1
        # Close in time (same year)
        if report.get('year') == other.get('year'):
            score += 1

        if score >= 3:
            similar.append(other['id'])

    return similar[:5]  # Max 5 similar


# ── Geocoding ──────────────────────────────────────────────────────────
def geocode_station(station: str, province: str) -> tuple:
    """Geocodifica desde station-coords.json."""
    if not station:
        return None, None

    import unicodedata
    def normalize(s):
        s = s.upper().strip()
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        return re.sub(r'\s+', ' ', s).strip()

    norm_station = normalize(station)

    # Exact match
    if station in STATION_COORDS:
        c = STATION_COORDS[station]
        return c['lat'], c['lng']

    # Normalized match
    for name, coords in STATION_COORDS.items():
        if normalize(name) == norm_station:
            return coords['lat'], coords['lng']

    # Partial match
    for name, coords in STATION_COORDS.items():
        norm_name = normalize(name)
        if norm_station in norm_name or norm_name in norm_station:
            return coords['lat'], coords['lng']

    # Key words match (first 2 significant words)
    words = [w for w in norm_station.split() if len(w) > 2]
    if len(words) >= 2:
        key = ' '.join(words[:2])
        for name, coords in STATION_COORDS.items():
            norm_name = normalize(name)
            if key in norm_name:
                return coords['lat'], coords['lng']

    return None, None


# ── Process Single PDF ─────────────────────────────────────────────────
def process_pdf(pdf_path: str, year: int) -> Optional[dict]:
    """Procesa un solo PDF y devuelve un dict estructurado."""
    filename = os.path.basename(pdf_path)

    try:
        pages = extract_pages(pdf_path)
        text = "\n".join(pages)
    except Exception as e:
        log.error(f"Error extrayendo texto de {filename}: {e}")
        return None

    if not text or len(text) < 100:
        log.warning(f"Texto muy corto en {filename}: {len(text)} chars")
        return None

    # Page-based section extraction (primary method)
    section_pages = find_section_pages(pages)

    # Build report
    title = extract_title(text, filename, year)
    meta = extract_metadata(text, filename, year)

    # Geocoding
    lat, lng = geocode_station(meta.get('estacion', ''), meta.get('provincia', ''))

    # Extract key fields using page-based approach
    resumen = extract_summary_pages(pages, section_pages)
    conclusiones = extract_conclusions_pages(pages, section_pages)
    recomendaciones = extract_recommendations_pages(pages, section_pages)

    # Fallback: if page-based failed, try old regex method
    if not resumen:
        resumen = extract_summary_old(text)
    if not conclusiones:
        sections_old = extract_sections_old(text)
        # Use old method as fallback
        if 'conclusiones' in sections_old:
            num = sections_old['conclusiones']
            next_num = sections_old.get('recomendaciones')
            section_text = get_section_text_old(text, num, next_num)
            conclusiones = [l.strip() for l in section_text.split('\n') if l.strip() and len(l.strip()) > 15][:10]

    # Build report object
    report = {
        "id": f"{year}-{meta.get('expediente', filename.replace('.pdf', ''))}",
        "year": year,
        "expediente": meta.get('expediente', ''),
        "titulo": title,
        "tipo": meta.get('tipo', 'accidente'),
        "tipo_suceso": meta.get('tipo', 'accidente'),
        "gravedad": meta.get('gravedad', 'leve'),
        "fecha_suceso": meta.get('fecha_suceso', ''),
        "ubicacion": {
            "estacion": meta.get('estacion', ''),
            "provincia": meta.get('provincia', ''),
            "lat": lat,
            "lng": lng,
        },
        "entidades": extract_entities(text),
        "consecuencias": {
            "victimas_mortales": meta.get('victimas_mortales', 0),
            "heridos": meta.get('heridos', 0),
            "danos_materiales": meta.get('danos_materiales', False),
        },
        "analisis": {
            "resumen": resumen,
            "descripcion": extract_description(text, extract_sections_old(text)),
        },
        "conclusiones": conclusiones,
        "recomendaciones": recomendaciones,
        "tags": build_tags(meta, text),
        "enlaces": {
            "ciaf_web": f"https://www.transportes.gob.es/organos-colegiados/ciaf/informes-finales-de-sucesos-investigados",
            "pdf_local": f"pdfs/{year}/{filename}",
        },
        "similares": [],  # Will be filled after all reports processed
    }

    return report


def build_tags(meta: dict, text: str) -> list[str]:
    """Construye tags descriptivos."""
    tags = [meta.get('tipo', 'accidente')]

    # Cause tags
    cause_patterns = {
        'paso a nivel': r'paso\s+a\s+nivel',
        'arrollamiento': r'arrollamiento',
        'colisión': r'colisión',
        'descarrilamiento': r'descarrilamiento',
        'factor humano': r'factor\s+humano',
        'señalización': r'señalización',
        'mantenimiento': r'mantenimiento',
        'infraestructura': r'infraestructura',
        'velocidad': r'velocidad',
        'alcoholemia': r'alcohol',
        'cruzamiento': r'cruce|cruzamiento',
        'vandalismo': r'vandalismo',
        'avería mecánica': r'avería\s+mecánica',
        'incendio': r'incendio',
    }

    for tag, pattern in cause_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            tags.append(tag)

    # Severity tag
    tags.append(meta.get('gravedad', 'leve'))

    return tags


# ── Main ──────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Uso: python3 parse_year_v2.py <año>")
        sys.exit(1)

    year = int(sys.argv[1])
    pdf_dir = PDF_DIR / str(year)

    if not pdf_dir.exists():
        log.error(f"Directorio no encontrado: {pdf_dir}")
        sys.exit(1)

    pdfs = sorted([f for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf'])
    log.info(f"Año {year}: {len(pdfs)} PDFs encontrados")

    reports = []
    errors = 0

    for i, pdf_path in enumerate(pdfs):
        log.info(f"  [{i+1}/{len(pdfs)}] {pdf_path.name}")
        report = process_pdf(str(pdf_path), year)
        if report:
            reports.append(report)
        else:
            errors += 1

    # Link similar reports
    log.info("Vinculando informes similares...")
    for report in reports:
        report['similares'] = find_similar_reports(report, reports)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{year}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Año {year}: {len(reports)} informes procesados, {errors} errores")
    log.info(f"   Guardado en: {output_file}")

    # Stats
    with_title = sum(1 for r in reports if r.get('titulo'))
    with_conclusions = sum(1 for r in reports if r.get('conclusiones'))
    with_recs = sum(1 for r in reports if r.get('recomendaciones'))
    with_coords = sum(1 for r in reports if r.get('ubicacion', {}).get('lat'))
    log.info(f"   Con título: {with_title}/{len(reports)}")
    log.info(f"   Con conclusiones: {with_conclusions}/{len(reports)}")
    log.info(f"   Con recomendaciones: {with_recs}/{len(reports)}")
    log.info(f"   Con coordenadas: {with_coords}/{len(reports)}")


if __name__ == "__main__":
    main()
