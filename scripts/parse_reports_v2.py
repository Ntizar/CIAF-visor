#!/usr/bin/env python3
"""
Parser mejorado de informes CIAF v2.
Extrae: título, fecha, estación, provincia, conclusiones, recomendaciones
Maneja 4 formatos históricos distintos (2007-2024).
"""
import fitz  # PyMuPDF
import re
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
REPORTS_DIR = BASE / 'data' / 'reports'
PDFS_DIR = BASE / 'pdfs'


def extract_full_text(pdf_path):
    """Extract all text from a PDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return '\n'.join(pages)


def extract_first_page(pdf_path):
    """Extract text from first page only."""
    doc = fitz.open(str(pdf_path))
    text = doc[0].get_text() if len(doc) > 0 else ''
    doc.close()
    return text


def extract_last_pages(pdf_path, n=3):
    """Extract text from last N pages."""
    doc = fitz.open(str(pdf_path))
    pages = []
    start = max(0, len(doc) - n)
    for i in range(start, len(doc)):
        pages.append(doc[i].get_text())
    doc.close()
    return '\n'.join(pages)


def parse_title_from_first_page(text):
    """Extract descriptive title from first page. Returns (title, date_str)."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    title = None
    date_str = None
    
    # Pattern 1 (2020+): "INFORME FINAL DE LA CIAF (IFC) 19/2020\nIncidente ferroviario ocurrido en la estación de Xeraco (Valencia),\nel 4 de marzo de 2020"
    for i, line in enumerate(lines):
        m = re.match(r'INFORME\s+FINAL.*?\(I?F?C?\)\s*(\d+/\d{4})', line, re.I)
        if m:
            # Next lines should have the description
            desc_lines = []
            for j in range(i+1, min(i+5, len(lines))):
                l = lines[j]
                if any(skip in l.upper() for skip in ['ENGLISH', 'CASO', '"EN NINGÚN', 'SECRETAR', 'MINISTERIO']):
                    break
                desc_lines.append(l)
            if desc_lines:
                title = ' '.join(desc_lines)
            break
    
    # Pattern 2 (2014-2019): "INFORME FINAL DE LA CIAF (IFC)\nSOBRE EL ACCIDENTE FERROVIARIO Nº 0017/2015\nOCURRIDO EL DÍA 09.02.2015 EN LA\nESTACIÓN DE A SUSANA (A CORUÑA)."
    if not title:
        for i, line in enumerate(lines):
            m = re.match(r'INFORME.*?\(IFC?\)', line, re.I)
            if m:
                desc_lines = []
                for j in range(i+1, min(i+6, len(lines))):
                    l = lines[j]
                    if any(skip in l.upper() for skip in ['ENGLISH', '"EN NINGÚN', 'SECRETAR', 'MINISTERIO', 'LA INVESTIGACIÓN']):
                        break
                    desc_lines.append(l)
                if desc_lines:
                    title = ' '.join(desc_lines)
                break
    
    # Pattern 3 (2007-2013): "Investigación del accidente\nnº 0009/2008 ocurrido el 16.04.2008"
    if not title:
        for i, line in enumerate(lines):
            m = re.match(r'Investigación del (?:accidente|incidente)\s*$', line, re.I)
            if m and i+1 < len(lines):
                next_line = lines[i+1]
                m2 = re.match(r'n[ºo]\s*(\d+/\d{4})\s*ocurrido\s+el\s+(.+)', next_line, re.I)
                if m2:
                    # Try to get more context from subsequent lines
                    desc_parts = []
                    for j in range(i+2, min(i+5, len(lines))):
                        l = lines[j]
                        if any(skip in l.upper() for skip in ['SECRETAR', 'MINISTERIO', 'COMISIÓN']):
                            break
                        desc_parts.append(l)
                    if desc_parts:
                        title = f"Investigación del accidente {m2.group(1)} — {' '.join(desc_parts)}"
                    else:
                        title = f"Investigación del accidente {m2.group(1)}"
                    raw_date = m2.group(2).strip()
                    # Normalize DD.MM.YYYY to YYYY-MM-DD
                    dm = re.match(r'(\d{1,2})[/.](\d{1,2})[/.](\d{4})', raw_date)
                    if dm:
                        date_str = f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}"
                    else:
                        date_str = raw_date
                    break
    
    # Pattern 4: Just "INFORME FINAL (IF) NN/YYYY" on its own
    if not title:
        for line in lines:
            m = re.match(r'INFORME\s+FINAL\s*\(IF\)\s*(\d+/\d{4})', line, re.I)
            if m:
                # Get next non-empty lines for description
                idx = lines.index(line)
                desc_lines = []
                for j in range(idx+1, min(idx+4, len(lines))):
                    l = lines[j]
                    if any(skip in l.upper() for skip in ['ENGLISH', '"EN NINGÚN', 'SECRETAR']):
                        break
                    if l:
                        desc_lines.append(l)
                if desc_lines:
                    title = ' '.join(desc_lines)
                break
    
    # Extract date from title if present
    if not date_str and title:
        # Patterns: "el día 11/08/2021", "el 4 de marzo de 2020", "09.02.2015", "16.04.2008"
        m = re.search(r'(\d{1,2})[/.](\d{1,2})[/.](\d{4})', title)
        if m:
            # Normalize: ensure YYYY-MM-DD format
            y, mo, d = m.group(3), m.group(2).zfill(2), m.group(1).zfill(2)
            date_str = f"{y}-{mo}-{d}"
        else:
            m = re.search(r'el\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', title, re.I)
            if m:
                months = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
                          'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
                month_num = months.get(m.group(2).lower(), 0)
                if month_num:
                    date_str = f"{m.group(3)}-{str(month_num).zfill(2)}-{m.group(1).zfill(2)}"
    
    # Also try to find date in first page text independently
    if not date_str:
        # Look for 'ocurrido el DD.MM.YYYY' or 'el día DD/MM/YYYY'
        m = re.search(r'ocurrido\s+el\s+(\d{1,2})[/.](\d{1,2})[/.](\d{4})', text, re.I)
        if m:
            date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
        else:
            m = re.search(r'el\s+día\s+(\d{1,2})/(\d{1,2})/(\d{4})', text, re.I)
            if m:
                date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
            else:
                # Try DD.MM.YYYY anywhere in first 500 chars
                m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text[:500])
                if m:
                    date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    
    # Final fallback: search full text
    if not date_str:
        full = text
        m = re.search(r'ocurrido\s+el\s+(\d{1,2})[/.](\d{1,2})[/.](\d{4})', full, re.I)
        if m:
            date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
        else:
            m = re.search(r'el\s+día\s+(\d{1,2})/(\d{1,2})/(\d{4})', full, re.I)
            if m:
                date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
            else:
                # Try DD.MM.YYYY format
                m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', full[:500])
                if m:
                    date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    
    return title, date_str


