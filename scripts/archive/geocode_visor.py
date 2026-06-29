#!/usr/bin/env python3
"""
CIAF Visor Geocoder v2
Limpia nombres de estación y geolocaliza los que faltan usando Nominatim.
"""

import json, os, re, time, urllib.request, urllib.parse

REPORT_DIR = "/root/workspace/CIAF-visor/data/reports"
STATION_COORDS_PATH = "/root/workspace/CIAF-visor/data/station-coords.json"

# Province names to strip from station names
PROVINCES = [
    'a coruña', 'álava', 'albacete', 'alicante', 'almería', 'asturias', 'ávila',
    'badajoz', 'barcelona', 'bizkaia', 'burgos', 'cáceres', 'cádiz', 'cantabria',
    'castellón', 'ciudad real', 'córdoba', 'cuenca', 'gipuzkoa', 'girona',
    'granada', 'guadalajara', 'guipúzcoa', 'huelva', 'huesca', 'islas baleares',
    'jaén', 'león', 'lleida', 'lugo', 'madrid', 'málaga', 'murcia', 'navarra',
    'orense', 'ourense', 'palencia', 'pontevedra', 'la rioja', 'salamanca',
    'santa cruz de tenerife', 'segovia', 'sevilla', 'soria', 'tarragona',
    'teruel', 'toledo', 'valencia', 'valladolid', 'vizcaya', 'zamora', 'zaragoza',
]

def clean_station_name(name):
    """Aggressively clean station name for geocoding."""
    if not name:
        return name
    
    cleaned = name.strip()
    
    # Remove trailing periods and numbers
    cleaned = re.sub(r'[.\s]*\d+\s*$', '', cleaned)
    
    # Remove province in parentheses: "Aboño (Asturias)" → "Aboño"
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)
    cleaned = re.sub(r'\s*\([^)]*\)', '', cleaned)
    
    # Remove trailing "y suprimido", "sobre las X", "a las X:XX", "desde", "en"
    cleaned = re.sub(r'\s+(y suprimido|sobre las \d+|a las \d+:\d+|desde|en)\s*$', '', cleaned, flags=re.IGNORECASE)
    
    # Remove "Pk NNN" or "PK NNN" suffix
    cleaned = re.sub(r'\s+[Pp][Kk]\s*\d+.*$', '', cleaned)
    
    # Remove trailing dots
    cleaned = cleaned.rstrip('.')
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    # Fix specific messy names
    fixes = {
        'Atocha)': 'Madrid Puerta de Atocha',
        'Atocha-Cercanías': 'Madrid Atocha Cercanías',
        'Barcelona Estació de': 'Barcelona Estació de França',
        'Barcelona Sant Andreu': 'Barcelona Sant Andreu Comtal',
        'Betanzos - Infesta': 'Betanzos-Infesta',
        'Calzada de Bureba': 'Calzada de Bureba',
        'Castellbibal': 'Castellbisbal',
        'Córdoba': 'Córdoba',
        'Cornellá': 'Cornellà de Llobregat',
        'Coslada': 'Coslada',
        'Pradell de Cascante': 'Pradell de la Teca',
        'Pradrell': 'Pradell de la Teca',
        'Valladolid': 'Valladolid Campo Grande',
        'Torrijos': 'Torrijos',
        'Chinchilla AV': 'Chinchilla',
        'Canfranc': 'Canfranc',
        'Busdongo': 'Busdongo de Arbás',
        'Boñar': 'Boñar',
        'Bifurcación Cerrato': 'Bifurcación Cerrato',
        'Ascó': 'Ascó',
        'Aluche': 'Aluche',
        'Almendralejo': 'Almendralejo',
        'Arcos de Jalón': 'Arcos de Jalón',
        'Arévalo': 'Arévalo',
        'Astillero': 'Astillero',
        'Blanes': 'Blanes',
        'Cheste': 'Cheste',
        'Chinchilla': 'Chinchilla de Monte-Aragón',
    }
    
    if cleaned in fixes:
        cleaned = fixes[cleaned]
    
    # Title case if all uppercase
    if cleaned.isupper() and len(cleaned) > 3:
        cleaned = cleaned.title()
        # Fix prepositions
        cleaned = re.sub(r'\bDe\b', 'de', cleaned)
        cleaned = re.sub(r'\bDel\b', 'del', cleaned)
        cleaned = re.sub(r'\bLa\b', 'la', cleaned)
        cleaned = re.sub(r'\bEl\b', 'el', cleaned)
        cleaned = re.sub(r'\bLos\b', 'los', cleaned)
        cleaned = re.sub(r'\bLas\b', 'las', cleaned)
        cleaned = re.sub(r'\bY\b', 'y', cleaned)
        cleaned = re.sub(r'\bA\b', 'a', cleaned)
    
    return cleaned


