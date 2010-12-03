#!/usr/bin/python
# -*- coding: utf-8 -*-

import pylab
import itertools
import sys
from math import pi
import csv
from numpy import *
from scipy import optimize
from scipy.signal import square
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import cbook
import functools
from itertools import product

DEBUG_COLUMNS_FIT = False


if __name__ == '__main__':

    image_data = genfromtxt("dati/dati.dat")
    SHUTTER_F = 9.78 / 2
    # image_data = genfromtxt("dati/misura03.dat")
    # SHUTTER_F = 5.856 / 2

    image_data = image_data[:, 1:]

    PIXEL_F = 100.0
    TAU_P = 1 / PIXEL_F


    def phi_pixel(x, phi0):
        r = modf((x * TAU_P + phi0 * 1.0 / SHUTTER_F) / (1.0 / SHUTTER_F))
        return r[0]


    def probe(x, phi0):
        return phi_pixel(x, phi0) < 0.5


    def build_row(l, phi):
        x = arange(l)
        r = modf((x * TAU_P + phi / SHUTTER_F) / (1.0 / SHUTTER_F))
        return r[0]


    def build_row_square(l, phi):
        x = arange(l)
        r = square((2 * pi) * ((SHUTTER_F * x * TAU_P) + phi))/2 + 0.5
        return r > 0.5

    # Costruisco l'istogramma
    # TODO provare con bincount o addirittura histogram
    #distribution = {}
    #for value in image_data.flat:
        #    curr_count = distribution.setdefault(value, 0)
        #    distribution[value] += 1
    # Plotting
    # keys = distribution.keys()
    # keys.sort()
    # values = [distribution[key] for key in keys]

    def swap((x, y)):
        return (y, x)

    image_height, image_width = image_data.shape
    image_size = (image_width, image_height)

    print "Dimensioni immagine (lxh): ", image_size
    print "Max: ", image_data.max()
    print "Min: ", image_data.min()

    probe_estimate = empty(image_data.shape, bool)
    for (position, value) in ndenumerate(image_data):
        probe_estimate[position] = value > image_data[position[0], :].mean()

    segmentdata = {'red': [(0.0, 0.0, 0.0),
                           (1.0, 0.0, 0.0)],
                   'green': [(0.0, 0.0, 0.0),
                             (1.0, 1.0, 1.0)],
                   'blue': [(0.0, 0.0, 0.0),
                            (1.0, 0.0, 0.0)],
    }

    my_color_map = LinearSegmentedColormap("stdGreen", segmentdata)

    pylab.figure(1)
    h, w = 3, 3
    pylab.subplot(h, w, 1)
    first_image = pylab.imshow(image_data, cmap=my_color_map)
    first_image.set_interpolation('nearest')
    pylab.title('Immagine originale')

    pylab.subplot(h, w, 2)
    estimate_plot = pylab.imshow(probe_estimate, cmap=pylab.get_cmap("gray"))
    estimate_plot.set_interpolation('nearest')
    pylab.title('Stima ON/OFF media')


    def fit_row(row):
        r = 50
        c = 99
        result_matrix = empty((r, c), float)
        for i in range(r):
            result_matrix[i] = build_row_square(c, i/float(r))
        repeated_row = tile(row, (r, 1))
        error_matrix = abs(result_matrix - repeated_row)
        errors = apply_along_axis(sum, 1, error_matrix)
        e = argmin(errors)
        return result_matrix[e]


    def find_phase(row):
        r = 50
        c = 99
        result_matrix = empty((r, c), float)
        # TODO inserire logbook!
        for i in range(r):
            result_matrix[i] = build_row_square(c, i/float(r))
        repeated_row = tile(row, (r, 1))
        error_matrix = abs(result_matrix - repeated_row)
        errors = apply_along_axis(sum, 1, error_matrix)
        e = argmin(errors)
        return e/float(r)

    print "Miglioro la stima...",

    phases = apply_along_axis(find_phase, 1, probe_estimate)
    new_phases = empty_like(phases)
    for n, p in enumerate(phases):
        if n == 0:
            new_phases[n] = phases[n]
        else:
            a = phases[n]
            while abs(a - new_phases[n-1]) >= 0.5:
                if a > new_phases[n-1]:
                    a -= 1
                else:
                    a += 1
            new_phases[n] = a

    m, b = polyfit(arange(new_phases.shape[0]), new_phases, 1)
    line = arange(new_phases.shape[0])* m + b

    #better_estimate = probe_estimate
    # better_estimate = apply_along_axis(fit_row, 1, probe_estimate)

    better_estimate = empty_like(probe_estimate)
    l = better_estimate.shape[1]
    for i, phi in enumerate(line):
        better_estimate[i] = build_row_square(l, phi)

    print "fatto!"

    # Ora produco altre due matrici simili per prendere solo la parte CENTRALE degli on e degli off

    def build_row_square_subset(l, phi, on):
        x = arange(l)
        duty_cycle = 0.1
        r = square((2 * pi) * ((SHUTTER_F * x * TAU_P) + phi - (0.5 - duty_cycle)/2 + 0.5 * (not on)), duty_cycle)/2 + 0.5
        return r >= 0.5

    central_part_on = empty_like(probe_estimate)
    l = central_part_on.shape[1]
    for i, phi in enumerate(line):
        central_part_on[i] = build_row_square_subset(l, phi, True)

    central_part_off = empty_like(probe_estimate)
    l = central_part_off.shape[1]
    for i, phi in enumerate(line):
        central_part_off[i] = build_row_square_subset(l, phi, False)

    pylab.subplot(h, w, 3)
    pylab.title('Stima ON/OFF fit periodico su prima stima')
    imgplot2 = pylab.imshow(better_estimate, cmap=pylab.get_cmap("gray"))
    imgplot2.set_interpolation('nearest')


    # Sezione fit esponenziale

    def fitting_function(x, a, b, c):
        return  a * (exp(-1.0 * x / b)) + c


    def exponential(x, p):
        return fitting_function(x, p[0], p[1], p[2])


    def compensate(measurement, p, column_length):
        x = measurement[0]
        y = measurement[1]
        low = exponential(column_length, p)
        return [x, y - (exponential(x, p) - low)]

    masked_image = dstack((image_data, better_estimate))


    def compensate_column_parameters(c):
        column = c[:, 0]
        mask = c[:, 1]

        column_on = array([[position, element] for position, element in enumerate(column) if mask[position]])
        column_off = array([[position, element] for position, element in enumerate(column) if not mask[position]])
        # Trovo parametri bright
        positions = column_on[:, 0]
        samples = column_on[:, 1]
        p0 = [samples.max() - samples.min(), 50, samples.min()]
        result = optimize.curve_fit(fitting_function, positions, samples, p0)
        parameters_on = result[0]
        # Trovo parametri dark
        positions = column_off[:, 0]
        samples = column_off[:, 1]
        p0 = [samples.max()- samples.min(), 50, samples.min()]
        result = optimize.curve_fit(fitting_function, positions, samples, p0)
        parameters_off = result[0]
        # Compenso
        compensated_off = array([compensate(item, parameters_off, column.shape[0]) for item in column_off])
        compensated_on = array([compensate(item, parameters_on, column.shape[0]) for item in column_on])
        c = concatenate((compensated_on, compensated_off))
        i = c[:, 0]
        c = c[:, 1]
        ind = i.argsort(axis=0)
        return (c[ind], parameters_on, parameters_off)


    def compensate_column(c):
        r = compensate_column_parameters(c)
        return r[0]

    # Compenso una colonna singola

    pylab.subplot(h, w, 4)
    pylab.title('Sample verticale')
    pylab.xlabel('Distanza')
    pylab.ylabel('Valore')

    col_n = 50

    sample_verticale = image_data[:, col_n]
    pylab.plot(sample_verticale)

    sample_verticale_mask = better_estimate[:, col_n]
    column = vstack((sample_verticale, sample_verticale_mask)).swapaxes(0, 1)

    compensated, p1, p2 = compensate_column_parameters(column)
    print "Valori ottimizzazione sample ON: ", p1

    time = arange(image_height)
    fit_values = exponential(time, p1)
    pylab.plot(time, fit_values)

    print "Valori ottimizzazione sample OFF: ", p2
    time = arange(image_height)
    fit_values = exponential(time, p2)
    pylab.plot(time, fit_values)


    # Compenso tutta l'immagine

    compensated_image = array(map(compensate_column, masked_image.swapaxes(0, 1))).swapaxes(0, 1)

    pylab.subplot(h, w, 6)
    corrected_image = pylab.imshow(compensated_image, cmap=my_color_map)
    corrected_image.set_interpolation('nearest')
    pylab.title('Immagine corretta per il bleaching')

    pylab.subplot(h, w, 5)
    compensated_column = compensated_image[:, col_n]
    pylab.plot(compensated_column)

    column_center_mask_on = central_part_on[:, col_n]
    compensated_column_center_on = array([[pos, item] for pos, item in enumerate(compensated_column) if column_center_mask_on[pos]])
    pylab.plot(compensated_column_center_on[:, 0], compensated_column_center_on[:, 1])

    column_center_mask_off = central_part_off[:, col_n]
    compensated_column_center_off = array([[pos, item] for pos, item in enumerate(compensated_column) if column_center_mask_off[pos]])
    pylab.plot(compensated_column_center_off[:, 0], compensated_column_center_off[:, 1])

    print "Calcolo enhancement ratio (per colonna 50)"
    print "Media ON:",
    print compensated_column_center_on[:, 1].mean()
    print "Media OFF:",
    print compensated_column_center_off[:, 1].mean()
    print "Rapporto di enhancement:",
    print compensated_column_center_on[:, 1].mean() / compensated_column_center_off[:, 1].mean()

    width = compensated_image.shape[1]
    image_on = empty((width, ), float)
    image_off = empty((width, ), float)
    ratio = empty((width, ), float)

    for i in range(width):
        compensated_column = compensated_image[:, i]
        compensated_column_center_on = array([item for pos, item in enumerate(compensated_column) if central_part_on[pos, i]])
        on = compensated_column_center_on.mean()
        image_on[i] = on
        compensated_column_center_off = array([item for pos, item in enumerate(compensated_column) if central_part_off[pos, i]])
        off = compensated_column_center_off.mean()
        image_off[i] = off
        ratio[i] = on / off

    pylab.subplot(h, w, 7)
    pylab.plot(image_on)
    pylab.plot(image_off)

    pylab.subplot(h, w, 8)
    pylab.plot(ratio)

    if DEBUG_COLUMNS_FIT:
        # Seconda figura, per i grafici dei fit delle colonne
        pylab.figure(2)
        print "Inizio a scrivere i grafici dei fit delle colonne...",
        sys.stdout.flush()
        parameters_list = empty((image_data.shape[1], 6), float)
        for i in range(image_data.shape[1]):
            sample_verticale = image_data[:, i]
            pylab.plot(sample_verticale)
            sample_verticale_mask = better_estimate[:, i]
            column = vstack((sample_verticale, sample_verticale_mask)).swapaxes(0, 1)
            compensated, p1, p2 = compensate_column_parameters(column)
            time = arange(image_height)
            fit_values_on = exponential(time, p1)
            pylab.plot(time, fit_values_on)
            fit_values_off = exponential(time, p2)
            pylab.plot(time, fit_values_off)
            pylab.plot(compensated)
            filename = "out/fitcolonna{0:02d}.png".format(i)
            pylab.savefig(filename)
            pylab.clf()
            parameters_list[i] = append(array(p1), p2)
        pylab.close()
        writer = csv.writer(open("out/parametri_fit_esponenziale.csv", "wb"), delimiter="\t")
        writer.writerows(parameters_list)
        pylab.figure(1)
        print "fatto!"

    pylab.show()
