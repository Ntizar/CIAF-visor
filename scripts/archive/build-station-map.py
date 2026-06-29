#!/usr/bin/env python3
"""
Build a hardcoded station-to-coordinates JSON map for Spanish railway stations
mentioned in CIAF accident reports.

Reads all JSON reports from data/reports/*.json, extracts unique station names
from ubicacion.estacion, filters out garbage entries, and produces a mapping
file at data/station-coords.json.

Usage:
    python3 scripts/build-station-map.py
"""

import json
import glob
import os
import re
import unicodedata

# ---------------------------------------------------------------------------
# Hardcoded coordinates for all Spanish provincial capitals, major railway
# stations, and known junctions / secondary stations referenced in CIAF data.
# Format: canonical_name -> {lat, lng, provincia}
# ---------------------------------------------------------------------------

STATION_COORDS = {
    # ===== Major intercity / hub stations =====
    "Madrid Chamartín":               {"lat": 40.4726, "lng": -3.6825, "provincia": "Madrid"},
    "Madrid Atocha":                   {"lat": 40.4065, "lng": -3.6920, "provincia": "Madrid"},
    "Atocha":                          {"lat": 40.4065, "lng": -3.6920, "provincia": "Madrid"},
    "Chamartín":                       {"lat": 40.4726, "lng": -3.6825, "provincia": "Madrid"},
    "Barcelona Sants":                 {"lat": 41.3725, "lng":  2.1404, "provincia": "Barcelona"},
    "Sevilla Santa Justa":             {"lat": 37.3919, "lng": -5.9773, "provincia": "Sevilla"},
    "Valencia Nord":                   {"lat": 39.4553, "lng": -0.3697, "provincia": "Valencia"},
    "Valencia Joaquín Sorolla":        {"lat": 39.4520, "lng": -0.3890, "provincia": "Valencia"},
    "Bilbao Abando":                   {"lat": 43.2603, "lng": -2.9262, "provincia": "Vizcaya"},
    "Zaragoza Delicias":               {"lat": 41.6568, "lng": -0.8812, "provincia": "Zaragoza"},
    "León":                            {"lat": 42.5981, "lng": -5.5667, "provincia": "León"},
    "Cuenca-Fernando Zóbel":           {"lat": 40.0335, "lng": -2.1431, "provincia": "Cuenca"},
    "A Coruña":                        {"lat": 43.3360, "lng": -8.3953, "provincia": "A Coruña"},
    "Vigo-Guixar":                     {"lat": 42.2288, "lng": -8.7117, "provincia": "Pontevedra"},
    "Pontevedra":                      {"lat": 42.4288, "lng": -8.6453, "provincia": "Pontevedra"},
    "Salou":                           {"lat": 41.0768, "lng":  1.1440, "provincia": "Tarragona"},
    "Figueres":                        {"lat": 42.2637, "lng":  2.9492, "provincia": "Girona"},
    "Lleida-Pirineus":                 {"lat": 41.6137, "lng":  0.6276, "provincia": "Lleida"},
    "Logroño":                         {"lat": 42.4611, "lng": -2.4453, "provincia": "La Rioja"},
    "Pamplona":                        {"lat": 42.8265, "lng": -1.6674, "provincia": "Navarra"},
    "Santander":                       {"lat": 43.4593, "lng": -3.8117, "provincia": "Cantabria"},
    "Gijón":                           {"lat": 43.5365, "lng": -5.6604, "provincia": "Asturias"},
    "Oviedo":                          {"lat": 43.3667, "lng": -5.8492, "provincia": "Asturias"},
    "Ourense":                         {"lat": 42.3365, "lng": -7.8560, "provincia": "Ourense"},
    "Orense":                          {"lat": 42.3365, "lng": -7.8560, "provincia": "Ourense"},
    "Cáceres":                         {"lat": 39.4710, "lng": -6.3723, "provincia": "Cáceres"},
    "Badajoz":                         {"lat": 38.8793, "lng": -6.9700, "provincia": "Badajoz"},
    "Córdoba":                         {"lat": 37.8884, "lng": -4.7794, "provincia": "Córdoba"},
    "Málaga María Zambrano":           {"lat": 36.7106, "lng": -4.4321, "provincia": "Málaga"},
    "Granada":                         {"lat": 37.1872, "lng": -3.6011, "provincia": "Granada"},
    "Almería":                         {"lat": 36.8318, "lng": -2.3983, "provincia": "Almería"},
    "Jaén":                            {"lat": 37.7703, "lng": -3.7588, "provincia": "Jaén"},
    "Albacete":                        {"lat": 38.9946, "lng": -1.8560, "provincia": "Albacete"},
    "Ciudad Real":                     {"lat": 38.9867, "lng": -3.9276, "provincia": "Ciudad Real"},
    "Cádiz":                           {"lat": 36.5298, "lng": -6.2926, "provincia": "Cádiz"},
    "Huelva":                          {"lat": 37.2614, "lng": -6.9447, "provincia": "Huelva"},
    "Murcia del Carmen":               {"lat": 37.9870, "lng": -1.1300, "provincia": "Murcia"},
    "Cartagena":                       {"lat": 37.5965, "lng": -0.9966, "provincia": "Murcia"},
    "Palma de Mallorca":               {"lat": 39.5714, "lng":  2.6544, "provincia": "Illes Balears"},
    "Castellón":                       {"lat": 39.9864, "lng": -0.0513, "provincia": "Castellón"},
    "Alicante":                        {"lat": 38.3452, "lng": -0.4939, "provincia": "Alicante"},
    "Teruel":                          {"lat": 40.3407, "lng": -1.1064, "provincia": "Teruel"},
    "Huesca":                          {"lat": 42.1316, "lng": -0.4081, "provincia": "Huesca"},

    # ===== Other provincial capitals / important cities =====
    "Valladolid Campo Grande":         {"lat": 41.6430, "lng": -4.7278, "provincia": "Valladolid"},
    "Vitoria-Gasteiz":                 {"lat": 42.8410, "lng": -2.6744, "provincia": "Álava"},
    "Santiago de Compostela":          {"lat": 42.8748, "lng": -8.5398, "provincia": "A Coruña"},
    "Lugo":                            {"lat": 43.0078, "lng": -7.5581, "provincia": "Lugo"},
    "Ponferrada":                      {"lat": 42.5466, "lng": -6.5911, "provincia": "León"},
    "Ávila":                           {"lat": 40.6560, "lng": -4.6971, "provincia": "Ávila"},
    "Salamanca":                       {"lat": 40.9685, "lng": -5.6641, "provincia": "Salamanca"},
    "Segovia":                         {"lat": 40.9485, "lng": -4.1180, "provincia": "Segovia"},
    "Guadalajara":                     {"lat": 40.6337, "lng": -3.1674, "provincia": "Guadalajara"},
    "Toledo":                          {"lat": 39.8628, "lng": -4.0273, "provincia": "Toledo"},
    "Cuenca":                          {"lat": 40.0704, "lng": -2.1350, "provincia": "Cuenca"},
    "Soria":                           {"lat": 41.7636, "lng": -2.4649, "provincia": "Soria"},
    "Palencia":                        {"lat": 42.0094, "lng": -4.5309, "provincia": "Palencia"},
    "Burgos":                          {"lat": 42.3439, "lng": -3.6983, "provincia": "Burgos"},
    "Miranda de Ebro":                 {"lat": 42.6858, "lng": -2.9464, "provincia": "Burgos"},
    "Zamora":                          {"lat": 41.5033, "lng": -5.7556, "provincia": "Zamora"},
    "Girona":                          {"lat": 41.9794, "lng":  2.8193, "provincia": "Girona"},
    "Tarragona":                       {"lat": 41.1189, "lng":  1.2446, "provincia": "Tarragona"},
    "Reus":                            {"lat": 41.1562, "lng":  1.1066, "provincia": "Tarragona"},
    "Tortosa":                         {"lat": 40.8117, "lng":  0.5205, "provincia": "Tarragona"},

    # ===== Madrid area =====
    "Aluche":                          {"lat": 40.3895, "lng": -3.7676, "provincia": "Madrid"},
    "Atocha-Cercanías":                {"lat": 40.4065, "lng": -3.6920, "provincia": "Madrid"},
    "Vicálvaro":                       {"lat": 40.4121, "lng": -3.5712, "provincia": "Madrid"},
    "Torrejón de Ardoz":               {"lat": 40.4556, "lng": -3.4822, "provincia": "Madrid"},
    "Getafe Industrial":               {"lat": 40.3028, "lng": -3.7248, "provincia": "Madrid"},
    "Leganes":                         {"lat": 40.3300, "lng": -3.7611, "provincia": "Madrid"},
    "Humanes":                         {"lat": 40.2524, "lng": -3.9242, "provincia": "Madrid"},
    "Móstoles":                        {"lat": 40.3228, "lng": -3.8649, "provincia": "Madrid"},
    "Pinar de las Rozas":              {"lat": 40.5250, "lng": -3.8750, "provincia": "Madrid"},
    "Navacerrada":                     {"lat": 40.8333, "lng": -4.0167, "provincia": "Madrid"},
    "Alcalá de Henares":               {"lat": 40.4833, "lng": -3.3667, "provincia": "Madrid"},
    "Villalba de Guadarrama":          {"lat": 40.6333, "lng": -3.8500, "provincia": "Madrid"},
    "Mataespesa de Alpedrete":         {"lat": 40.6167, "lng": -4.0667, "provincia": "Madrid"},
    "San Cristóbal Industrial":        {"lat": 40.3833, "lng": -3.7500, "provincia": "Madrid"},
    "La Florida":                      {"lat": 40.4500, "lng": -3.7167, "provincia": "Madrid"},

    # ===== Barcelona area =====
    "Barcelona Sant Andreu Arenal":    {"lat": 41.4350, "lng":  2.1900, "provincia": "Barcelona"},
    "Sant Andreu Arenal":              {"lat": 41.4350, "lng":  2.1900, "provincia": "Barcelona"},
    "Barcelona Marina":                {"lat": 41.3923, "lng":  2.1948, "provincia": "Barcelona"},
    "El Clot-Aragó":                   {"lat": 41.4090, "lng":  2.1897, "provincia": "Barcelona"},
    "El Clot Aragó":                   {"lat": 41.4090, "lng":  2.1897, "provincia": "Barcelona"},
    "Sant Celoni":                     {"lat": 41.6936, "lng":  2.4940, "provincia": "Barcelona"},
    "Badalona":                        {"lat": 41.4536, "lng":  2.2438, "provincia": "Barcelona"},
    "Cornellà":                        {"lat": 41.3566, "lng":  2.0706, "provincia": "Barcelona"},
    "Mataró":                          {"lat": 41.5373, "lng":  2.4474, "provincia": "Barcelona"},
    "Granollers Centre":               {"lat": 41.6002, "lng":  2.2863, "provincia": "Barcelona"},
    "Blanes":                          {"lat": 41.6778, "lng":  2.7920, "provincia": "Girona"},
    "Tordera":                         {"lat": 41.7026, "lng":  2.7247, "provincia": "Barcelona"},
    "Hostalric":                       {"lat": 41.7512, "lng":  2.6340, "provincia": "Girona"},
    "Cardedeu":                        {"lat": 41.6353, "lng":  2.3564, "provincia": "Barcelona"},
    "Llinars del Vallès":              {"lat": 41.6396, "lng":  2.4016, "provincia": "Barcelona"},
    "Cerdanyola del Vallès":           {"lat": 41.4929, "lng":  2.1374, "provincia": "Barcelona"},
    "Sant Feliu de Llobregat":         {"lat": 41.3843, "lng":  2.0441, "provincia": "Barcelona"},
    "Sant Pol de Mar":                 {"lat": 41.6022, "lng":  2.5968, "provincia": "Barcelona"},
    "Sitges":                          {"lat": 41.2367, "lng":  1.8034, "provincia": "Barcelona"},
    "Vilanova i la Geltrú":            {"lat": 41.2193, "lng":  1.7286, "provincia": "Barcelona"},
    "Martorell":                       {"lat": 41.4733, "lng":  1.9272, "provincia": "Barcelona"},
    "Molins de Rei":                   {"lat": 41.4138, "lng":  2.0143, "provincia": "Barcelona"},
    "Rubí":                            {"lat": 41.4933, "lng":  2.0345, "provincia": "Barcelona"},
    "Gavà":                            {"lat": 41.3063, "lng":  2.0033, "provincia": "Barcelona"},
    "Bellvitge":                       {"lat": 41.3534, "lng":  2.1065, "provincia": "Barcelona"},
    "Manresa":                         {"lat": 41.7257, "lng":  1.8269, "provincia": "Barcelona"},
    "Olesa de Montserrat":             {"lat": 41.5441, "lng":  1.8932, "provincia": "Barcelona"},
    "Prat de Llobregat":               {"lat": 41.3298, "lng":  2.0889, "provincia": "Barcelona"},
    "La Pobla Llarga":                 {"lat": 41.3632, "lng":  2.0083, "provincia": "Barcelona"},
    "Calella":                         {"lat": 41.6136, "lng":  2.6604, "provincia": "Barcelona"},
    "Vilamalla":                       {"lat": 41.6839, "lng":  2.8280, "provincia": "Girona"},
    "Torelló":                         {"lat": 41.8167, "lng":  2.2667, "provincia": "Barcelona"},

    # ===== Valencia area =====
    "Alfafar-Benetússer":              {"lat": 39.4211, "lng": -0.3556, "provincia": "Valencia"},
    "Algemesí":                        {"lat": 39.1535, "lng": -0.4350, "provincia": "Valencia"},
    "Alzira":                          {"lat": 39.1547, "lng": -0.4406, "provincia": "Valencia"},
    "Cheste":                          {"lat": 39.4944, "lng": -0.6841, "provincia": "Valencia"},
    "Vila-real":                       {"lat": 39.9367, "lng": -0.1997, "provincia": "Castellón"},
    "Villarreal":                      {"lat": 39.9367, "lng": -0.1997, "provincia": "Castellón"},
    "Benifaió":                        {"lat": 39.2831, "lng": -0.5750, "provincia": "Valencia"},
    "Silla":                           {"lat": 39.3606, "lng": -0.4183, "provincia": "Valencia"},
    "Valencia Sant Isidre":            {"lat": 39.4397, "lng": -0.4033, "provincia": "Valencia"},
    "Valencia-Font de Sant Lluís":     {"lat": 39.4530, "lng": -0.3520, "provincia": "Valencia"},
    "Moncofar":                        {"lat": 39.8114, "lng": -0.1520, "provincia": "Castellón"},
    "Onda":                            {"lat": 39.9625, "lng": -0.2605, "provincia": "Castellón"},
    "Elx Parc":                        {"lat": 38.2667, "lng": -0.6833, "provincia": "Alicante"},
    "Novelda-Aspe":                    {"lat": 38.3833, "lng": -0.8167, "provincia": "Alicante"},
    "Villena":                         {"lat": 38.6333, "lng": -0.8667, "provincia": "Alicante"},
    "Los Gavilanes":                   {"lat": 39.5000, "lng": -0.7167, "provincia": "Valencia"},
    "Xeraco":                          {"lat": 39.0333, "lng": -0.2167, "provincia": "Valencia"},
    "Pedralba":                        {"lat": 39.5500, "lng": -0.7167, "provincia": "Valencia"},
    "El Rebollar":                     {"lat": 41.9000, "lng": -6.7833, "provincia": "Zamora"},
    "La Encina":                       {"lat": 38.3667, "lng": -0.7167, "provincia": "Alicante"},
    "Els Guiamets":                    {"lat": 41.0833, "lng": 0.7500, "provincia": "Tarragona"},

    # ===== Galicia =====
    "Santiago de Compostela":          {"lat": 42.8748, "lng": -8.5398, "provincia": "A Coruña"},
    "O Porriño":                       {"lat": 42.1618, "lng": -8.6353, "provincia": "Pontevedra"},
    "Redondela":                       {"lat": 42.2851, "lng": -8.6097, "provincia": "Pontevedra"},
    "Guillarei":                       {"lat": 42.0705, "lng": -8.6368, "provincia": "Pontevedra"},
    "Chapela":                         {"lat": 42.2850, "lng": -8.5640, "provincia": "Pontevedra"},
    "Betanzos-Infesta":                {"lat": 43.2840, "lng": -8.2180, "provincia": "A Coruña"},
    "Xubia":                           {"lat": 43.4800, "lng": -8.2340, "provincia": "A Coruña"},

    # ===== Asturias =====
    "Avilés":                          {"lat": 43.5574, "lng": -5.9208, "provincia": "Asturias"},
    "Trasona":                         {"lat": 43.5450, "lng": -5.8230, "provincia": "Asturias"},
    "Trubia":                          {"lat": 43.3400, "lng": -5.9780, "provincia": "Asturias"},
    "Pravia":                          {"lat": 43.4861, "lng": -6.1120, "provincia": "Asturias"},
    "Infiesto":                        {"lat": 43.3500, "lng": -5.2167, "provincia": "Asturias"},
    "Boñar":                           {"lat": 42.8667, "lng": -5.3167, "provincia": "León"},
    "El Caleyo":                       {"lat": 43.3667, "lng": -5.8500, "provincia": "Asturias"},
    "El Entrego":                      {"lat": 43.2833, "lng": -5.7167, "provincia": "Asturias"},
    "Lieres":                          {"lat": 43.2000, "lng": -5.6167, "provincia": "Asturias"},
    "Laviana":                         {"lat": 43.2500, "lng": -5.5667, "provincia": "Asturias"},
    "Sama de Langreo":                 {"lat": 43.2833, "lng": -5.7667, "provincia": "Asturias"},
    "Langreo":                         {"lat": 43.2833, "lng": -5.7667, "provincia": "Asturias"},
    "San Claudio":                     {"lat": 43.3500, "lng": -5.7833, "provincia": "Asturias"},
    "Aboño":                           {"lat": 43.5833, "lng": -5.7500, "provincia": "Asturias"},

    # ===== Cantabria =====
    "Cazoña":                          {"lat": 43.4667, "lng": -3.8333, "provincia": "Cantabria"},
    "Maliño":                          {"lat": 43.4500, "lng": -3.8500, "provincia": "Cantabria"},
    "Maliaño":                         {"lat": 43.4500, "lng": -3.8500, "provincia": "Cantabria"},
    "Renedo":                          {"lat": 43.3500, "lng": -3.8333, "provincia": "Cantabria"},
    "Unquera":                         {"lat": 43.3833, "lng": -4.4167, "provincia": "Cantabria"},
    "Astillero":                       {"lat": 43.4000, "lng": -3.8167, "provincia": "Cantabria"},
    "A Susana":                        {"lat": 43.3300, "lng": -3.8100, "provincia": "Cantabria"},

    # ===== Basque Country =====
    "Zalla":                           {"lat": 43.2167, "lng": -3.1333, "provincia": "Vizcaya"},
    "Sodupe":                          {"lat": 43.2167, "lng": -3.0667, "provincia": "Vizcaya"},
    "Hernani":                         {"lat": 43.2690, "lng": -1.9745, "provincia": "Guipúzcoa"},
    "Hernani Centro":                  {"lat": 43.2690, "lng": -1.9745, "provincia": "Guipúzcoa"},
    "Zumárraga":                       {"lat": 43.0833, "lng": -2.3167, "provincia": "Guipúzcoa"},
    "Tolosa":                          {"lat": 43.1350, "lng": -2.0740, "provincia": "Guipúzcoa"},
    "Altsasua":                        {"lat": 42.8988, "lng": -2.1697, "provincia": "Navarra"},
    "Anoeta":                          {"lat": 42.8980, "lng": -2.1300, "provincia": "Guipúzcoa"},
    "Aranguren":                       {"lat": 42.8940, "lng": -1.6120, "provincia": "Navarra"},
    "Heras":                           {"lat": 43.2333, "lng": -2.8667, "provincia": "Vizcaya"},
    "Lezama":                          {"lat": 43.2667, "lng": -2.8333, "provincia": "Vizcaya"},
    "Zorrotza":                        {"lat": 43.2833, "lng": -2.9500, "provincia": "Vizcaya"},
    "Balmaseda Mercancías":            {"lat": 43.1917, "lng": -3.1917, "provincia": "Vizcaya"},
    "Francia":                         {"lat": 43.2620, "lng": -2.9250, "provincia": "Vizcaya"},
    "Ortuella":                        {"lat": 43.3083, "lng": -3.0583, "provincia": "Vizcaya"},
    "Barakaldo":                       {"lat": 43.2967, "lng": -2.9833, "provincia": "Vizcaya"},
    "Sestao":                          {"lat": 43.3100, "lng": -3.0083, "provincia": "Vizcaya"},
    "Inoso-Oiardo":                    {"lat": 42.9000, "lng": -2.5167, "provincia": "Álava"},

    # ===== Navarra / La Rioja =====
    "Tudela de Navarra":               {"lat": 42.0615, "lng": -1.6065, "provincia": "Navarra"},
    "Viana de Cega":                   {"lat": 42.5467, "lng": -1.6581, "provincia": "Navarra"},
    "Fuenmayor":                       {"lat": 42.4750, "lng": -2.5620, "provincia": "La Rioja"},
    "Cortes de Navarra":               {"lat": 42.1667, "lng": -1.6667, "provincia": "Navarra"},
    "Apeadero de Abaroa-San Miguel":   {"lat": 42.8500, "lng": -1.7167, "provincia": "Navarra"},

    # ===== Aragón =====
    "Calatayud":                       {"lat": 41.3535, "lng": -1.6458, "provincia": "Zaragoza"},
    "Tardienta":                       {"lat": 42.0833, "lng": -0.5333, "provincia": "Huesca"},
    "Cambiador de ancho de Zaragoza Delicias": {"lat": 41.6568, "lng": -0.8812, "provincia": "Zaragoza"},
    "Ariza":                           {"lat": 41.3167, "lng": -2.0500, "provincia": "Zaragoza"},
    "Ascó":                            {"lat": 41.2167, "lng":  0.5667, "provincia": "Tarragona"},
    "Fabara":                          {"lat": 41.1833, "lng":  0.1000, "provincia": "Zaragoza"},
    "Río Huerva":                      {"lat": 41.6333, "lng": -0.9333, "provincia": "Zaragoza"},
    "Las Navas del Marqués":           {"lat": 40.6000, "lng": -4.3333, "provincia": "Ávila"},

    # ===== Castilla-La Mancha =====
    "Medina del Campo":                {"lat": 41.3083, "lng": -4.8333, "provincia": "Valladolid"},
    "Tembleque":                       {"lat": 39.7000, "lng": -3.1167, "provincia": "Toledo"},
    "Socuéllamos":                     {"lat": 39.2833, "lng": -3.0000, "provincia": "Ciudad Real"},
    "Tarancón":                        {"lat": 40.0167, "lng": -3.0167, "provincia": "Cuenca"},
    "Urda":                            {"lat": 39.4167, "lng": -3.4833, "provincia": "Toledo"},

    # ===== Andalucía =====
    "Lora del Río":                    {"lat": 37.6667, "lng": -5.5333, "provincia": "Sevilla"},
    "Montoro":                         {"lat": 38.0167, "lng": -4.3833, "provincia": "Córdoba"},
    "Alcolea":                         {"lat": 37.9500, "lng": -4.6667, "provincia": "Córdoba"},
    "San Fernando de Cádiz":           {"lat": 36.4750, "lng": -6.2000, "provincia": "Cádiz"},
    "Arahal":                          {"lat": 37.2667, "lng": -5.5500, "provincia": "Sevilla"},
    "Calañas":                         {"lat": 37.6500, "lng": -6.8833, "provincia": "Huelva"},
    "Tocón-MonteFrío":                 {"lat": 37.2500, "lng": -3.6333, "provincia": "Granada"},
    "Villafra":                        {"lat": 37.8833, "lng": -4.8167, "provincia": "Córdoba"},

    # ===== León / Castilla y León =====
    "Dueñas":                          {"lat": 42.2167, "lng": -4.4333, "provincia": "Palencia"},
    "Cistierna":                       {"lat": 42.8000, "lng": -5.2000, "provincia": "León"},
    "Villamanín":                      {"lat": 42.8000, "lng": -5.8333, "provincia": "León"},
    "La Vecilla":                      {"lat": 42.7500, "lng": -5.4000, "provincia": "León"},
    "Arévalo":                         {"lat": 41.0667, "lng": -4.7167, "provincia": "Ávila"},
    "Puebla de Sanabria":              {"lat": 42.0667, "lng": -6.6333, "provincia": "Zamora"},
    "Villadepalos":                    {"lat": 42.5333, "lng": -6.0667, "provincia": "León"},
    "La Hiniesta":                     {"lat": 42.2500, "lng": -5.8333, "provincia": "León"},

    # ===== Cataluña (Tarragona / Lleida) =====
    "Tamarite":                        {"lat": 41.8667, "lng":  0.2833, "provincia": "Huesca"},
    "Borges del Camp":                 {"lat": 41.1667, "lng":  1.0167, "provincia": "Tarragona"},
    "San Vicente de Calders":          {"lat": 41.2333, "lng":  1.6333, "provincia": "Tarragona"},

    # ===== Murcia =====
    "El Pozo":                         {"lat": 37.9833, "lng": -1.1333, "provincia": "Murcia"},

    # ===== Girona =====
    "Figueres-Vilafant":               {"lat": 42.2605, "lng":  2.9385, "provincia": "Girona"},

    # ===== Burgos / Palencia =====
    "Burgos Rosa de Lima":             {"lat": 42.3439, "lng": -3.6983, "provincia": "Burgos"},

    # ===== Santa María de Huerta =====
    "Santa María de Huerta":           {"lat": 41.2667, "lng": -2.1833, "provincia": "Soria"},

    # ===== Torralba =====
    "Torralba":                        {"lat": 41.9167, "lng": -2.5333, "provincia": "Soria"},

    # ===== Additional secondary stations =====
    "Pedrera":                         {"lat": 37.3333, "lng": -4.6833, "provincia": "Sevilla"},
    "Apeadero de Platja de Castelldefels": {"lat": 41.2667, "lng": 1.9333, "provincia": "Barcelona"},
    "Apeadero de Salbio":              {"lat": 43.2333, "lng": -2.8667, "provincia": "Vizcaya"},
    "Caparrates":                      {"lat": 41.1500, "lng": -1.2667, "provincia": "Zaragoza"},
}


