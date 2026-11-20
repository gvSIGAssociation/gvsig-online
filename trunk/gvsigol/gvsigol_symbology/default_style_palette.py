# -*- coding: utf-8 -*-
'''
Colores del estilo que se crea por defecto al publicar una capa.

El color sale de una paleta cerrada y se asigna de forma rotatoria dentro de cada
grupo de capas: capas del mismo grupo reciben colores distintos, y el nombre del
grupo desplaza el punto de partida para que no todos los grupos empiecen igual.
'''
import zlib

# Ordenada para que dos colores consecutivos contrasten entre sí.
PALETTE = (
    '#2E86C1',  # azul
    '#E67E22',  # naranja
    '#17A589',  # verde azulado
    '#D81B60',  # magenta
    '#B7950B',  # ocre
    '#8E44AD',  # morado
    '#43A047',  # verde
    '#C0392B',  # rojo
    '#00ACC1',  # cian
    '#3F51B5',  # índigo
)

BORDER_DARKEN_FACTOR = 0.7


def pick_color(group_name, layers_in_group):
    # crc32 y no hash(): hash() cambia entre procesos y el color no sería reproducible.
    offset = zlib.crc32((group_name or '').encode('utf-8'))
    return PALETTE[(offset + (layers_in_group or 0)) % len(PALETTE)]


def darken(hex_color, factor=BORDER_DARKEN_FACTOR):
    channels = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02X%02X%02X' % tuple(int(channel * factor) for channel in channels)
