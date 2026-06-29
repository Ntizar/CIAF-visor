#!/usr/bin/env python3
"""
CIAF Visor Complete Fixer v3
Extrae estaciones del resumen, limpia nombres, re-geolocaliza todo.
"""

import json, os, re, time, urllib.request, urllib.parse

REPORT_DIR = "/root/workspace/CIAF-visor/data/reports"
STATION_COORDS_PATH = "/root/workspace/CIAF-visor/data/station-coords.json"
INDIVIDUAL_DIR = "/root/workspace/ciaf-data/data/individual"

# A Coruña default coords (from failed parsing)
DEFAULT_LAT, DEFAULT_LNG = 43.336, -8.3953

# Province names
PROVINCES = {
    'a coruña', 'álava', 'albacete', 'alicante', 'almería', 'asturias', 'ávila',
    'badajoz', 'barcelona', 'bizkaia', 'burgos', 'cáceres', 'cádiz', 'cantabria',
    'castellón', 'ciudad real', 'córdoba', 'cuenca', 'gipuzkoa', 'girona',
    'granada', 'guadalajara', 'huelva', 'huesca', 'islas baleares', 'jaén',
    'león', 'lleida', 'lugo', 'madrid', 'málaga', 'murcia', 'navarra',
    'orense', 'ourense', 'palencia', 'pontevedra', 'la rioja', 'salamanca',
    'soria', 'tarragona', 'teruel', 'toledo', 'valencia', 'valladolid',
    'vizcaya', 'zamora', 'zaragoza',
}

def extract_station_from_text(text):
    """Extract station name from resumen/descripcion text."""
    if not text:
        return None, None
    
    # Pattern: "estación de X" or "estación de X (Y)"
    patterns = [
        r'estaci[oó]n\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de|del|la|el|los|las|a|en|y)\s+[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+)*(?:\s*\([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\))?)',
        r'apeadero\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de|del|la|el|los|las|a|en|y)\s+[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+)*(?:\s*\([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\))?)',
        r'en\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de|del|la|el|los|las|a|en|y)\s+[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+)*(?:\s*\([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\))?)\s*,',
        r'paso a nivel\s+(?:de\s+|entre\s+[^i]+y\s+)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de|del|la|el|los|las|a|en|y)\s+[A-ZÁÉÍÓÚÑ]?[a-záéíóúñ]+)*)',
    ]
    
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            station = m.group(1).strip()
            # Clean province in parentheses
            station = re.sub(r'\s*\([^)]*\)\s*$', '', station)
            return station, None
    
    return None, None


def extract_province_from_text(text):
    """Extract province from resumen text."""
    if not text:
        return None
    
    # Look for province in parentheses
    m = re.search(r'\(([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)*)\)', text)
    if m:
        prov = m.group(1).strip().lower()
        if prov in PROVINCES:
            return m.group(1).strip()
    
    # Look for province name standalone
    for prov in PROVINCES:
        if re.search(r'\b' + re.escape(prov) + r'\b', text, re.IGNORECASE):
            return prov.title()
    
    return None


