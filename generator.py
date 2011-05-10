#!/usr/bin/python
# -*- coding: utf-8 -*-

from numpy import *
import pylab
from matplotlib.colors import LinearSegmentedColormap

LINE_LENGTH = 100
REPETITIONS = 15
PIXEL_F = 100.0
PIXEL_T = 1.0 / PIXEL_F
SHUTTER_F = 5.856
SHUTTER_T = 1.0 / (SHUTTER_F * 2.0)

# TODO: cambiare con lettura da file
# TODO: preparare per multiriga

segmentdata = {'red': [(0.0, 0.0, 0.0),
                       (1.0, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0),
                         (1.0, 1.0, 1.0)],
               'blue': [(0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0)],
}

my_color_map = LinearSegmentedColormap("stdGreen", segmentdata)

# input_data = ones(LINE_LENGTH, dtype=float).repeat(REPETITIONS)
input_data = genfromtxt("dati/NonUniformeRate.csv", delimiter=";")
# Trasformo in array bidimensionale, salvo il numero di righe
input_data = input_data.reshape(-1, LINE_LENGTH)
rows = input_data.shape[0]
# Aggiungo le ripetizioni, do la forma definitiva all'array
input_data = input_data.repeat(REPETITIONS, 0)
input_data = input_data.reshape(rows, REPETITIONS, LINE_LENGTH)

# Visualizzo principalmente per debugging
# print input_data.shape
# pylab.imshow(input_data[10,:,:], cmap=my_color_map)
# pylab.show()

# TODO: aggiungere bleaching
# TODO: aggiungere rumore
# er_data = ones(LINE_LENGTH, dtype=float).repeat(REPETITIONS) * 2
er_data = genfromtxt("dati/NonUniformeRatio.csv", delimiter=";")
er_data = er_data.reshape(-1, LINE_LENGTH)
er_data = er_data.repeat(REPETITIONS, 0)
er_data = er_data.reshape(rows, REPETITIONS, LINE_LENGTH)


def build_row_square(l, phi):
    x = arange(l)
    r = square((2 * pi) * ((SHUTTER_F * x * PIXEL_T) + phi))/2 + 0.5
    return r > 0.5

# TODO ma non lo uso questo shutter?
shutter = build_row_square(LINE_LENGTH, 0.0)


def pixel_start(pos):
    return pos * PIXEL_T


def pixel_end(pos):
    return (pos + 1) * PIXEL_T

enhanced_data = empty_like(input_data)
print input_data.shape
for (row_n, row) in enumerate(input_data):
    shape = row.shape
    row = row.flat
    enhanced_row = empty_like(row)
    noise = random.normal(5, 1, shape[0]*shape[1])
    er_row = er_data[row_n].flat
    for (pos, val) in ndenumerate(row):
        pos = pos[0]
        start = pixel_start(pos)
        end = pixel_end(pos)
        val += noise[pos]
        # Se non c'è transizione
        if start // SHUTTER_T == end // SHUTTER_T:
            # TODO: per capire on/off mi baso sul modulo due. Non è il massimo!
            if (start // SHUTTER_T) % 2:
                enhanced_row[pos] = val * er_row[pos]
            else:
                enhanced_row[pos] = val
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
                enhanced_row[pos] = phase_before / total_phase * val * er_row[pos] + \
                                     phase_after / total_phase * val
            else:
                enhanced_row[pos] = phase_before / total_phase * val + \
                    phase_after / total_phase * val * er_row[pos]
        s = sqrt(abs(enhanced_row[pos]))
        enhanced_row[pos] += random.uniform(-s, s)
        if enhanced_row[pos] < 0:
            enhanced_row[pos] = 0
    enhanced_data[row_n] = enhanced_row.reshape(shape)
enhanced_data = enhanced_data.reshape(rows * REPETITIONS, LINE_LENGTH)

pylab.imshow(enhanced_data)
pylab.show()

savetxt("out/generated.dat", enhanced_data, fmt="%3.4f0", delimiter="\t")
