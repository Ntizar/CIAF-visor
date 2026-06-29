# 🔍 Auditoría CIAF — Informe Completo
**Fecha:** 2026-06-29 11:08
**Fuentes:** Excel Base Datos CIAF (548 filas, 278 expedientes únicos) vs JSONs (270 archivos)

---

## 1. 📊 CUBIERTA DE DATOS

### 1.1 Volumen general
| Fuente | Cantidad |
|--------|----------|
| PDFs totales (CIAF/) | 294 |
| PDFs informes (años) | 270 |
| PDFs memorias | 17 |
| PDFs normativa | 7 |
| JSONs en ciaf-data/ | 270 |
| Expedientes únicos Excel | 278 |
| Filas Excel (con rec. múltiples) | 548 |

### 1.2 Informes FALTANTES en JSONs (8 informes sin JSON)
| Año | Excel | JSON | Faltan |
|-----|-------|------|--------|
| 2007 | 4 | 4 | — |
| 2008 | 57 | 53 | 4 ⚠️ |
| 2009 | 43 | 43 | — |
| 2010 | 28 | 28 | — |
| 2011 | 24 | 24 | — |
| 2012 | 23 | 22 | 1 ⚠️ |
| 2013 | 23 | 23 | — |
| 2014 | 14 | 14 | — |
| 2015 | 15 | 10 | 5 ⚠️ |
| 2016 | 11 | 11 | — |
| 2017 | 12 | 12 | — |
| 2018 | 2 | 2 | — |
| 2019 | 3 | 3 | — |
| 2020 | 3 | 3 | — |
| 2021 | 6 | 6 | — |
| 2022 | 5 | 5 | — |
| 2023 | 3 | 3 | — |
| 2024 | 2 | 3 | -1 ➕ |
| 2025 | 0 | 1 | -1 ➕ |