def parse_station_from_title(title):
    """Extract station/city and province from title."""
    if not title:
        return None, None
    
    station = None
    province = None
    
    # Pattern: "en la estación de X (PROVINCIA)" or "estación de Xeraco (Valencia)"
    m = re.search(r'estación\s+de\s+(.+?)(?:\s*[,.]?\s*\(([^)]+)\))?(?:\s*[,.]?\s*el\s|\s*$)', title, re.I)
    if m:
        station = m.group(1).strip().rstrip(',.')
        if m.group(2):
            province = m.group(2).strip()
    
    # Pattern: "en Medinaceli (Soria)"
    if not station:
        m = re.search(r'en\s+([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[a-záéíóú]+)*)\s*\(([^)]+)\)', title)
        if m:
            station = m.group(1).strip()
            province = m.group(2).strip()
    
    # Pattern: "EN LA ESTACIÓN DE A SUSANA (A CORUÑA)"
    if not station:
        m = re.search(r'ESTACIÓN\s+DE\s+(.+?)\s*\(([^)]+)\)', title, re.I)
        if m:
            station = m.group(1).strip()
            province = m.group(2).strip()
    
    # Pattern: "Bif. Galicia en las inmediaciones de la estación de León"
    if not station:
        m = re.search(r'(?:inmediaciones de\s+)?(?:la\s+)?estación\s+de\s+([^.]+)', title, re.I)
        if m:
            station = m.group(1).strip().rstrip('.!,')
    
    return station, province


