#!/usr/bin/env python3
"""
geocode_all.py – Geocodifica todas las estaciones de los informes CIAF
=====================================================================

1. Carga todos los JSONs de data/reports/YYYY.json
2. Extrae estaciones únicas
3. Geocodifica cada una con Nominatim (1.1s entre peticiones)
4. Actualiza los JSONs con lat/lng
5. Regenera index.json
"""

import json
import sys
import time
import re
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "data" / "reports"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CIAF-Visor/1.0"
GEOCODE_DELAY = 2.1  # 2s entre peticiones (Nominatim policy: max 1 req/s)


def geocode(station_name: str, province: str = "") -> tuple:
    """Geocodifica una estación usando Nominatim con retry."""
    clean = station_name.strip()
    clean = re.sub(r'\s+', ' ', clean)
    
    queries = [f"{clean} España"]
    if province:
        queries.append(f"{clean} {province}")
    simplified = re.sub(r'\b(Clasificación|Clasificacion|Terminal|Central|Norte|Sur|Este|Oeste)\b', '', clean).strip()
    if simplified and simplified != clean:
        queries.append(f"{simplified} España")
    
    for query in queries:
        for attempt in range(3):  # max 3 retries per query
            try:
                params = urllib.parse.urlencode({
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
                    return float(best['lat']), float(best['lon'])
                break  # Sin resultados, probar siguiente query
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = GEOCODE_DELAY * (2 ** attempt)  # 4s, 8s, 16s
                    print(f"  429, esperando {wait:.0f}s...", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"  Error {e.code}")
                    break
            except Exception as e:
                print(f"  Error: {e}")
                break
        time.sleep(GEOCODE_DELAY)
    
    return None, None


def main():
    print("=" * 60)
    print("Geocodificación de estaciones CIAF")
    print("=" * 60)
    
    # Cargar todos los informes y recoger estaciones únicas
    station_map = {}  # (estacion, provincia) -> [(year, report_id)]
    all_reports = {}  # year -> [reports]
    
    for year_file in sorted(REPORTS_DIR.glob("*.json")):
        if year_file.name == "index.json":
            continue
        year = int(year_file.stem)
        with open(year_file) as f:
            reports = json.load(f)
        all_reports[year] = reports
        
        for r in reports:
            est = r.get('ubicacion', {}).get('estacion', '')
            prov = r.get('ubicacion', {}).get('provincia', '')
            lat = r.get('ubicacion', {}).get('lat')
            
            if est and not lat and len(est) < 40:  # Solo geocodificar nombres cortos
                key = (est.strip(), prov.strip())
                if key not in station_map:
                    station_map[key] = []
                station_map[key].append((year, r.get('id', '')))
    
    unique_stations = list(station_map.keys())
    print(f"\nEstaciones únicas sin geocodificar: {len(unique_stations)}")
    total = len(unique_stations)
    
    # Geocodificar
    geo_cache = {}
    for i, (est, prov) in enumerate(unique_stations):
        print(f"[{i+1}/{total}] {est} ({prov})...", end=" ", flush=True)
        lat, lng = geocode(est, prov)
        geo_cache[(est, prov)] = (lat, lng)
        if lat:
            print(f"✓ {lat:.4f}, {lng:.4f}")
        else:
            print("✗ no encontrado")
    
    # Actualizar JSONs
    updated = 0
    for year, reports in all_reports.items():
        changed = False
        for r in reports:
            est = r.get('ubicacion', {}).get('estacion', '').strip()
            prov = r.get('ubicacion', {}).get('provincia', '').strip()
            key = (est, prov)
            if key in geo_cache and geo_cache[key] != (None, None):
                lat, lng = geo_cache[key]
                r['ubicacion']['lat'] = lat
                r['ubicacion']['lng'] = lng
                changed = True
                updated += 1
        
        if changed:
            with open(REPORTS_DIR / f"{year}.json", 'w') as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Geocodificados: {updated} informes")
    print(f"No encontrados: {sum(1 for v in geo_cache.values() if v == (None, None))} estaciones")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