### 1.3 JSONs EXTRAS (en JSON pero no en Excel)
| Archivo JSON | Año | ID | Estación |
|-------------|-----|-----|----------|
| 020_2010.json | 2010 | IF-080410-281210-CIAF | Silla |
| 109IF010109190509CIAF.json | 2009 | IF-010109-190509-CIAF | Estación de Sitges |
| 151022140811IFCIAF.json | 2014 | IF-42-2014 | Pancorbo |
| 152011.json | 2011 | IF-070311-290512-CIAF | Flaçà |
| 170627151005ifciafsn.json | 2015 | IF-46-2015 | Estación de Tardienta |
| 180525160930ifsn_ciaf.json | 2016 | IF-43-2016 | Lena |
| 181219-170523-if-sn_ciaf.json | 2017 | IF-25-2017 | Urcabustaiz |
| 200421-180701-if-sn_ciaf_.json | 2018 | 200421-180701-IF_CIAF | Pedralba |
| 2025-41-0522-if.json | 2025 | IF 41-2025 | Cortes de Navarra |
| 230209140709CIAF.json | 2009 | IF-230209-140709-CIAF |  |
| 231008140709CIAF.json | 2008 | IF-231008-140709-CIAF | Villalba de Guadarrama |
| 240309140709CIAF.json | 2009 | IF-240309-140709-CIAF | Estación de Algemesí |
| 241008140709CIAF.json | 2008 | IF-241008-140709-CIAF | Moncófar |
| 260526-241029-if-sf_ciaf.json | 2024 | 111-2024 | Álora |
| 412.json | 2012 | IF-120112-250912-CIAF | Estación de San Claudio |
| 4411.json | 2011 | IF-130711-250912-CIAF | Caparrates |
| 492011.json | 2011 | IF-261011-290512-CIAF | Sant Pol de Mar |
| 509IF220109190509CIAF.json | 2009 | IF-220109-190509-CIAF | Estación de Gavá |
| 512011.json | 2011 | IF-051111-290512-CIAF | Barcelona |
| 6311.json | 2011 | IF-271211-250912-CIAF | Zaragoza |
| IF010611310112CIAF.json | 2011 | IF-010611-310112-CIAF | Trasona |
| IF010612280513CIAF.json | 2012 | IF-010612-280513-CIAF | Falset |
| IF010712280513CIAF.json | 2012 | IF-010712-280513-CIAF | Zaragoza |
| IF020209221209CIAF.json | 2009 | IF-020209-221209-CIAF | Zegama |
| IF021008281108CIAF.json | 2008 | IF-021008-281108-CIAF | Viaducto sobre el río Esla entre Cistierna y León |
| IF021108240209CIAF.json | 2008 | IF-021108-240209-CIAF |  |
| IF030608300908CIAF.json | 2008 | IF-030608-300908-CIAF | Paso a nivel tipo P, entre las estaciones de El Priorato y Lora del Río |
| IF031108240209CIAF.json | 2008 | IF-031108-240209-CIAF | Cardedeu |
| IF040111200911CIAF.json | 2011 | IF-040011-200911-CIAF | Zaragoza |
| IF040613230914CIAF.json | 2013 | IF-040613-230914-CIAF | Sant Sadurní d’Anoia |
| IF050411280212CIAF.json | 2011 | IF-050411-280212-CIAF | Rubí |
| IF050609221209CIAF.json | 2009 | IF-050609-221209-CIAF | Maçanet de la Selva |
| IF050708181208CIAF.json | 2008 | IF-050708-181208-CIAF | Medina del Campo |
| IF050913270115CIAF.json | 2013 | IF-050913-270115-CIAF | Requejada |
| IF060508181208CIAF.json | 2008 | IF-060508-181208-CIAF | Estación de Fabara |
| IF060613281014CIAF.json | 2013 | IF-060613-281014-CIAF | Zaragoza |
| IF060709221209CIAF.json | 2009 | IF-060709-221209-CIAF | Ronda |
| IF061212170913CIAF.json | 2012 | IF-061212-170913-CIAF | Laviana |
| IF070313140714CIAF.json | 2013 | IF-070313-140714-CIAF | Viana de Cega |
| IF070413240315CIAF.json | 2013 | IF-070413-240315-CIAF | Almodóvar del Campo |
| IF081012250613CIAF.json | 2012 | IF-081012-250613-CIAF | Zuera |
| IF081108240209CIAF.json | 2008 | IF-081108-240209-CIAF |  |
| IF090113240614CIAF.json | 2013 | IF-090113-240614-CIAF | Villafranca de Córdoba |
| IF090212271112CIAF.json | 2012 | IF-090212-271112-CIAF | Mataró |
| IF090508300908CIAF.json | 2008 | IF-090508-300908-CIAF | Cetina |
| IF090512261212CIAF.json | 2012 | IF-090512-261212-CIAF | Astillero |
| IF090810_250211CIAF.json | 2010 | IF-090810-250211-CIAF | Cabezón de la Sal |
| IF091108240209CIAF.json | 2008 | IF-091108-240209-CIAF | Paso a nivel clase A, entre Almagro y el apeadero de El Campillo |
| IF100110280910CIAF.json | 2010 | IF-100110-280910-CIAF | Majarabique |
| IF100213240614CIAF.json | 2013 | IF-100213-240614-CIAF | Maliaño |
| IF100710290311CIAF.json | 2010 | IF-100710-290311-CIAF | Aracaldo |
| IF101108240209CIAF.json | 2008 | IF-101108-240209-CIAF | Paso a nivel clase C, en la población de Monforte de Lemos, carretera de Monforte a Neiras |
| IF110210280910CIAF.json | 2010 | IF-110210-280910-CIAF | Pinar de Las Rozas |
| IF110508281108CIAF.json | 2008 | IF-110508-281108-CIAF |  |
| IF110512290113CIAF.json | 2012 | IF-110512-290113-CIAF | Narón |
| IF110711270312CIAF.json | 2011 | IF-110711-270312-CIAF | Villanúa |
| IF110713251114CIAF1.json | 2013 | IF-110713-251114-CIAF | Lleida Pirineus |
| IF120312260213CIAF.json | 2012 | IF-120312-260213-CIAF | Estación de Socuéllamos |
| IF120813100215CIAF.json | 2013 | IF-120813-100215-CIAF | Salomó |
| IF121011260612CIAF.json | 2011 | IF-121011-260612-CIAF | Vilamalla |
| IF130508281008CIAF.json | 2008 | IF-130508-281008-CIAF | Entre el apeadero de Alegia y la estación de Tolosa, a la salida de un túnel en curva a la izquierda de radio 475 y 9,4 milésimas de pendiente ascendente en el sentido de la circulación, en las cercanías de la Ctra. Nacional I |
| IF130508300908CIAF.json | 2008 | IF-130508-300908-CIAF | paso entarimado del apeadero de Hernani Centro |
| IF131008240209CIAF.json | 2008 | IF-131008-240209-CIAF | La Encina |
| IF131208210409CIAF.json | 2008 | IF-131208-210409-CIAF | Vitoria |
| IF131208310309CIAF.json | 2008 | IF-131208-310309-CIAF | Calella |
| IF140508220708CIAF.json | 2008 | IF-140508-220708-CIAF |  |
| IF140610_310111CIAF.json | 2010 | IF-140610-310111-CIAF | Ortigueira |
| IF140710_250211CIAF.json | 2010 | IF-140710-250211-CIAF | Ribadeo |
| IF140813251114CIAF1.json | 2013 | IF-140813-251114-CIAF | Torralba |
| IF141008210409CIAF.json | 2008 | IF-141008-210409-CIAF | Leganés |
| IF150112221012CIAF.json | 2012 | IF-150112-221012-CIAF | Trubia |
| IF150612290413CIAF.json | 2012 | IF-150612-290413-CIAF | Arévalo |
| IF151008240209CIAF.json | 2008 | IF-151008-240209-CIAF |  |
| IF151211260612CIAF.json | 2011 | IF-151211-260612-CIAF | Valencia |
| IF160111200911CIAF.json | 2011 | IF-160111-200911-CIAF | Aguadulce |
| IF160311251011CIAF.json | 2011 | IF-160311-251011-CIAF | Olesa de Montserrat |
| IF160408300908CIAF.json | 2008 | IF-160408-300908-CIAF | Sant Feliú de Llobregat |
| IF160511280212CIAF.json | 2011 | IF-160511-280212-CIAF | Los Gavilanes |
| IF160708281108CIAF.json | 2008 | IF-160708-281108-CIAF | Valencia Nord |
| IF160710290311CIAF.json | 2010 | IF-160710-290311-CIAF | Valladolid |
| IF170409221209CIAF.json | 2009 | IF-170409-221209-CIAF | El Caleyo |
| IF180412261212CIAF.json | 2012 | IF-180412-261212-TI | Heras |
| IF180609221209CIAF.json | 2009 | IF-180609-221209-CIAF | Madrid Chamartín |
| IF180810290311CIAF.json | 2010 | IF-180810-290311-CIAF | Utrera |
| IF181008240209CIAF.json | 2008 | IF-181008-240209-CIAF |  |
| IF190112271112CIAF.json | 2012 | IF-190112-271112-CIAF | Barcelona |
| IF190712280513CIAF.json | 2012 | IF-190712-280513-CIAF | Montoro |
| IF191211240712CIAF.json | 2011 | IF-191211-240712-CIAF | Madrid Chamartín |
| IF200413250214CIAF.json | 2013 | IF-200413-250214-CIAF | Anoeta |
| IF200513140714CIAF.json | 2013 | IF-200513-140714-CIAF | Almendralejo |
| IF200711260612CIAF.json | 2011 | IF-200711-260612-CIAF | Bargas |
| IF200913230914CIAF.json | 2013 | IF-200913-230914-CIAF | Barcelona Sants |
| IF201008240209CIAF.json | 2008 | IF-201008-240209-CIAF | Santa María de Huerta |
| IF201208210409CIAF.json | 2008 | IF-201208-210409-CIAF | Salou |
| IF210308220708CIAF.json | 2008 | IF-210308-220708-CIAF |  |
| IF210612260313CIAF.json | 2012 | IF-210612-260313-CIAF | Plasencia de Jalón |
| IF211212250613CIAF.json | 2012 | IF-211212-250613-CIAF | Valencia-Font de Sant Lluis |
| IF220408220708CIAF.json | 2008 | IF-220408-220708-CIAF | Zorrotza |
| IF220608240209CIAF.json | 2008 | IF-220608-240209-CIAF | P.K. 149,950 de la línea 200 Madrid-Barcelona, junto a un centro de ocio denominado Imperial Drink y su aparcamiento. |
| IF220609221209CIAF.json | 2009 | IF-220609-221209-CIAF | Piloña |
| IF221108240209CIAF.json | 2008 | IF-221108-240209-CIAF |  |
| IF230114270115CIAF.json | 2014 | IF-230114-270115-CIAF | Fuentebureba |
| IF230411271211CIAF.json | 2011 | IF-230411-271211-CIAF | L’Hospitalet de Llobregat |
| IF230512260213CIAF.json | 2012 | IF-230512-260213-CIAF | Tocón-Montefrío |
| IF230610_310111CIAF.json | 2010 | IF-230610-310111-CIAF | Apeadero de Platja de Castelldefels |
| IF240508300908CIAF.json | 2008 | IF-240508-300908-CIAF | Villena |
| IF240511270312CIAF.json | 2011 | IF-240511-270312-CIAF | Villamanín |
| IF240608281108CIAF.json | 2008 | IF-240608-281108-CIAF | Inicio del viaducto sobre la Riera D'Argentona |
| IF240713200514CIAF.json | 2013 | IF-240713-200514-CIAF | Santiago de Compostela |
| IF260213291013CIAF.json | 2013 | IF-260213-291013-CIAF | Coslada |
| IF260313240614CIAF1.json | 2013 | IF-260313-240614-CIAF | Urda |
| IF260412290113CIAF.json | 2012 | IF-260412-290113-CIAF | Río Huerva |
| IF260513140714CIAF.json | 2013 | IF-260513-140714-CIAF | Sevilla Santa Justa |
| IF260609221209CIAF.json | 2009 | IF-260609-221209-CIAF | Estación de Aluche |
| IF260610_310111CIAF.json | 2010 | IF-260610-310111-CIAF | Vitoria – Gasteiz |
| IF260913281014CIAF.json | 2013 | IF-260913-281014-CIAF | Valladolid |
| IF270213291013CIAF.json | 2013 | IF-270213-291013-CIAF | Madrid |
| IF270508300908CIAF.json | 2008 | IF-270508-300908-CIAF | Paso a nivel tipo B, entre las estaciones de Santa Cruz de la Zarza y Ocaña |
| IF270811240712CIAF.json | 2011 | IF-270811-240712-CIAF | Granollers - Centre |
| IF271011240712CIAF.json | 2011 | IF-271011-240712-CIAF | Astillero |
| IF271013231214CIAF.json | 2013 | IF-271013-231214-CIAF | Sant Andreu Arenal |
| IF271013251114CIAF1.json | 2013 | IF-271013-251114-CIAF | Zalla |
| IF280411271211CIAF.json | 2011 | IF-280411-271211-CIAF | Barcelona |
| IF280413200514CIAF.json | 2013 | IF-280413-200514-CIAF | Vegaquemada |
| IF280908181208CIAF.json | 2008 | IF-280908-181208-CIAF |  |
| IF290610_250211CIAF.json | 2010 | IF-290610-250211-CIAF | Sant Andreu Arenal |
| IF290808181208CIAF.json | 2008 | IF-290808-181208-CIAF |  |
| IF291012290113CIAF.json | 2012 | IF-291012-290113-CIAF | Miguelturra |
| IF310113291013CIAF.json | 2013 | IF-310113-291013-CIAF | Val de San Vicente |
| IF_011209_230310_CIAF.json | 2009 | IF-011209-230310-CIAF | O Porriño |
| IF_081009_230210_CIAF.json | 2009 | IF-081009-230210-CIAF | Monforte de Lemos |
| IF_110310_261010CIAF.json | 2010 | IF-110310-261010-CIAF | Villaquilambre |
| IF_280809_230210_CIAF.json | 2009 | IF-280809-230210-CIAF | El Rebollar |
| IF_280909_230210_CIAF.json | 2009 | IF-280909-230210-CIAF | Cartagena |
| IF_310809_060410_CIAF.json | 2009 | IF-310809-060410-CIAF | San Cristóbal Industrial |
| IF_N_62_CIAF.json | 2009 | IF-131209-270410-CIAF | Orbita |