def parse_conclusions(full_text):
    """Extract conclusions from the full document text."""
    conclusions = []
    
    # Find "CONCLUSIONES" or "CONCLUSIÓN" section
    patterns = [
        r'(?:^|\n)\s*(?:\d+\.?\s*)?CONCLUSIONES?\s*(?:\n|$)',
        r'(?:^|\n)\s*(?:\d+\.?\s*)?CONCLUSIÓN(?:ES)?\s*(?:\n|$)',
    ]
    
    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.I | re.M))
        if matches:
            # Take the last match (usually the actual conclusions, not TOC reference)
            start = matches[-1].end()
            # Find end of section (next numbered section or end of text)
            end_match = re.search(r'\n\s*\d+\.?\s+[A-ZÁÉÍÓÚ]', full_text[start:start+3000])
            if end_match:
                end = start + end_match.start()
            else:
                end = min(start + 2000, len(full_text))
            
            section = full_text[start:end].strip()
            # Clean up header/footer noise
            section = re.sub(r'Pág\.\s*\d+\s+de\s+\d+', '', section)
            section = re.sub(r'Investigación del.*?CIAF', '', section, flags=re.S)
            section = re.sub(r'SECRETAR.*?FERROVIARIOS', '', section, flags=re.S)
            section = re.sub(r'Informe\s+(?:Final|Definitivo)', '', section, flags=re.I)
            section = re.sub(r'ID-\d+.*?CIAF', '', section)
            section = section.strip()
            
            if section and len(section) > 10:
                # Split into individual conclusions if numbered
                items = re.split(r'\n\s*[-•]\s+', section)
                if len(items) > 1:
                    conclusions = [i.strip() for i in items if i.strip() and len(i.strip()) > 10]
                else:
                    # Single block of text
                    sentences = re.split(r'(?<=[.])\s+', section)
                    # Group into reasonable chunks
                    current = ''
                    for s in sentences:
                        current += s + ' '
                        if len(current) > 50:
                            conclusions.append(current.strip())
                            current = ''
                    if current.strip():
                        conclusions.append(current.strip())
            break
    
    return conclusions


def parse_recommendations(full_text):
    """Extract recommendations from the full document text."""
    recommendations = []
    
    # Find "RECOMENDACIONES" section
    patterns = [
        r'(?:^|\n)\s*(?:\d+\.?\s*)?RECOMENDACIONES?\s*(?:\n|$)',
    ]
    
    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.I | re.M))
        if matches:
            start = matches[-1].end()
            # Find end of section
            end_match = re.search(r'\n\s*\d+\.?\s+[A-ZÁÉÍÓÚ]|(?:^|\n)\s*(?:Anexos?|ANEXOS?|Bibliografía)', full_text[start:start+3000], re.M)
            if end_match:
                end = start + end_match.start()
            else:
                end = min(start + 2000, len(full_text))
            
            section = full_text[start:end].strip()
            # Clean up
            section = re.sub(r'Pág\.\s*\d+\s+de\s+\d+', '', section)
            section = re.sub(r'Investigación del.*?CIAF', '', section, flags=re.S)
            section = re.sub(r'SECRETAR.*?FERROVIARIOS', '', section, flags=re.S)
            section = re.sub(r'Informe\s+(?:Final|Definitivo)', '', section, flags=re.I)
            section = section.strip()
            
            if section and len(section) > 10:
                # Split into individual recommendations
                items = re.split(r'\n\s*[-•]\s+', section)
                if len(items) > 1:
                    seen = set()
                    for i in items:
                        t = i.strip()
                        if t and len(t) > 10 and t[:50] not in seen:
                            seen.add(t[:50])
                            recommendations.append(t)
                else:
                    # Could be "no se establecen recomendaciones"
                    if 'no se establecen' in section.lower() or 'no procede' in section.lower():
                        recommendations = [section.strip()]
                    else:
                        sentences = re.split(r'(?<=[.])\s+', section)
                        current = ''
                        for s in sentences:
                            current += s + ' '
                            if len(current) > 50:
                                recommendations.append(current.strip())
                                current = ''
                        if current.strip():
                            recommendations.append(current.strip())
            break
    
    return recommendations


def parse_severity(text, tags):
    """Determine severity from text and tags."""
    text_lower = text.lower() if text else ''
    tags_lower = [t.lower() for t in tags] if tags else []
    
    if 'fatal' in tags_lower or 'víctimas mortales' in text_lower or 'cadáver' in text_lower or 'fallec' in text_lower:
        return 'fatal'
    elif 'grave' in tags_lower or 'herido' in text_lower or 'lesion' in text_lower:
        return 'grave'
    else:
        return 'leve'