def clean_station_name(name):
    """Clean station name aggressively."""
    if not name:
        return name
    
    cleaned = name.strip()
    
    # Remove trailing periods and numbers
    cleaned = re.sub(r'[.\s]*\d+\s*$', '', cleaned)
    
    # Remove province in parentheses
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)
    
    # Remove trailing junk
    cleaned = re.sub(r'\s+(y suprimido|sobre las \d+|a las \d+:\d+|desde|en|por|y éste|y con)\s*$', '', cleaned, flags=re.IGNORECASE)
    
    # Remove "Pk NNN" suffix
    cleaned = re.sub(r'\s+[Pp][Kk]\s*\d+.*$', '', cleaned)
    
    # Remove "desde" prefix
    cleaned = re.sub(r'^\w+\s+desde\s+', '', cleaned)
    
    # Remove trailing dots
    cleaned = cleaned.rstrip('.')
    cleaned = cleaned.strip()
    
    # Fix specific known issues
    fixes = {
        'Atocha)': 'Madrid Puerta de Atocha',
        'Atocha-Cercanías': 'Madrid Atocha Cercanías',
        'Barcelona Estació de': 'Barcelona Estació de França',
        'Barcelona Sant Andreu': 'Barcelona Sant Andreu Comtal',
        'L\'Hospitalet de': 'L\'Hospitalet de Llobregat',
        'San Vicente de la': 'San Vicente de la Barquera',
        'Caparrates es el': 'Caparrates',
        'Santa María de la': 'Santa María de la Alameda',
        'Chapela y con': 'Chapela',
        'Ronda y éste': 'Ronda',
        'Villamanín por': 'Villamanín',
        'Francia (ancho': 'Irún',
        'Francia y': 'Irún',
        'trenes del apeadero': None,  # Will be extracted from text
        'San': None,  # Will be extracted from text
        'La': None,  # Will be extracted from text
        'Urda () y': 'Urda',
        'Pk': None,
    }
    
    if cleaned in fixes:
        if fixes[cleaned] is None:
            return None  # Signal to extract from text
        cleaned = fixes[cleaned]
    
    # Title case if all uppercase
    if cleaned.isupper() and len(cleaned) > 3:
        cleaned = cleaned.title()
        cleaned = re.sub(r'\bDe\b', 'de', cleaned)
        cleaned = re.sub(r'\bDel\b', 'del', cleaned)
        cleaned = re.sub(r'\bLa\b', 'la', cleaned)
        cleaned = re.sub(r'\bEl\b', 'el', cleaned)
        cleaned = re.sub(r'\bLos\b', 'los', cleaned)
        cleaned = re.sub(r'\bLas\b', 'las', cleaned)
        cleaned = re.sub(r'\bY\b', 'y', cleaned)
        cleaned = re.sub(r'\bA\b', 'a', cleaned)
    
    return cleaned


def load_station_db():
    """Load station coordinates database."""
    with open(STATION_COORDS_PATH) as f:
        db = json.load(f)
    # Build lowercase lookup
    lookup = {}
    for k, v in db.items():
        lookup[k.lower().strip()] = v
    return lookup