---

## 2. 🏷️ TAXONOMÍA DE SEVERIDAD (RD 929/2022 / Dir. UE 2016/798)

### 2.1 Clasificación oficial según normativa
La normativa europea (Directiva 2016/798) y española definen:

**Accidentes:**
- **Muy grave:** Fallecimiento de una o más personas, o lesiones graves a una o más personas, o daños materiales importantes que requieran reparación importante del material rodante o de la infraestructura
- **Grave:** No clasificable como "muy grave" pero con fallecimiento o lesiones graves, o evacuación de viajeros, o daños significativos
- **Menor:** Otros accidentes con material rodante en movimiento

**Incidentes:**
- **Incidente grave:** Evento con alto potencial de riesgo de accidente
- **Incidente menor:** Otros eventos

### 2.2 Severidad derivada del Excel (según datos de víctimas)
- **Muy grave (fatal):** 101 expedientes
- **Grave:** 5 expedientes
- **Menor:** 172 expedientes

### 2.3 Severidad ACTUAL en JSONs
- **menor:** 178 informes
- **grave:** 92 informes

### 2.4 ⚠️ PROBLEMA CRÍTICO: Subcategorización de gravedad
Los JSONs SOLO tienen 2 valores de gravedad: "menor" (178) y "grave" (92).
**FALTA la categoría "muy grave"** que debería existir para informes con víctimas mortales.

