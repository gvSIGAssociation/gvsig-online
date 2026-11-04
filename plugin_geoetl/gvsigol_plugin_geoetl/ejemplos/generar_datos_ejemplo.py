# -*- coding: utf-8 -*-
"""
Genera los datos de ejemplo del manual de los nodos predictivos (carpeta clasificacion_barranco/).

Es una escena SINTÉTICA de 300 x 300 m (píxeles de 1 m, EPSG:25830): un barranco sinuoso con agua en el
cauce, vegetación a ambos lados y suelo en el resto, más algunas manchas de vegetación aisladas. Las bandas
tienen ruido y las clases se solapan, como en una imagen real, para que los resultados no sean perfectos.

    python generar_datos_ejemplo.py [carpeta_de_salida]

Es reproducible (semillas fijas): siempre produce los mismos ficheros.
"""
import json
import os
import sys

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, box

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clasificacion_barranco')
os.makedirs(OUT, exist_ok=True)
W = H = 300
X0, Y0 = 500000.0, 4300300.0               # esquina superior izquierda (EPSG:25830)
CRS = 'EPSG:25830'
NAMES = {0: 'suelo', 1: 'vegetacion', 2: 'agua'}

# ---------------------------------------------------------------- verdad de terreno
yy, xx = np.mgrid[0:H, 0:W]
centre = 150 + 55 * np.sin(xx / 38.0)                   # eje del cauce (fila de cada columna)
dist = np.abs(yy - centre)
truth = np.zeros((H, W), 'uint8')                       # 0 suelo, 1 vegetación, 2 agua
truth[dist < 38] = 1
truth[dist < 5] = 2
for cx, cy, r in ((40, 40, 14), (255, 45, 11), (60, 255, 16), (240, 250, 9)):     # manchas aisladas
    truth[(xx - cx) ** 2 + (yy - cy) ** 2 < r * r] = 1

# ---------------------------------------------------------------- ortofoto: Rojo, Verde, Infrarrojo
rng = np.random.RandomState(7)
means = {0: (125, 112, 85), 1: (55, 95, 185), 2: (30, 55, 25)}
bands = np.zeros((3, H, W), 'float32')
for cls, m in means.items():
    mask = truth == cls
    for b in range(3):
        bands[b][mask] = rng.normal(m[b], 34, mask.sum())
bands = np.clip(bands, 0, 255).astype('uint8')
with rasterio.open(os.path.join(OUT, 'ortofoto.tif'), 'w', driver='GTiff', height=H, width=W, count=3, dtype='uint8',
                   crs=CRS, transform=from_origin(X0, Y0, 1, 1), compress='deflate') as dst:
    dst.write(bands)
    dst.descriptions = ('Rojo', 'Verde', 'Infrarrojo')

# ---------------------------------------------------------------- modelo del terreno: 2 m de píxel (otra resolución)
rng2 = np.random.RandomState(11)
h2 = H // 2
yy2, xx2 = np.mgrid[0:h2, 0:h2]
centre2 = (150 + 55 * np.sin((xx2 * 2 + 1) / 38.0)) / 2.0
dist2 = np.abs(yy2 - centre2) * 2.0
from scipy.ndimage import gaussian_filter
undulation = gaussian_filter(rng2.normal(0, 1, (h2, h2)), 9)            # relieve suave que no depende del cauce
undulation = 6.0 * undulation / undulation.std()
dem = (100.0 + 0.35 * dist2 + 0.02 * xx2 * 2 + undulation + rng2.normal(0, 1.2, (h2, h2))).astype('float32')
with rasterio.open(os.path.join(OUT, 'terreno.tif'), 'w', driver='GTiff', height=h2, width=h2, count=1, dtype='float32',
                   crs=CRS, transform=from_origin(X0, Y0, 2, 2), compress='deflate', nodata=-9999) as dst:
    dst.write(dem[None])
    dst.descriptions = ('Altura',)


def px(c0, r0, c1, r1):                    # columnas/filas de píxel -> caja en metros
    return box(X0 + c0, Y0 - r1, X0 + c1, Y0 - r0)


def pure_samples(seed, per_class, avoid=()):
    """Rectángulos 100 % puros de cada clase, repartidos por la escena y sin tocar los de `avoid`."""
    srng = np.random.RandomState(seed)
    rows, taken = [], list(avoid)
    for cls, size in ((0, (14, 14)), (1, (10, 10)), (2, (6, 4))):
        chosen = []
        for _ in range(40000):
            w, h = size
            c0, r0 = srng.randint(0, W - w), srng.randint(0, H - h)
            if not (truth[r0:r0 + h, c0:c0 + w] == cls).all():
                continue
            if any(abs(c0 - c) < 30 and abs(r0 - r) < 30 for c, r in chosen + taken):
                continue
            chosen.append((c0, r0))
            rows.append({'clase': NAMES[cls], 'geometry': px(c0, r0, c0 + w, r0 + h)})
            if len(chosen) == per_class[cls]:
                break
    return rows, [(int(g.bounds[0] - X0), int(Y0 - g.bounds[3])) for g in [r['geometry'] for r in rows]]


