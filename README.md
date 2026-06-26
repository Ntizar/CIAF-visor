# CIAF Visor — Visor integral de informes de accidentes ferroviarios

![CIAF Visor](https://img.shields.io/badge/CIAF-Visor-v1.0-blue)
![Datos](https://img.shields.io/badge/Datos-277_informes-green)
![Memorias](https://img.shields.io/badge/Memorias-17_anuales-orange)

Visor interactivo de todos los informes de accidentes ferroviarios de la **Comisión de Investigación de Accidentes Ferroviarios (CIAF)** de España, desde 2007 hasta 2025.

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

| Fuente | Cantidad | Período |
|--------|----------|---------|
| Informes de accidentes | 277 PDFs | 2007-2025 |
| Memorias anuales | 17 PDFs | 2008-2024 |
| Normativa | 7 PDFs | Varios |

### Cómo funciona

1. Los PDFs originales se procesan con PyMuPDF para extraer texto
2. Un parser inteligente detecta el formato (3 formatos diferentes según la época)
3. Se genera JSON estructurado por año con todos los campos normalizados
4. El frontend carga los JSONs y muestra un visor interactivo con Leaflet + Chart.js

---

## 🗂️ Estructura del proyecto

```
CIAF-visor/
├── data/                          # Datos procesados (JSON)
│   ├── index.json                 # Índice global de todos los informes
│   ├── relations.json             # Relaciones entre entidades e informes
│   ├── train-tracks.geojson       # Vías de tren de España (OSM)
│   ├── reports/                   # Informes por año
│   │   ├── 2007.json
│   │   ├── 2008.json
│   │   └── ...
│   ├── memorias/                  # Memorias anuales
│   │   ├── index.json
│   │   ├── 2008.json
│   │   └── ...
│   └── images/                    # Imágenes extraídas de PDFs
│       ├── 2007/
│       └── ...
├── pdfs/                          # PDFs originales (no subir a GitHub)
│   ├── 2007/ ... 2025/
│   ├── memorias/
│   └── normativa/
├── frontend/                      # Frontend web
│   ├── index.html                 # Visor principal
│   └── css/
│       └── kaizen.css             # Kaizen Design System
├── scripts/                       # Scripts de procesamiento
│   ├── parse_all.py               # Parser principal de informes
│   ├── download-tracks.py         # Descarga vías de tren (Overpass)
│   └── sync.py                    # Sincronización con web CIAF
├── ARQUITECTURA.md                # Documentación técnica
└── README.md                      # Este archivo
```

---

## 🚀 Instalación y uso

### Requisitos

- Python 3.8+
- pip

### Dependencias

```bash
pip install PyMuPDF
```

### Procesar informes

```bash
# Procesar todos los PDFs (tarda ~15-30 minutos)
python3 scripts/parse_all.py

# Descargar vías de tren de OpenStreetMap
python3 scripts/download-tracks.py

# Sincronizar con la web CIAF (detecta nuevos informes)
python3 scripts/sync.py
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

## 📊 Formatos de informe

La CIAF ha usado 3 formatos diferentes a lo largo de los años:

| Período | Normativa | Formato |
|---------|-----------|---------|
| 2007-2008 | Pre-RD 810/2007 | Libre (Informe definitivo/Final) |
| 2009-2013 | RD 810/2007 | Estandarizado (secciones 1-5) |
| 2014-2025 | RD 623/2014 | Estandarizado (secciones 0-6) |

El parser (`parse_all.py`) detecta automáticamente el formato y extrae los campos comunes:

- **Ubicación**: estación, provincia, coordenadas GPS
- **Tipo de suceso**: descarrilamiento, colisión, incendio, atropello, etc.
- **Análisis**: resumen, factores humanos, infraestructura, material rodante
- **Conclusiones** y **recomendaciones** (con implementador y destinatarios)
- **Consecuencias**: víctimas mortales, heridos, daños materiales

---

## 🔧 Mantenimiento

### Actualizar con nuevos informes

Cuando la CIAF publique nuevos informes:

```bash
python3 scripts/sync.py
```

Este script:
1. Comprueba la web de la CIAF por nuevos PDFs
2. Descarga los que falten
3. Ejecuta el parser
4. Regenera los JSONs

### Añadir un informe manualmente

1. Colocar el PDF en `pdfs/YYYY/`
2. Ejecutar `python3 scripts/parse_all.py`
3. Verificar que el JSON se generó correctamente en `data/reports/YYYY.json`

### Verificar calidad de datos

Los JSONs generados incluyen validación básica. Para revisión manual:

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

## 🗺️ Mapa de vías de tren

Las vías de tren se descargan de OpenStreetMap vía Overpass API:

```bash
python3 scripts/download-tracks.py
```

El archivo `data/train-tracks.geojson` incluye:
- Líneas principales (azul)
- Alta velocidad (rojo)
- Cercanías (verde)
- Mercancías (gris)

### Capas del mapa

| Capa | Descripción | Fuente |
|------|-------------|--------|
| IGN Gris | Mapa base topográfico | IGN (CC BY 4.0) |
| Vías de tren | Red ferroviaria | OpenStreetMap (ODbL) |
| Informes | Puntos de accidentes | CIAF (datos públicos) |

---

## 📈 Dashboard

El dashboard incluye:

- **KPIs**: total informes, víctimas, evolución temporal
- **Gráficos**: distribución por tipo, causa, empresa
- **Tabla**: todos los informes con filtros y búsqueda
- **Memorias**: comparación año a año

---

## 📝 Normativa

El proyecto procesa 7 documentos normativos:

1. Directiva UE 2016/798
2. Reglamento Ejecución UE 2020/572
3. Ley 38/2015 de investigación ferroviaria
4. **RD 623/2014** (define la estructura de informes)
5. RD 2387/2004 de investigación de accidentes
6. RD 664/2015 de condiciones de seguridad
7. RD 929/2020 de Agencia de Seguridad Ferroviaria

---

## 🤝 Contribuir

Las mejoras son bienvenidas:

1. Fork el proyecto
2. Crear una rama para tu cambio
3. Hacer commit
4. Abrir un Pull Request

### Áreas de mejora

- [ ] Mejorar extracción de coordenadas GPS
- [ ] Añadir más gráficos al dashboard
- [ ] Implementar búsqueda por texto completo
- [ ] Añadir filtros por rango de fechas
- [ ] Exportar datos a CSV/Excel

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

---

## 🏗️ Hecho con

- [Leaflet](https://leafletjs.com/) — Mapas interactivos
- [Chart.js](https://www.chartjs.org/) — Gráficos
- [PyMuPDF](https://pymupdf.readthedocs.io/) — Extracción de texto de PDFs
- [Kaizen Design System](https://github.com/Ntizar/kaizen-design-system) — CSS corporativo
- [IGN WMTS](https://www.ign.es/wmts/ign-base) — Mapas base de España
- [OpenRailwayMap](https://www.openrailwaymap.org/) — Vías de tren

---

*Hecho con ❤️ por David Antizar*