Según el Excel, hay 101 informes con víctimas mortales que DEBERÍAN ser "muy grave".

### 2.5 Tipología de suceso — Excel vs JSONs

**Excel: 57 valores únicos (muy granular, inconsistente)**

| [132] Descarrilamiento |
| [ 84] Accidente ferroviario |
| [ 54] Conato de colisión |
| [ 35] Arrollamiento de persona |
| [ 30] Incidente ferroviario |
| [ 23] Incidente operacional |
| [ 17] Colisión por alcance |
| [ 16] Arrollamiento |
| [  9] Colisión |
| [  9] Accidente grave por descarrilamiento |
| [  9] Descarrilamiento de tren |
| [  8] Rebase de señal |
| [  7] Incendio de material rodante |
| [  7] colisión frontal |
| [  7] Arrollamiento de vehículo por tren |
| [  6] Rebase indebido de señal |
| [  6] Incidente Operacional - Retroceso no autorizado |
| [  5] Fallo de señalización |
| [  5] Colisión con desprendimiento de rocas |
| [  4] Fallo en las instalaciones de seguridad |
| [  4] descarrilamiento |
| [  4] Colisión de trenes |
| [  4] Incidente operacional con riesgo de colisión |
| [  3] Colisión entre trenes |
| [  3] Rebase de señal en rojo |
| [  3] Colisión lateral |
| [  3] Escape de material |
| [  3] Rotura de eje en tren de viajeros |
| [  3] Fallo de cargamento |
| [  3] Escape de tren a la deriva |
| [  3] Descarrilamiento por escape de material |
| [  2] Arrollamiento de ciclista |
| [  2] Colisión entre tren y vehículo de carretera |
| [  2] Colisión de tren |
| [  2] Arrollamiento de un vehículo por tren |
| [  2] Colisión de tren con señal y maquinaria en vía |
| [  2] Arrollamiento de personas |
| [  2] Arrollamiento de peatón |
| [  2] Conato de incendio |
| [  2] Incendio en locomotora |
| [  2] Rebase de señal y deriva de locomotora |
| [  2] Colisión frontal de trenes |
| [  2] Incendio en tren |
| [  2] Accidente en paso a nivel |
| [  1] Colisión con obstáculos en la vía |
| [  1] Arrollamiento de obstáculo |
| [  1] Arrollamiento de obstáculo y descarrilamiento |
| [  1] Conato de colisión entre trenes |
| [  1] Colisión y descarrilamiento |
| [  1] Conato de colisión por rebase de señal |
| [  1] Colisión con obstáculo en la vía |
| [  1] Arrollamiento de barra de carril |
| [  1] Conato de colisión por alcance |
| [  1] Conato de colisión y descarrilamiento |
| [  1] Rebase de señal de parada |
| [  1] Arrollamiento de motocicleta por tren |
| [  1] Colisión con roca |