train_rows, train_pos = pure_samples(3, {0: 5, 1: 5, 2: 4})
valid_rows, _ = pure_samples(21, {0: 4, 1: 4, 2: 3}, avoid=train_pos)
gpd.GeoDataFrame(train_rows, crs=CRS).to_file(os.path.join(OUT, 'muestras_entrenamiento.shp'), driver='ESRI Shapefile', encoding='utf-8')
gpd.GeoDataFrame(valid_rows, crs=CRS).to_file(os.path.join(OUT, 'muestras_validacion.shp'), driver='ESRI Shapefile', encoding='utf-8')

# ---------------------------------------------------------------- tramos del barranco (zonas para medir superficies)
tramos = [{'tramo': 'Tramo %d' % (i + 1), 'geometry': px(i * 100, 0, (i + 1) * 100, H)} for i in range(3)]
gpd.GeoDataFrame(tramos, crs=CRS).to_file(os.path.join(OUT, 'tramos_barranco.shp'), driver='ESRI Shapefile', encoding='utf-8')

# ---------------------------------------------------------------- puntos de inventario (para predecir una tabla)
prng = np.random.RandomState(5)


def points(n, with_class, label_col):
    rows = []
    for i in range(n):
        c, r = prng.randint(2, W - 2), prng.randint(2, H - 2)
        row = {'id': i + 1, 'rojo': int(bands[0, r, c]), 'verde': int(bands[1, r, c]), 'infrarrojo': int(bands[2, r, c]),
               'geometry': Point(X0 + c + 0.5, Y0 - r - 0.5)}
        if with_class:
            row['clase'] = NAMES[int(truth[r, c])]
        else:
            row['clase_real'] = NAMES[int(truth[r, c])]
        rows.append(row)
    return rows


gpd.GeoDataFrame(points(160, True, 'clase'), crs=CRS).to_file(os.path.join(OUT, 'puntos_inventario.shp'), driver='ESRI Shapefile', encoding='utf-8')
gpd.GeoDataFrame(points(40, False, 'clase_real'), crs=CRS).to_file(os.path.join(OUT, 'puntos_nuevos.shp'), driver='ESRI Shapefile', encoding='utf-8')

# ---------------------------------------------------------------- parcelas de campo con biomasa medida (para regresión)
brng = np.random.RandomState(9)
plots = []
while len(plots) < 45:
    c0, r0 = brng.randint(3, W - 8), brng.randint(3, H - 8)
    if any(abs(c0 - c) < 12 and abs(r0 - r) < 12 for c, r, _ in plots):
        continue
    cc, rr = c0 + 2, r0 + 2                                       # centro de la parcela de 5 x 5 m
    cls = truth[rr, cc]
    if cls == 1:
        biomass = 6.0 - dist[rr, cc] / 9.0 + brng.normal(0, 0.35)    # más densa cerca del cauce
    elif cls == 0:
        biomass = 0.35 + brng.normal(0, 0.12)
    else:
        biomass = 0.0
    plots.append((c0, r0, round(max(float(biomass), 0.0) + 0.013, 2)))        # nunca valores enteros
gpd.GeoDataFrame([{'biomasa': v, 'geometry': px(c, r, c + 5, r + 5)} for c, r, v in plots], crs=CRS).to_file(
    os.path.join(OUT, 'parcelas_campo.shp'), driver='ESRI Shapefile', encoding='utf-8')

# ---------------------------------------------------------------- verdad de terreno (para comparar los resultados del manual)
truth_report = {'pixel_m2': 1.0, 'superficie_total_m2': {}, 'superficie_por_tramo_m2': {}}
for cls, name in NAMES.items():
    truth_report['superficie_total_m2'][name] = int((truth == cls).sum())
    for i in range(3):
        truth_report['superficie_por_tramo_m2'].setdefault('Tramo %d' % (i + 1), {})[name] = int((truth[:, i * 100:(i + 1) * 100] == cls).sum())
with open(os.path.join(OUT, 'verdad_de_terreno.json'), 'w', encoding='utf-8') as f:
    json.dump(truth_report, f, ensure_ascii=False, indent=1)
print(json.dumps(truth_report, ensure_ascii=False))
print(sorted(os.listdir(OUT)))
