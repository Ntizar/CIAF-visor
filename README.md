# CIAF Visor — Visor integral de informes de accidentes ferroviarios

![CIAF Visor](https://img.shields.io/badge/CIAF-Visor-v2.1-blue)
![Datos](https://img.shields.io/badge/Datos-269_informes-green)
![Memorias](https://img.shields.io/badge/Memorias-18_anuales-orange)
![Años](https://img.shields.io/badge/Años-2007--2025-purple)

Visor interactivo de **todos** los informes de accidentes ferroviarios de la **Comisión de Investigación de Accidentes Ferroviarios (CIAF)** de España, desde 2007 hasta 2025.

**Enlace:** [https://ntizar.github.io/CIAF-visor/](https://ntizar.github.io/CIAF-visor/)

---

## 📋 ¿Qué es esto?

Un sistema completo para:

- **Visualizar** todos los informes de accidentes ferroviarios en un mapa interactivo
- **Analizar** tendencias, causas y estadísticas con dashboards interactivos
- **Comparar** datos entre años usando las memorias anuales de la CIAF
- **Buscar** informes por estación, empresa, tipo de suceso o gravedad

### Fuentes de datos

| Fuente | Cantidad | Período | Enlace |
|--------|----------|---------|--------|
| Informes de accidentes | 269 informes (JSON) | 2007-2025 | [transportes.gob.es](https://www.transportes.gob.es/organos-colegiados/ciaf/informes-finales-de-sucesos-investigados) |
| Memorias anuales | 18 resúmenes (JSON) | 2007-2024 | [transportes.gob.es](https://www.transportes.gob.es/organos-colegiados/ciaf/memorias-anuales/memoriasanuales) |

### Capas geoespaciales (en vivo)

| Capa | Fuente | Uso |
|------|--------|-----|
| Mapa base | IGN España (WMTS) | Cartografía oficial |
| Red ferroviaria | ADIF WMS | Visualización de vías |
| Limitaciones de velocidad | ArcGIS FeatureServer | Restricciones LTV |

---

## 🗂️ Estructura del proyecto

```
CIAF-visor/
├── data/
│   ├── index.json              # Índice: años disponibles, estadísticas globales
│   ├── reports/                # Fuente de verdad: 269 informes (JSON)
│   │   ├── 2007.json           # Array de objetos informe
│   │   ├── 2008.json
│   │   ├── ...
│   │   └── 2025.json
│   └── memorias/               # Resúmenes anuales (JSON)
│       ├── 2007.json
│       ├── ...
│       └── 2024.json
├── frontend/
│   └── index.html              # App SPA completa (HTML + CSS + JS inline)
├── scripts/
│   ├── parse_all.py            # Pipeline: PDF → JSON individuales
│   ├── parse_reports_v2.py     # Parser v2 de informes
│   ├── parse_year_v2.py        # Parser por año
│   ├── generate_index.py       # Genera index.json desde reports/
│   ├── sync.py                 # Sincronización de datos
│   ├── test_parser.py          # Tests del parser
│   └── archive/                # Scripts de fix completados (solo referencia)
└── README.md
```

---

## 📊 Esquema de datos

### Informe (`data/reports/YYYY.json`)

```json
{
  "id": "2009-0001/2009",
  "year": 2009,
  "expediente": "0001/2009",
  "titulo": "INFORME FINAL SOBRE LA INVESTIGACIÓN DEL ACCIDENTE FERROVIARIO...",
  "tipo": "accidente",
  "tipo_suceso": "otro_accidente",
  "gravedad": "muy grave",
  "fecha_suceso": "2009-01-01",
  "ubicacion": {
    "estacion": "Estación de Sitges",
    "provincia": "Barcelona",
    "lat": 41.2367,
    "lng": 1.8034,
    "lugar": "Estación de Sitges"
  },
  "entidades": ["ADIF", "Renfe Operadora"],
  "consecuencias": {
    "victimas_mortales": 3,
    "heridos": 0,
    "danos_materiales": true
  },
  "analisis": {
    "resumen": "Accidente ferroviario ocurrido el 1 de enero de 2009...",
    "causa_directa": "Acercamiento de la víctima al tren..."
  },
  "conclusiones": ["El accidente tuvo su origen en..."],
  "recomendaciones": [],
  "tags": ["accidente", "arrollamiento", "fatal"],
  "enlaces": {
    "ciaf_web": "https://www.transportes.gob.es/..."
  }
}
```

### Memoria (`data/memorias/YYYY.json`)

```json
{
  "year": 2009,
  "title": "Memoria Anual CIAF 2009",
  "summary": "De los 70 sucesos notificados...",
  "total_accidents": 56,
  "total_incidents": 11,
  "total_fatal": 8,
  "top_causes": [...],
  "top_entities": [...],
  "highlights": "El 37% de los sucesos investigados..."
}
```

---

## 🚀 Despliegue

El proyecto se despliega automáticamente vía **GitHub Pages** con el workflow `.github/workflows/pages.yml`.

### Estructura de carga del frontend

1. `index.json` → años disponibles
2. `reports/YYYY.json` → datos de cada año
3. `memorias/YYYY.json` → memorias (bajo demanda)
4. Capas externas: IGN WMTS, ADIF WMS, ArcGIS LTV

---

## 🔧 Scripts del pipeline

| Script | Función | Estado |
|--------|---------|--------|
| `parse_all.py` | Pipeline completo: PDF → JSON individuales | Activo |
| `parse_reports_v2.py` | Parser v2 de informes CIAF | Activo |
| `parse_year_v2.py` | Parser por año con batch processing | Activo |
| `generate_index.py` | Genera `index.json` desde reports | Activo |
| `sync.py` | Sincronización y actualización | Activo |
| `test_parser.py` | Tests del parser | Activo |

### Archivo de scripts completados

`scripts/archive/` contiene scripts de fix que ya ejecutaron su trabajo:
- `cruce_datos.py` — Cruce JSON individuales + Excel
- `fix_visor_complete.py` — Fix nombres, provincias, geocoding
- `fix_visor_data.py` — Fix gravedad y tipología
- `geocode_all.py` / `geocode_visor.py` — Geocodificación
- `build-station-map.py` — Construcción DB estaciones

---

## ⚠️ Errores conocidos y lecciones

### Cross-reference por expediente incompleto

El error más grave descubierto: cruzar por número de expediente **sin el año** causa corrupción masiva de datos.

```
# MAL — el mismo resumen se copia a 5 registros:
exp = "50"  # → 50/2008, 50/2009, 50/2010, 50/2011, 50/2012 todos iguales

# BIEN — matching completo:
exp = "0050/2009"  # → solo el registro correcto
```

### Geolocalización por PK

La interpolación por PK puede dar coords erróneas (>0.1 grado diferencia). Siempre verificar coords del JSON individual antes de usar LTV.

### Coordenadas duplicadas erróneas

Registros de provincias diferentes compartiendo las mismas coords = error de interpolación PK. Ejemplo: 3 registros (Zaragoza, Soria, Lleida) con coords (41.63, 0.51).

---

## 📜 Normativa aplicable

- **RD 929/2020** — Agencia de Seguridad Ferroviaria
- **Ley 38/2015** — Investigación de accidentes ferroviarios
- **RD 623/2014** — Organización del CIAF
- **Directiva (UE) 2016/798** — Investigación de accidentes ferroviarios

---

## 📄 Licencia

- **Datos:** Públicos (fuente: Ministerio de Transportes)
- **Código:** MIT

---

Hecho con ❤️ por David Antizar