**JSONs: 7 valores únicos (simplificado en exceso)**

| [134] accidente |
| [ 71] incidente |
| [ 51] descarrilamiento |
| [  9] colisión |
| [  3] colisión por alcance |
| [  1] colisión con obstáculo y descarrilamiento |
| [  1] arrollamiento |

### 2.6 ⚠️ PROBLEMA CRÍTICO: Tipología incompleta en JSONs
El Excel tiene una taxonomía rica con 58 categorías de tipo_suceso.
Los JSONs reducen todo a 7 categorías genéricas (accidente, incidente, descarrilamiento, colisión, etc.).
**Se pierde información crucial** como: conato de colisión, rebase de señal, incendio, fallo de señalización, etc.

### 2.7 Propuesta de taxonomía normalizada (RD 929/2022)
Basándonos en la normativa y los datos del Excel, se propone:

**Categoría principal (tipo):**
1. `accidente_muy_grave` — Con víctimas mortales
2. `accidente_grave` — Con heridos graves
3. `accidente_menor` — Sin víctimas o solo leves
4. `incidente_grave` — Alto potencial de riesgo
5. `incidente_menor` — Otros eventos

**Tipología detallada (tipo_suceso) — normalizada:**
1. `descarrilamiento` — Descarrilamiento de tren
2. `colision_trenes` — Colisión entre trenes
3. `colision_vehiculo` — Colisión tren-vehículo de carretera
4. `colision_obstaculo` — Colisión con obstáculos en vía
5. `colision_rocas` — Colisión con desprendimiento de rocas
6. `arrollamiento_persona` — Arrollamiento de persona/peatón
7. `arrollamiento_vehiculo` — Arrollamiento de vehículo por tren
8. `arrollamiento_ciclista` — Arrollamiento de ciclista
9. `paso_nivel` — Accidente en paso a nivel
10. `incendio` — Incendio de material rodante
11. `rebase_senal` — Rebase indebido de señal
12. `escape_material` — Escape de material/tren a la deriva
13. `fallo_senalizacion` — Fallo de señalización
14. `fallo_seguridad` — Fallo en instalaciones de seguridad
15. `rotura_eje` — Rotura de eje
16. `fallo_cargamento` — Fallo de cargamento
17. `conato_colision` — Conato de colisión (sin contacto)
18. `otro` — Otros

