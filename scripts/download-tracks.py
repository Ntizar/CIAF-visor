#!/usr/bin/env python3
"""
download-tracks.py – Descarga la red ferroviaria española de OpenStreetMap
===========================================================================

Usa Overpass API para obtener todas las vías de tren de España y genera
un archivo GeoJSON compatible con Leaflet.

Salida:
    data/train-tracks.geojson

Uso:
    python3 scripts/download-tracks.py
"""

import json
import sys
import time
import logging
import urllib.request
import urllib.parse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("tracks")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT = DATA_DIR / "train-tracks.geojson"

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Query: todas las vías de tren en España
# Incluye: líneas principales, alta velocidad, cercanías, media distancia
OVERPASS_QUERY = """
[out:json][timeout:120];
(
  // Líneas principales y alta velocidad
  way["railway"="rail"]["usage"~"main|highspeed"]({{bbox}});
  
  // Líneas regionales y de mercancías
  way["railway"="rail"]["usage"~"regional|freight"]({{bbox}});
  
  // Cercanías y metro de superficie
  way["railway"="rail"]["usage"~"commuter|suburban"]({{bbox}});
  
  // Vías sin especificar usage (cubre muchas líneas menores)
  way["railway"="rail"]["usage"!~"industrial|military|tourism|heritage"]({{bbox}});
  
  // Alta velocidad específica
  way["railway"="high_speed"]({{bbox}});
  
  // Tranvías urbanos principales (opcional, comentar si no se quiere)
  // way["railway"="tram"]["operator"]({{bbox}});
);
out body;
>;
out skel qt;
"""

# Bounding box de España peninsular + Baleares + Canarias
BBOXES = {
    "peninsular": "35.9,-9.5,43.8,4.5",
    "baleares": "38.6,0.9,40.2,4.5",
    "canarias": "27.4,-18.5,29.5,-13.2",
}


def query_overpass(bbox: str) -> dict:
    """Ejecuta una consulta Overpass y devuelve el resultado."""
    query = OVERPASS_QUERY.replace("{{bbox}}", bbox)
    
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(OVERPASS_URL, data=data, method="POST")
    req.add_header("User-Agent", "CIAF-Visor/1.0 (proyecto educativo)")
    
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.error(f"Error en Overpass API: {e}")
        return {}


def osm_to_geojson(osm_data: dict) -> dict:
    """Convierte datos OSM (nodos + ways) a GeoJSON FeatureCollection."""
    nodes = {}
    features = []
    
    for element in osm_data.get("elements", []):
        if element["type"] == "node":
            nodes[element["id"]] = (element["lon"], element["lat"])
    
    for element in osm_data.get("elements", []):
        if element["type"] != "way":
            continue
        
        # Construir coordenadas del way
        coords = []
        for node_id in element.get("nodes", []):
            if node_id in nodes:
                coords.append(nodes[node_id])
        
        if len(coords) < 2:
            continue
        
        # Determinar tipo de vía
        tags = element.get("tags", {})
        railway = tags.get("railway", "rail")
        usage = tags.get("usage", "")
        name = tags.get("name", "")
        operator = tags.get("operator", "")
        gauge = tags.get("gauge", "")
        speed = tags.get("maxspeed", "")
        
        # Color por tipo
        if railway == "high_speed" or usage == "highspeed":
            color = "#e74c3c"  # Rojo - Alta velocidad
            weight = 3
        elif usage in ("commuter", "suburban"):
            color = "#2ecc71"  # Verde - Cercanías
            weight = 2
        elif usage == "freight":
            color = "#95a5a6"  # Gris - Mercancías
            weight = 2
        else:
            color = "#3498db"  # Azul - Líneas principales
            weight = 2.5
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "osm_id": element["id"],
                "railway": railway,
                "usage": usage,
                "name": name,
                "operator": operator,
                "gauge": gauge,
                "speed": speed,
                "color": color,
                "weight": weight
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def main():
    log.info("=" * 60)
    log.info("Descarga de vías ferroviarias – OpenStreetMap/Overpass")
    log.info("=" * 60)
    
    all_features = []
    
    for region, bbox in BBOXES.items():
        log.info(f"Descargando {region} (bbox: {bbox})...")
        osm_data = query_overpass(bbox)
        
        if not osm_data:
            log.warning(f"No se obtuvieron datos para {region}")
            continue
        
        geojson = osm_to_geojson(osm_data)
        n_features = len(geojson["features"])
        log.info(f"  {region}: {n_features} tramos obtenidos")
        all_features.extend(geojson["features"])
        
        time.sleep(2)  # Pausa entre peticiones
    
    # Crear GeoJSON final
    result = {
        "type": "FeatureCollection",
        "features": all_features,
        "properties": {
            "source": "OpenStreetMap via Overpass API",
            "license": "ODbL",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_features": len(all_features)
        }
    }
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    
    log.info(f"Guardado: {OUTPUT}")
    log.info(f"Total tramos: {len(all_features)}")
    log.info("Completado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