# ---------------------------------------------------------------------------
# Garbage filter: names that are clearly not station names
# ---------------------------------------------------------------------------

# Words/phrases that indicate the "station" field contains a description
GARBAGE_WORDS = {
    "en condiciones", "circula", "por obras", "a la altura",
    "punto kilom", "donde", "observa que", "va caminando",
    "se produce", "con destino", "tenía prescrita parada",
    "maquinista", "jornada de conducción", "bifurcación sagrera",
    "paso a nivel", "clase a", "clase b", "clase c",
    "plena vía", "plena via", "eje del", "descarril",
    "intercalado", "todo tren", "velocidad", "carga",
    "colision", "arrollamiento", "incendio",
    "saliendo de", "salir de", "cuando se",
    "el que", "la que", "los que", "las que",
    "a la izquierda", "a la derecha",
    "inici", "continu", "rebas", "marchaba",
    "presenta", "inflam", "pasa", "pasaba",
    "con la", "el día", "conductor",
    "segundo eje", "descenso", "trabaj",
    "en anuncio de parada", "en un", "en la vía",
}

EXACT_GARBAGE = {
    "paso a nivel",
    "paso a nivel clase a",
    "paso a nivel clase b",
    "paso a nivel clase c",
    "paso a nivel por obras",
    "plena vía",
    "plena via",
    "terminal de contenedores de silla",
}