def process_pdf(pdf_path, year):
    """Process a single PDF and return extracted data."""
    text = extract_full_text(pdf_path)
    first_page = extract_first_page(pdf_path)
    last_pages = extract_last_pages(pdf_path, 4)
    
    # Extract title and date
    title, date_str = parse_title_from_first_page(first_page)
    
    # If no date from title, try full text
    if not date_str:
        m = re.search(r'ocurrido\s+el\s+(\d{1,2})[/.](\d{1,2})[/.](\d{4})', text, re.I)
        if m:
            date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
        else:
            m = re.search(r'el\s+día\s+(\d{1,2})/(\d{1,2})/(\d{4})', text, re.I)
            if m:
                date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
            else:
                m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text[:1000])
                if m:
                    date_str = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    
    # Extract station and province from title
    station, province = parse_station_from_title(title or first_page)
    
    # Extract conclusions and recommendations
    conclusions = parse_conclusions(text)
    recommendations = parse_recommendations(text)
    
    # Determine severity
    tags = []  # Will be set from existing JSON or extracted
    severity = parse_severity(text, tags)
    
    return {
        'titulo': title,
        'date': date_str,
        'station': station,
        'province': province,
        'conclusions': conclusions,
        'recommendations': recommendations,
        'severity': severity,
    }


def main():
    """Reprocess all PDFs and update JSON files."""
    stats = {'total': 0, 'improved': 0, 'conclusions_found': 0, 'recommendations_found': 0, 'dates_found': 0}
    
    for year_dir in sorted(PDFS_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        year = year_dir.name
        json_path = REPORTS_DIR / f'{year}.json'
        
        if not json_path.exists():
            continue
        
        with open(json_path) as f:
            reports = json.load(f)
        
        # Build lookup from enlaces.pdf_local to report index
        pdf_to_idx = {}
        for i, r in enumerate(reports):
            pdf_local = r.get('enlaces', {}).get('pdf_local', '')
            if pdf_local:
                # Extract just the filename from the path
                pdf_name = pdf_local.split('/')[-1]
                pdf_to_idx[pdf_name] = i
        
        modified = False
        for pdf_file in year_dir.glob('*.pdf'):
            if pdf_file.name not in pdf_to_idx:
                continue
            
            idx = pdf_to_idx[pdf_file.name]
            report = reports[idx]
            stats['total'] += 1
            
            try:
                extracted = process_pdf(pdf_file, year)
            except Exception as e:
                print(f"  ERROR processing {pdf_file}: {e}")
                continue
            
            # Update fields if we got better data
            # Only improve title if current one is a filename or very short
            if extracted['titulo'] and (not report.get('titulo') or len(report.get('titulo', '')) < 20 or report['titulo'] == pdf_file.name.replace('.pdf', '')):
                report['titulo'] = extracted['titulo']
                modified = True
                stats['improved'] += 1
            
            if extracted['date'] and not report.get('date'):
                report['date'] = extracted['date']
                modified = True
                stats['dates_found'] += 1
            
            if extracted['station'] and not report.get('station'):
                report['station'] = extracted['station']
                modified = True
            
            if extracted['province'] and not report.get('province'):
                report['province'] = extracted['province']
                modified = True
            
            if extracted['conclusions'] and not report.get('conclusiones'):
                report['conclusiones'] = extracted['conclusions']
                modified = True
                stats['conclusions_found'] += 1
            
            if extracted['recommendations'] and not report.get('recomendaciones'):
                report['recomendaciones'] = extracted['recommendations']
                modified = True
                stats['recommendations_found'] += 1
            
            if extracted['severity'] and not report.get('severity'):
                report['severity'] = extracted['severity']
                modified = True
        
        if modified:
            with open(json_path, 'w') as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
            print(f"  {year}: updated ({sum(1 for r in reports if r.get('conclusions'))} with conclusions)")
    
    print(f"\n=== RESUMEN ===")
    print(f"PDFs procesados: {stats['total']}")
    print(f"Títulos mejorados: {stats['improved']}")
    print(f"Fechas encontradas: {stats['dates_found']}")
    print(f"Conclusiones encontradas: {stats['conclusions_found']}")
    print(f"Recomendaciones encontradas: {stats['recommendations_found']}")


if __name__ == '__main__':
    main()