def geocode_nominatim(name, provincia=''):
    """Geocode using Nominatim."""
    query = f"{name}, España"
    if provincia:
        query = f"{name}, {provincia}, España"
    
    params = urllib.parse.urlencode({
        'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'es'
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'CIAF-Visor/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return None, None


def main():
    print("=" * 60)
    print("  CIAF Visor Complete Fixer v3")
    print("=" * 60)
    
    station_db = load_station_db()
    print(f"Station DB: {len(station_db)} entries")
    
    # Load individual JSONs for cross-reference
    ind_index = {}
    for f in os.listdir(INDIVIDUAL_DIR):
        if not f.endswith('.json'):
            continue
        with open(os.path.join(INDIVIDUAL_DIR, f)) as fh:
            d = json.load(fh)
        exp = None
        if '_cross_ref' in d:
            exp = d['_cross_ref'].get('excel_exp')
        if exp:
            ind_index[exp] = d
    
    print(f"Individual JSONs: {len(ind_index)}")
    
    year_files = sorted([f for f in os.listdir(REPORT_DIR) if f.endswith('.json')])
    
    total_fixed = 0
    total_extracted = 0
    total_nominatim = 0
    
    for yf in year_files:
        fpath = os.path.join(REPORT_DIR, yf)
        with open(fpath) as f:
            records = json.load(f)
        
        changed = False
        
        for r in records:
            exp = r.get('expediente', '')
            loc = r.get('ubicacion', {})
            old_est = loc.get('estacion', '')
            lat = loc.get('lat')
            lng = loc.get('lng')
            
            # Check if coords are wrong (A Coruña default)
            is_default = (lat and abs(lat - DEFAULT_LAT) < 0.01 and abs(lng - DEFAULT_LNG) < 0.01)
            
            # 1. Try to extract station from resumen
            resumen = r.get('analisis', {}).get('resumen', '') or r.get('resumen_verificado', '') or ''
            titulo = r.get('titulo', '')
            
            extracted_est, _ = extract_station_from_text(resumen + ' ' + titulo)
            
            # 2. Clean current station name
            cleaned_est = clean_station_name(old_est) if old_est else None
            
            # 3. Choose best station name
            best_est = None
            if extracted_est and len(extracted_est) > 2:
                best_est = extracted_est
            elif cleaned_est and len(cleaned_est) > 2:
                best_est = cleaned_est
            elif old_est and len(old_est) > 2:
                # Try cleaning more aggressively
                best_est = clean_station_name(old_est)
            
            # 4. If still no station, try individual JSON
            if not best_est or len(best_est) <= 2:
                ind_data = ind_index.get(exp, {})
                if ind_data.get('estacion'):
                    best_est = ind_data['estacion']
            
            # 5. Update station name if improved
            if best_est and best_est != old_est:
                loc['estacion'] = best_est
                changed = True
            
            # 6. Re-geolocate if needed
            needs_geo = is_default or not lat or not lng
            
            if needs_geo and best_est:
                # Try station DB
                est_lower = best_est.lower().strip()
                found = False
                
                # Exact match
                if est_lower in station_db:
                    coords = station_db[est_lower]
                    loc['lat'] = coords.get('lat')
                    loc['lng'] = coords.get('lng')
                    changed = True
                    total_fixed += 1
                    found = True
                
                # Partial match
                if not found:
                    for db_key, db_val in station_db.items():
                        if est_lower in db_key or db_key in est_lower:
                            loc['lat'] = db_val.get('lat')
                            loc['lng'] = db_val.get('lng')
                            changed = True
                            total_fixed += 1
                            found = True
                            break
                
                # Nominatim fallback
                if not found:
                    prov = loc.get('provincia', '')
                    lat2, lng2 = geocode_nominatim(best_est, prov)
                    if lat2 and lng2:
                        loc['lat'] = lat2
                        loc['lng'] = lng2
                        changed = True
                        total_nominatim += 1
                        time.sleep(1.1)
                    else:
                        # Extract province from resumen
                        prov_from_text = extract_province_from_text(resumen)
                        if prov_from_text:
                            loc['provincia'] = prov_from_text
                            lat3, lng3 = geocode_nominatim(best_est, prov_from_text)
                            if lat3 and lng3:
                                loc['lat'] = lat3
                                loc['lng'] = lng3
                                changed = True
                                total_nominatim += 1
                                time.sleep(1.1)
            
            # 7. Fix province if wrong
            prov_from_text = extract_province_from_text(resumen)
            if prov_from_text and prov_from_text != loc.get('provincia'):
                # Only update if current province seems wrong
                if is_default or not loc.get('provincia'):
                    loc['provincia'] = prov_from_text
                    changed = True
        
        if changed:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            total_extracted += sum(1 for r in records if r.get('ubicacion', {}).get('estacion'))
    
    print(f"\n{'=' * 60}")
    print(f"  RESUMEN")
    print(f"{'=' * 60}")
    print(f"  Geocodificados desde DB: {total_fixed}")
    print(f"  Geocodificados desde Nominatim: {total_nominatim}")
    
    # Final stats
    final_default = 0
    final_empty = 0
    final_total = 0
    final_geo = 0
    
    for yf in year_files:
        with open(os.path.join(REPORT_DIR, yf)) as f:
            data = json.load(f)
        for r in data:
            final_total += 1
            loc = r.get('ubicacion', {})
            lat = loc.get('lat')
            lng = loc.get('lng')
            est = loc.get('estacion', '')
            
            if not est or len(est) <= 2:
                final_empty += 1
            if lat and abs(lat - DEFAULT_LAT) < 0.01 and abs(lng - DEFAULT_LNG) < 0.01:
                final_default += 1
            if lat and lng:
                final_geo += 1
    
    print(f"\n📊 Estado final:")
    print(f"  Total: {final_total}")
    print(f"  Geolocalizados: {final_geo}")
    print(f"  Con coords por defecto: {final_default}")
    print(f"  Estación vacía/corta: {final_empty}")


if __name__ == '__main__':
    main()
