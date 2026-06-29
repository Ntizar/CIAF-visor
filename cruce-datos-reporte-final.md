# 🔗 Informe de Cruce de Datos CIAF — Versión Final
**Fecha:** 2026-06-29 11:30
**Excel:** 260218_Base_Datos_CIAF_1.xlsx (548 filas, 278 expedientes únicos)
**JSONs:** 270 archivos en `/root/workspace/ciaf-data/data/individual`

---

## 📊 Resumen del Cruce

| Métrica | Antes | Después |
|---------|-------|---------|
| JSONs con severidad correcta | 175 (65%) | 268 (99%) |
| JSONs con tipología detallada | 0 (0%) | 268 (99%) |
| JSONs con PK normalizado | 63 (23%) | 268 (99%) |
| JSONs geolocalizados | 8 (3%) | 193 (71%) |
| JSONs con causa directa | 0 (0%) | 268 (99%) |
| JSONs con recomendaciones Excel | 0 (0%) | 268 (99%) |

## 🔧 Correcciones Aplicadas

### Severidad (RD 929/2022)
- **95 informes** corregidos de "grave"/"menor" → "muy grave" (tenían fallecidos)
- **3 informes** corregidos de "menor" → "grave" (tenían heridos graves)
- Distribución final: 94 muy grave, 4 grave, 148 menor

### Tipología Normalizada
De solo "accidente"/"incidente" a categorías detalladas:
- descarrilamiento: 64
- otro_accidente: 50
- conato_colision: 34
- arrollamiento_persona: 26
- otro_incidente: 14
- arrollamiento: 10
- arrollamiento_vehiculo: 8
- colision_alcance: 7
- rebase_senal: 7
- colision_trenes: 5
- (y 13 categorías más)

### PK Normalizados
- 207 PKs convertidos de formato "P.K. 429,825" → "429+825"
- PK numérico añadido para cálculos

### Geocodificación por PK + Línea
- **185 informes** geocodificados usando interpolación LTV (FeatureServer ADIF)
- **8 informes** ya tenían coordenadas reales
- **75 informes** sin cobertura LTV (líneas regionales/cortas)
- **2 informes** sin datos de PK

### Campos Enriquecidos
- `causa_directa` — del Excel
- `factores_contribuyentes` — del Excel
- `infraestructura` — del Excel
- `tiempo_afeccion` — del Excel
- `recomendaciones_excel` — array con texto y destinatario
- `_cross_ref` — metadatos de cruce (expediente, timestamp, cambios)

## 📁 Estructura de Salida

```
/root/workspace/ciaf-data/data/individual/
├── 270 JSONs (268 corregidos + 2 sin Excel)
├── Backup: individual_backup_20260629/
└── Copia temporal: individual_corrected/

/root/workspace/CIAF-visor/
├── cruce-datos-reporte.md (este informe)
├── ltv_lookup.json (datos LTV para geocodificación)
└── scripts/cruce_datos.py (herramienta de cruce)
```

## ⚠️ Pendiente

1. **75 informes sin geocodificación** — líneas sin cobertura LTV. Opciones:
   - Geocodificar por nombre de estación con Nominatim
   - Usar WFS Tramificación para interpolar geometría
2. **10 informes del Excel sin JSON** — PDFs que no se han parseado
3. **2 JSONs sin Excel** — informes muy nuevos (41/2025, 111/2024)

---
*Generado automáticamente por CIAF Cross-Reference Tool*