MAX_STATION_NAME_LEN = 35


def strip_accents(s: str) -> str:
    """Remove combining characters (accents) from string."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')


def normalize_key(name: str) -> str:
    """Produce a lookup key: strip accents, lowercase, simplify punctuation."""
    key = strip_accents(name).lower().strip()
    # Normalize all dash-like chars
    key = re.sub(r'\s*[-–—]\s*', '-', key)
    key = re.sub(r'\s+', ' ', key)
    return key


def is_garbage(name: str) -> bool:
    """Return True if the name looks like a description rather than a station."""
    lower = name.lower().strip()

    # Exact garbage
    if lower in EXACT_GARBAGE:
        return True

    # Too long → almost certainly a description
    if len(name) > MAX_STATION_NAME_LEN:
        return True

    # Check for garbage words/phrases (use word-boundary matching
    # to avoid false positives like "donde" matching inside "redondela")
    for gw in GARBAGE_WORDS:
        if re.search(r'\b' + re.escape(gw) + r'\b', lower):
            return True

    return False


def extract_station_names(reports_dir: str) -> set:
    """Read all JSON report files and extract unique station names."""
    stations = set()
    for filepath in sorted(glob.glob(os.path.join(reports_dir, "*.json"))):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            loc = item.get("ubicacion", {})
            est = loc.get("estacion")
            if est and isinstance(est, str) and est.strip():
                stations.add(est.strip())
    return stations


def build_lookup_table():
    """Build a normalized→(canonical_name, coords) mapping from the hardcoded coords."""
    lookup = {}
    for name, coords in STATION_COORDS.items():
        key = normalize_key(name)
        lookup[key] = (name, coords)
    return lookup


def match_station(raw_name: str, lookup: dict):
    """
    Try to match a raw station name from reports against the lookup table.
    Returns (matched_name, coords_dict) or (None, None).
    """
    key = normalize_key(raw_name)

    # Exact match
    if key in lookup:
        return lookup[key]

    # Try stripping all dashes/spaces for comparison
    # (handles "SEVILLA - SANTA JUSTA" → "sevillasantajusta" etc.)
    key_no_dash = re.sub(r'[\s\-–—]+', '', key)
    for lk, (lname, lcoords) in lookup.items():
        lk_no_dash = re.sub(r'[\s\-–—]+', '', lk)
        if key_no_dash == lk_no_dash:
            return (lname, lcoords)

    # Remove trailing garbage fragments (e.g., "y con", "en", etc.)
    clean = re.sub(r'\s+(y|en|con|de|el|la|los|las|desde|donde|a)\b.*$', '', raw_name, flags=re.IGNORECASE).strip()
    key2 = normalize_key(clean)
    if key2 in lookup:
        return lookup[key2]

    # Try removing parenthetical content
    clean2 = re.sub(r'\s*\(.*?\)\s*', '', raw_name).strip()
    key3 = normalize_key(clean2)
    if key3 in lookup:
        return lookup[key3]

    # Substring matching: check if any lookup key is a substring or vice versa
    for lk, (lname, lcoords) in lookup.items():
        if len(lk) > 2 and len(key) > 2:
            if lk in key or key in lk:
                return (lname, lcoords)

    return (None, None)


def main():
    reports_dir = "/root/workspace/CIAF-visor/data/reports"
    output_path = "/root/workspace/CIAF-visor/data/station-coords.json"

    # 1. Extract all station names
    print("Extracting station names from reports...")
    raw_stations = extract_station_names(reports_dir)
    print(f"  Found {len(raw_stations)} unique raw station names.")

    # 2. Filter garbage
    valid_stations = set()
    garbage_stations = set()
    for name in raw_stations:
        if is_garbage(name):
            garbage_stations.add(name)
        else:
            valid_stations.add(name)
    print(f"  Filtered out {len(garbage_stations)} garbage entries:")
    for g in sorted(garbage_stations):
        print(f"    [GARBAGE] {g!r}")

    print(f"  {len(valid_stations)} valid station names remaining.")

    # 3. Build lookup
    lookup = build_lookup_table()

    # 4. Match valid stations to coordinates
    result = {}
    matched = set()
    unmatched = []

    for name in sorted(valid_stations):
        matched_name, coords = match_station(name, lookup)
        if matched_name and coords:
            result[name] = {
                "lat": coords["lat"],
                "lng": coords["lng"],
                "provincia": coords["provincia"],
            }
            matched.add(name)
        else:
            unmatched.append(name)

    print(f"\n  Matched {len(matched)} stations to coordinates.")
    if unmatched:
        print(f"  {len(unmatched)} stations could not be matched:")
        for u in unmatched:
            print(f"    - {u}")

    # 5. Also include all hardcoded stations (even if not in reports)
    for name, coords in STATION_COORDS.items():
        if name not in result:
            result[name] = {
                "lat": coords["lat"],
                "lng": coords["lng"],
                "provincia": coords["provincia"],
            }

    print(f"\n  Total entries in output: {len(result)}")

    # 6. Sort and write
    sorted_result = dict(sorted(result.items()))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_result, f, indent=2, ensure_ascii=False)

    print(f"\n  Written to {output_path}")

    # 7. Print sample
    print("\nSample entries:")
    samples = ["Madrid Chamartín", "Barcelona Sants", "Sevilla Santa Justa",
               "Santiago de Compostela", "Gijón", "Cádiz", "Guillarei",
               "León", "Zaragoza Delicias", "Valencia Nord"]
    for s in samples:
        if s in result:
            c = result[s]
            print(f"  {s}: ({c['lat']}, {c['lng']}) [{c['provincia']}]")


if __name__ == "__main__":
    main()
