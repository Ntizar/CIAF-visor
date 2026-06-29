# CIAF Visor — Visor integral de informes de accidentes ferroviarios

![CIAF Visor](https://img.shields.io/badge/CIAF-Visor-v2.0-blue)
![Datos](https://img.shields.io/badge/Datos-269_informes-green)
![Memorias](https://img.shields.io/badge/Memorias-17_anuales-orange)
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
- **Exportar** datos estructurados en formato JSON

### Fuentes de datos

| Fuente | Cantidad | Período | Enlace |
|--------|----------|---------|--------|
| Informes de accidentes | 269 JSONs (de ~294 PDFs) | 2007-2025 | [transportes.gob.es](https://www.transportes.gob.es/organos-colegiados/ciaf/informes-finales-de-sucesos-investigados) |
| Memorias anuales | 17 PDFs | 2008-2024 | [transportes.gob.es](https://www.transportes.gob.es/organos-colegiados/ciaf/memorias-anuales/memoriasanuales) |
| Vías de tren | Red ferroviaria España | Actual | OpenStreetMap (Overpass API) |
| Coordenadas estaciones | 355 estaciones | Actual | ADIF LTV FeatureServer |

---

## 🗂️ Estructura del proyecto

```
CIAF-visor/
├── data/                          # ← DATOS PROCESADOS (JSON) - Source of Truth
│   ├── reports/                   # Informes por año (269 registros)
│   │   ├── 2007.json              # Array de objetos informe
│   │   ├── 2008.json
│   │   ├── ...
│   │   ├── 2025.json
│   │   └── YYYY/                  # Índices por año (generados)
│   │       └── index.json
│   ├── memorias/                  # Memorias anuales
│   │   ├── 2008.json
│   │   └── ...
│   ├── station-coords.json        # Coordenadas de 355 estaciones
│   ├── index.json                 # Índice global consolidado
│   ├── relations.json             # Relaciones entidades ↔ informes
│   └── images/                    # Imágenes extraídas de PDFs
│       └── YYYY/
├── ciaf-data/                     # ← JSONs INDIVIDUALES por informe
│   └── data/
│       └── individual/            # 268 archivos: NNNN_YY_CIAF.json
│           ├── 0002CIAF.json
│           ├── 0033_09_CIAF.json
│           └── ...
├── pdfs/                          # PDFs originales (NO subir a GitHub)
│   ├── 2007/ ... 2025/            # Organizados por año
│   ├── memorias/                  # Memorias anuales
│   └── normativa/                 # Documentos normativos
├── frontend/                      # Frontend web
│   ├── index.html                 # Visor principal
│   └── css/
│       └── kaizen.css             # Kaizen Design System
├── scripts/                       # Scripts de procesamiento
│   ├── parse_all.py               # Parser principal de PDFs → JSON
│   ├── parse_reports_v2.py        # Parser mejorado v2
│   ├── cruce_datos.py             # Cruce Excel ↔ JSONs individuales
│   ├── geocode_visor.py           # Geocodificación de estaciones
│   ├── geocode_all.py             # Geocodificación masiva
│   ├── fix_visor_data.py          # Corrección de gravedad/tipología
│   ├── fix_visor_complete.py      # Fix completo de estaciones
│   ├── build-station-map.py       # Construcción DB de estaciones
│   ├── download-tracks.py         # Descarga vías de tren (OSM)
│   ├── generate_index.py          # Generación de index.json
│   ├── sync.py                    # Sincronización con web CIAF
│   └── test_parser.py             # Tests del parser
├── normativa/                     # Documentos normativos
├── auditoria-ciaf-2025-06-29.md   # Auditoría completa de datos
├── cruce-datos-reporte-final.md   # Reporte de cruce Excel ↔ JSONs
├── .gitignore                     # Excluye pdfs/ y archivos temporales
└── README.md                      # Este archivo
```

---

## 🔄 Flujo de datos

### Pipeline completo

```
PDFs CIAF (web)
    ↓ [sync.py]
PDFs en pdfs/YYYY/
    ↓ [parse_all.py / parse_reports_v2.py]
JSONs individuales en ciaf-data/data/individual/
    ↓ [cruce_datos.py + Excel]
Correcciones (severidad, tipología,PKs)
    ↓ [fix_visor_data.py + geocode_visor.py]
data/reports/YYYY.json (Source of Truth para el visor)
    ↓ [GitHub Pages]
Frontend interactivo
```

### Fuentes de verdad

| Campo | Fuente | Notas |
|-------|--------|-------|
| **Título del informe** | JSON individual (extraído del PDF) | Título original del documento |
| **Conclusiones** | JSON individual (extraído del PDF) | Texto literal del informe |
| **Recomendaciones** | JSON individual (extraído del PDF) | Texto literal del informe |
| **Severidad** | Excel + RD 929/2022 | "fatal" → "muy grave" |
| **Tipología** | Excel (normalizada a ~18 categorías) | RD 929/2022 |
| **Provincia** | Excel | Más fiable que PDFs individuales |
| **Estación** | Excel + JSON individual | Limpieza de nombres |
| **PK / Tramo** | Excel + JSON individual | Point kilometer y línea ADIF |
| **Coordenadas** | JSON individual (lat/lng) | Geolocalización por PK + ADIF LTV |
| **Fecha** | JSON individual | Formato ISO 8601 |

---

## 🚀 Instalación y uso

### Requisitos

- Python 3.8+
- pip

### Dependencias

```bash
pip install PyMuPDF openpyxl requests
```

### Procesar informes (pipeline completo)

```bash
# 1. Sincronizar PDFs desde la web CIAF
python3 scripts/sync.py

# 2. Parsear todos los PDFs → JSONs individuales
python3 scripts/parse_all.py

# 3. Cruzar con Excel (requiere el archivo Excel)
python3 scripts/cruce_datos.py

# 4. Corregir gravedad y tipología
python3 scripts/fix_visor_data.py

# 5. Geolocalizar estaciones
python3 scripts/geocode_visor.py

# 6. Generar index.json consolidado
python3 scripts/generate_index.py

# 7. Descargar vías de tren de OpenStreetMap
python3 scripts/download-tracks.py
```

### Ejecutar localmente

```bash
cd frontend/
python3 -m http.server 8000
# Abrir http://localhost:8000
```

### Deploy en GitHub Pages

1. Crear repo `CIAF-visor` en GitHub
2. Subir el código (excluyendo `pdfs/` con `.gitignore`)
3. Activar GitHub Pages en Settings → Pages → Source: GitHub Actions
4. El frontend se despliega automáticamente

---

## 📊 Estructura de un informe (JSON)

Cada registro en `data/reports/YYYY.json` tiene esta estructura:

```json
{
  "id": "2009-0033",
  "year": 2009,
  "expediente": "0033/2009",
  "titulo": "INFORME FINAL SOBRE EL ACCIDENTE FERROVIARIO Nº 0033/2009...",
  "tipo": "accidente",
  "tipo_suceso": "Arrollamiento de persona por tren",
  "gravedad": "muy grave",
  "fecha_suceso": "2009-07-08",
  "hora": "18:21",
  "ubicacion": {
    "estacion": "Ribamontán al Monte",
    "provincia": "Cantabria",
    "lugar": "Paso a nivel clase C en Villaverde de Pontones",
    "lat": 43.372215,
    "lng": -3.902858
  },
  "pk": "551+254",
  "tramo": "24 Santander - Bilbao",
  "entidades": {
    "operador": "FEVE",
    "infraestructura": "ADIF"
  },
  "consecuencias": {
    "fallecidos": 1,
    "heridos_graves": 0,
    "heridos_leves": 0
  },
  "analisis": {
    "resumen": "Accidente ferroviario ocurrido el 8 de julio de 2009...",
    "causa_directa": "Invasión del gálibo de la vía por parte del vehículo",
    "factores_contribuyentes": ["Señalización incompleta"]
  },
  "conclusiones": [
    "El arrollamiento tiene su origen en la invasión del gálibo..."
  ],
  "recomendaciones": [
    "No se establecen recomendaciones."
  ],
  "tags": ["paso_a_nivel", "atropello", "muerto"]
}
```

### Campos de severidad (RD 929/2022)

| Severidad | Definición |
|-----------|------------|
| **muy grave** | Al menos 1 fallecido o lesiones muy graves |
| **grave** | Lesiones graves sin fallecidos |
| **menor** | Sin fallecidos ni lesiones graves |

### Tipologías normalizadas (18 categorías)

Según RD 929/2022:

1. Arrollamiento de persona por tren
2. Arrollamiento de vehículo por tren
3. Colisión entre trenes
4. Colisión con obstáculo en vía
5. Descarrilamiento
6. Incendio
7. Atropello en paso a nivel
8. Caída de pasajero
9. Caída de mercancía
10. Daño intencional
11. Avería en infraestructura
12. Avería en material rodante
13. Conato de colisión
14. Otros sucesos
15. Accidente ferroviario (genérico)
16. Incidente ferroviario
17. Suceso de seguridad
18. No clasificado

---

## 🔧 Scripts de procesamiento

### parse_all.py / parse_reports_v2.py

Parser principal de PDFs. Extrae texto usando PyMuPDF y detecta automáticamente 4 formatos históricos:

- **2007-2008**: Formato libre (pre-RD 810/2007)
- **2009-2013**: Estandarizado secciones 1-5 (RD 810/2007)
- **2014-2025**: Estandarizado secciones 0-6 (RD 623/2014)

**Salida:** JSONs individuales en `ciaf-data/data/individual/`

### cruce_datos.py

Cruza datos del Excel con los JSONs individuales. Corrige:
- Severidad (fatal → muy grave)
- Tipología (normalizada a 18 categorías)
- PKs y tramos

**Entrada:** Excel + JSONs individuales
**Salida:** JSONs corregidos en `ciaf-data/data/individual/`

### geocode_visor.py / geocode_all.py

Geolocaliza estaciones usando:
1. DB de coordenadas de estaciones (355 entradas)
2. Nominatim (OpenStreetMap) como fallback
3. ADIF LTV FeatureServer para interpolación por PK

**Salida:** Coordenadas lat/lng en `data/reports/YYYY.json`

### fix_visor_data.py / fix_visor_complete.py

Correcciones masivas de calidad:
- Nombres de estación (sin mayúsculas, sin puntos finales)
- Provincias verificadas
- Coordenadas desde JSONs individuales

### build-station-map.py

Construye la base de datos de coordenadas de estaciones a partir de:
- Nombres extraídos de los informes
- Coordenadas de ADIF LTV FeatureServer
- Nominatim como fallback

### download-tracks.py

Descarga la red ferroviaria española de OpenStreetMap vía Overpass API. Genera `data/train-tracks.geojson`.

### generate_index.py

Genera `data/index.json` consolidado a partir de todos los `YYYY.json`.

### sync.py

Sincroniza con la web de la CIAF:
1. Detecta nuevos informes
2. Descarga PDFs faltantes
3. Ejecuta el parser

---

## 📈 Dashboard

El dashboard incluye:

- **KPIs**: total informes, víctimas, evolución temporal
- **Gráficos**: distribución por tipo, causa, empresa
- **Tabla**: todos los informes con filtros y búsqueda
- **Memorias**: comparación año a año

### Capas del mapa

| Capa | Descripción | Fuente |
|------|-------------|--------|
| IGN Gris | Mapa base topográfico | IGN (CC BY 4.0) |
| Vías de tren | Red ferroviaria | OpenStreetMap (ODbL) |
| Informes | Puntos de accidentes | CIAF (datos públicos) |

---

## 🔧 Mantenimiento

### Añadir nuevos informes

Cuando la CIAF publique nuevos informes:

```bash
# 1. Sincronizar PDFs
python3 scripts/sync.py

# 2. Parsear nuevos PDFs
python3 scripts/parse_all.py

# 3. Si hay Excel actualizado, cruzar datos
python3 scripts/cruce_datos.py

# 4. Geolocalizar nuevos
python3 scripts/geocode_visor.py

# 5. Generar index
python3 scripts/generate_index.py

# 6. Subir a GitHub
git add -A && git commit -m "feat: nuevos informes CIAF" && git push
```

### Añadir un informe manualmente

1. Colocar el PDF en `pdfs/YYYY/`
2. Ejecutar `python3 scripts/parse_all.py`
3. Verificar que se generó en `ciaf-data/data/individual/`
4. Ejecutar `python3 scripts/cruce_datos.py` si hay Excel
5. Ejecutar `python3 scripts/geocode_visor.py`
6. Verificar en `data/reports/YYYY.json`

### Verificar calidad de datos

```bash
# Verificar un año específico
python3 -c "
import json
with open('data/reports/2024.json') as f:
    reports = json.load(f)
for r in reports:
    print(f\"{r['id']}: {r['tipo']} - {r['ubicacion'].get('estacion', 'N/A')}\")
"
```

### Errores de procesamiento

Si hay errores, se guardan en `data/parse_errors.json`. Revisar este archivo para detectar problemas.

---

## 🗺️ Geolocalización

### Fuentes de coordenadas

1. **JSONs individuales** (extraídos del PDF): lat/lng cuando aparecen en el informe
2. **ADIF LTV FeatureServer**: Interpolación por PK (point kilometer) en vías de ADIF
3. **DB de estaciones** (355 entradas): Coordenadas manuales de estaciones conocidas
4. **Nominatim**: Fallback para estaciones no cubiertas

### Precisión

- **Alta** (~100m): Cuando el PDF incluye coordenadas GPS exactas
- **Media** (~500m): Interpolación por PK en línea conocida
- **Baja** (~2km): Geocodificación por nombre de estación

---

## 📝 Normativa de referencia

El proyecto procesa informes según la normativa vigente:

| Normativa | Período | Efecto |
|-----------|---------|--------|
| Pre-RD 810/2007 | 2007-2008 | Formato libre |
| RD 810/2007 | 2009-2013 | Formato estandarizado (secciones 1-5) |
| RD 623/2014 | 2014-2025 | Formato estandarizado (secciones 0-6) |
| **RD 929/2022** | Actual | Taxonomía de severidad (muy grave/grave/menor) |

---

## 🤝 Contribuir

Las mejoras son bienvenidas:

1. Fork el proyecto
2. Crear una rama para tu cambio
3. Hacer commit
4. Abrir un Pull Request

### Áreas de mejora

- [ ] Mejorar extracción de coordenadas GPS de PDFs
- [ ] Añadir más gráficos al dashboard
- [ ] Implementar búsqueda por texto completo
- [ ] Añadir filtros por rango de fechas
- [ ] Exportar datos a CSV/Excel
- [ ] Añadir datos de AEMET (condiciones meteorológicas)
- [ ] Integrar con API de ADIF para actualización automática

---

## 🐛 Conocimiento de errores

### Errores detectados y corregidos

1. **Cruce por número sin año**: El script `cruce_datos.py` original cruzaba por número de expediente sin year, causando que datos de un año se copiaran a otros (ej: 0050/2009 → 0050/2011)
2. **Severidad incorrecta**: Registros con fallecidos clasificados como "grave" en vez de "muy grave"
3. **Coordenadas erróneas**: La interpolación por PK no siempre era precisa; los JSONs individuales tienen mejores coordenadas
4. **Nombres de estación**: Muchos tenían formato inconsistente (mayúsculas, puntos finales, provincias incluidas)

### Solución aplicada

- Usar JSONs individuales como fuente de verdad para título, conclusiones, coordenadas
- Usar Excel como fuente de verdad para provincia, PK, tramo
- Normalizar severidad según RD 929/2022
- Limpiar nombres de estación

---

## 📄 Licencia

Los datos son de **dominio público** (informes de accidentes ferroviarios del gobierno de España).

El código está bajo la licencia **MIT**.

Las imágenes del mapa son de **OpenStreetMap** (ODbL) y **IGN** (CC BY 4.0).

---

## 📚 Referencias

- [CIAF - Comisión de Investigación de Accidentes Ferroviarios](https://www.transportes.gob.es/organos-colegiados/ciaf)
- [Informes finales de sucesos investigados](https://www.transportes.gob.es/organos-colegiados/ciaf/informes-finales-de-sucesos-investigados)
- [Memorias anuales](https://www.transportes.gob.es/organos-colegiados/ciaf/memorias-anuales/memoriasanuales)
- [RD 623/2014](https://www.transportes.gob.es/recursos_mfom/comodin/recursos/4-rd_623-2014.pdf) (BOE-A-2014-7651)
- [RD 929/2022](https://www.boe.es/doue/2022/217/B00031-00043.pdf) - Taxonomía de severidad

---

## 🏗️ Hecho con

- [Leaflet](https://leafletjs.com/) — Mapas interactivos
- [Chart.js](https://www.chartjs.org/) — Gráficos
- [PyMuPDF](https://pymupdf.readthedocs.io/) — Extracción de texto de PDFs
- [Kaizen Design System](https://github.com/Ntizar/kaizen-design-system) — CSS corporativo
- [IGN WMTS](https://www.ign.es/wmts/ign-base) — Mapas base de España
- [OpenRailwayMap](https://www.openrailwaymap.org/) — Vías de tren
- [ADIF LTV](https://servicios1.adif.es/LTV_CONTENT_LTVPWGS84/) — Coordenadas de vías

---

*Hecho con ❤️ por David Antizar*
