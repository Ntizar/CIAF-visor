# 🔗 Informe de Cruce de Datos CIAF
**Fecha:** 2026-06-29 11:24
**Excel:** 260218_Base_Datos_CIAF_1.xlsx
**JSONs:** 270 archivos en /root/workspace/ciaf-data/data/individual

---

## 📊 Resumen del Cruce

| Métrica | Valor |
|---------|-------|
| Expedientes Excel | 278 |
| JSONs cargados | 270 |
| **Emparejados** | **246** |
| Excel sin JSON | 32 |
| JSON sin Excel | 6 |

## 🔧 Correcciones Aplicadas

| Corrección | Cantidad |
|------------|----------|
| Severidad corregida | 95 |
| Tipología corregida/anadida | 0 |
| PK normalizados | 207 |
| Campos adicionados | 249 |

## 📋 Detalle de Cambios por Informe

### Cambios por campo:
- **severidad:** 95 informes

### Muestra de cambios (primeros 20):

**1/2008:**
  - severidad: grave → muy grave

**1/2009:**
  - severidad: grave → muy grave

**2/2008:**
  - severidad: grave → muy grave

**2/2009:**
  - severidad: grave → muy grave

**2/2010:**
  - severidad: grave → muy grave

**3/2008:**
  - severidad: grave → muy grave

**3/2010:**
  - severidad: grave → muy grave

**4/2008:**
  - severidad: menor → muy grave

**4/2009:**
  - severidad: grave → muy grave

**5/2009:**
  - severidad: grave → muy grave

**6/2008:**
  - severidad: menor → muy grave

**7/2009:**
  - severidad: grave → muy grave

**9/2008:**
  - severidad: grave → muy grave

**10/2008:**
  - severidad: grave → muy grave

**12/2008:**
  - severidad: grave → muy grave

**12/2009:**
  - severidad: grave → muy grave

**12/2017:**
  - severidad: grave → muy grave

**13/2008:**
  - severidad: grave → muy grave

**13/2009:**
  - severidad: menor → grave

**14/2008:**
  - severidad: grave → muy grave


## ⚠️ Expedientes sin JSON (32)

- 11/2023
- 12/2019
- 19/2008
- 19/2020
- 20/2008
- 28/2012
- 28/2019
- 3/2011
- 30/2015
- 31/2008
- 34/2012
- 34/2020
- 38/2021
- 39/2015
- 4/2020
- 43/2015
- 43/2023
- 46/2022
- 48/2022
- 49/2015
- 58/2015
- 59/2021
- 6/2012
- 64/2008
- 64/2021
- 64/2024
- 7/2012
- 70/2022
- 71/2012
- 71/2021
- 8/2021
- 9/2021

## ⚠️ JSONs sin Excel (6)

- 260526-241029-if-sf_ciaf.json (id: 111-2024)
- IF090512261212CIAF.json (id: IF-090512-261212-CIAF)
- IF160111200911CIAF.json (id: IF-160111-200911-CIAF)
- IF180412261212CIAF.json (id: IF-180412-261212-TI)
- IF190112271112CIAF.json (id: IF-190112-271112-CIAF)
- IF291012290113CIAF.json (id: IF-291012-290113-CIAF)

## 📊 Distribución de Severidad Corregida

- **menor:** 148 informes
- **muy grave:** 94 informes
- **grave:** 4 informes


## 📊 Distribución de Tipología Normalizada

- **descarrilamiento:** 64 informes
- **otro_accidente:** 50 informes
- **conato_colision:** 34 informes
- **arrollamiento_persona:** 26 informes
- **otro_incidente:** 14 informes
- **arrollamiento:** 10 informes
- **arrollamiento_vehiculo:** 8 informes
- **rebase_senal:** 7 informes
- **colision_alcance:** 7 informes
- **colision_trenes:** 5 informes
- **arrollamiento_ciclista:** 2 informes
- **colision_obstaculo:** 2 informes
- **arrollamiento_obstaculo:** 2 informes
- **escape_material:** 2 informes
- **colision:** 2 informes
- **incendio:** 2 informes
- **colision_rocas:** 2 informes
- **colision_vehiculo:** 1 informes
- **colision_lateral:** 1 informes
- **colision_descarrilamiento:** 1 informes
- **colision_infraestructura:** 1 informes
- **fallo_seguridad:** 1 informes
- **rotura_eje:** 1 informes
- **incidente_operacional:** 1 informes


## 🗂️ Estructura de Salida

```
/root/workspace/ciaf-data/data/individual_corrected/
├── 246 JSONs corregidos
└── (mismos nombres que originales)
```

## ⚠️ Próximos Pasos

1. **Geocodificación por PK:** Implementar interpolación usando WFS Tramificación ADIF
2. **Re-parseo de PDFs faltantes:** Para los 32 informes sin JSON
3. **Validación cruzada:** Verificar que las víctimas del Excel coinciden con las del JSON

---
*Generado automáticamente por CIAF Cross-Reference Tool*