---

## 3. 📍 UBICACIÓN Y GEOLOCALIZACIÓN

### 3.1 Estado actual
- **Coordenadas (lat/lng):** 97% de los JSONs tienen lat=null, lng=null
- **Campo "estacion":** A veces es nombre de estación, a veces nombre de municipio, a veces descripción larga
- **Campo "pk":** Formato inconsistente: "P.K. 62+902", "351+200", "PK 166+800", "429,825"

### 3.2 Propuesta: Posición real en la vía
Para cada informe se dispone de:
- **Línea** (ej: "400 Alcázar de San Juan-Cádiz")
- **PK** (punto kilométrico, ej: "429+825")

Con estos datos se puede:
1. **Geocodificar por línea + PK** usando las APIs del IGN o Adif
2. **Obtener coordenadas reales** del punto del accidente en la vía
3. **Mostrar en el mapa** la posición exacta del siniestro, no solo el municipio

### 3.3 Implementación recomendada
- Usar el archivo GTFS de Adif + tabla de PKs por línea para geocodificar
- O usar la API del IGN WMTS para obtener coordenadas a partir de línea + PK
- Almacenar lat/lng reales en el JSON
- Mantener "estacion" como referencia textual

---

## 4. 📋 RESUMEN DE ACCIONES NECESARIAS

### 🔴 CRÍTICO (datos incorrectos)
1. **Corregir gravedad:** Asignar "muy grave" a informes con víctimas mortales (actualmente todos marcados como "grave" o "menor")
2. **Normalizar tipología:** Reasignar tipo_suceso del Excel a categorías normalizadas según RD 929/2022
3. **Completar informes faltantes:** Generar JSONs para los ~8 informes sin procesar

### 🟡 IMPORTANTE (calidad de datos)
4. **Geocodificar eventos:** Obtener lat/lng reales a partir de línea + PK
5. **Normalizar PK:** Establecer formato estándar (ej: "429+825")
6. **Limpiar campo estacion:** Extraer solo nombre de estación/municipio, no descripciones largas

### 🟢 MEJORA (usabilidad)
7. **Añadir campo tipo_suceso** normalizado al JSON
8. **Añadir campo recomendaciones** con destinatario (como en el Excel)
9. **Mejorar tags** con categorías normalizadas

---

*Informe generado automáticamente por Mastermind*