def geocode_nominatim(name, provincia=''):
    """Geocode using Nominatim with delay."""
    query = f"{name}, España"
    if provincia:
        query = f"{name}, {provincia}, España"
    
    params = urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'limit': 1,
        'countrycodes': 'es'
    })
    
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={'User-Agent': 'CIAF-Visor/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        pass
    
    return None, None


def main():
    print("=" * 60)
    print("  CIAF Visor Geocoder v2")
    print("=" * 60)
    
    # Load station DB
    with open(STATION_COORDS_PATH) as f:
        station_db = json.load(f)
    
    # Build lookup: lowercase → coords
    db_lookup = {}
    for k, v in station_db.items():
        db_lookup[k.lower().strip()] = v
    
    # Process all year files
    year_files = sorted([f for f in os.listdir(REPORT_DIR) if f.endswith('.json')])
    
    total_fixed = 0
    total_nominatim = 0
    still_missing = []
    
    for yf in year_files:
        fpath = os.path.join(REPORT_DIR, yf)
        with open(fpath) as f:
            records = json.load(f)
        
        changed = False
        year_fixed = 0
        
        for r in records:
            loc = r.get('ubicacion', {})
            old_est = loc.get('estacion', '')
            
            # Skip if already geolocated
            if loc.get('lat') and loc.get('lng'):
                continue
            
            # Clean station name
            new_est = clean_station_name(old_est)
            if new_est != old_est:
                loc['estacion'] = new_est
                changed = True
            
            # Try DB lookup
            est_lower = new_est.lower().strip()
            if est_lower in db_lookup:
                coords = db_lookup[est_lower]
                loc['lat'] = coords.get('lat')
                loc['lng'] = coords.get('lng')
                changed = True
                year_fixed += 1
                total_fixed += 1
                continue
            
            # Try partial match
            found = False
            for db_key, db_val in db_lookup.items():
                if est_lower in db_key or db_key in est_lower:
                    loc['lat'] = db_val.get('lat')
                    loc['lng'] = db_val.get('lng')
                    changed = True
                    year_fixed += 1
                    total_fixed += 1
                    found = True
                    break
            
            if found:
                continue
            
            # Try Nominatim
            provincia = loc.get('provincia', '')
            lat, lng = geocode_nominatim(new_est, provincia)
            if lat and lng:
                loc['lat'] = lat
                loc['lng'] = lng
                changed = True
                total_nominatim += 1
                time.sleep(1.1)  # Rate limit
            else:
                still_missing.append({
                    'expediente': r.get('expediente', '?'),
                    'estacion': new_est,
                    'provincia': provincia
                })
        
        if changed:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        
        if year_fixed:
            print(f"  {yf.replace('.json','')}: {year_fixed} geocoded from DB")
    
    print(f"\n{'=' * 60}")
    print(f"  RESUMEN")
    print(f"{'=' * 60}")
    print(f"  Geocodificados desde DB: {total_fixed}")
    print(f"  Geocodificados desde Nominatim: {total_nominatim}")
    print(f"  Total nuevos: {total_fixed + total_nominatim}")
    
    if still_missing:
        print(f"\n⚠️  Aún sin geolocalizar ({len(still_missing)}):")
        for item in still_missing:
            print(f"  {item['expediente']:15s} | {item['estacion'][:35]:35s} | {item['provincia']}")
    
    # Final count
    final_geo = 0
    total = 0
    for yf in year_files:
        with open(os.path.join(REPORT_DIR, yf)) as f:
            data = json.load(f)
        for r in data:
            total += 1
            loc = r.get('ubicacion', {})
            if loc.get('lat') and loc.get('lng'):
                final_geo += 1
    
    print(f"\n📍 Total final: {final_geo}/{total} geolocalizados ({final_geo*100//total}%)")


if __name__ == '__main__':
    main()
