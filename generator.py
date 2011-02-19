#!/usr/bin/python
# -*- coding: utf-8 -*-

from numpy import *

LINE_LENGTH = 100
REPETITIONS = 90
PIXEL_F = 100.0
PIXEL_T = 1.0 / PIXEL_F
SHUTTER_F = 5.856
SHUTTER_T = 1.0 / (SHUTTER_F * 2.0)

# TODO: cambiare con lettura da file
# TODO: preparare per multiriga
input_data = ones(LINE_LENGTH, dtype=float).repeat(REPETITIONS)
# TODO: aggiungere bleaching
# TODO: aggiungere rumore
er_data = ones(LINE_LENGTH, dtype=float).repeat(REPETITIONS) * 2


def build_row_square(l, phi):
    x = arange(l)
    r = square((2 * pi) * ((SHUTTER_F * x * PIXEL_T) + phi))/2 + 0.5
    return r > 0.5

shutter = build_row_square(LINE_LENGTH, 0.0)


def pixel_start(pos):
    return pos * PIXEL_T


def pixel_end(pos):
    return (pos + 1) * PIXEL_T

enhanced_data = empty_like(input_data)
for (pos, val) in ndenumerate(input_data):
    pos = pos[0]
    start = pixel_start(pos)
    end = pixel_end(pos)
    # Se non c'è transizione
    if start // SHUTTER_T == end // SHUTTER_T:
        # TODO: per capire on/off mi baso sul modulo due. Non è il massimo!
        if (start // SHUTTER_T) % 2:
            enhanced_data[pos] = val * er_data[pos]
        else:
            enhanced_data[pos] = val
    # Transizione
    else:
        phase_start = start % (SHUTTER_T)
        phase_end = end % (SHUTTER_T)
        # Durata totale del pixel. In realtà è inutile calcolarla
        total_phase = (1 - phase_end) + phase_start
        phase_before = (1 - phase_end)
        phase_after = phase_start
        # Acceso -> spento
        if (start // SHUTTER_T) % 2:
            enhanced_data[pos] = phase_before * val * er_data[pos] + \
                                 phase_after * val
        else:
            enhanced_data[pos] = phase_before * val + \
                phase_after * val * er_data[pos]
enhanced_data = enhanced_data.reshape(REPETITIONS, LINE_LENGTH)
print enhanced_data.shape
savetxt("out/generated.dat", enhanced_data, fmt="%3.4f0")
