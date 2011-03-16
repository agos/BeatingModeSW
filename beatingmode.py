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


class BeatingImageRow(object):
    """Class for a single logical row of a beating image.
        Multiple repetitions are present"""

    def __init__(self, data, pixel_frequency=100.0, shutter_frequency=5.0):
        super(BeatingImageRow, self).__init__()
        self.pixel_frequency = pixel_frequency
        self.shutter_frequency = shutter_frequency
        self.data = data
        self.image_height, self.image_width = self.data.shape
        self.image_size = (self.image_width, self.image_height)
        self.__unbleached_data = None
        self.__beating_mask = None
        self.__phases = None
        self.__central_part_on = None
        self.__central_part_off = None
        self.__reconstructed_on = None
        self.__reconstructed_off = None
        self.__enhancement_ratios = None

    @property
    def unbleached_data(self):
        if self.__unbleached_data is None:

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
            masked_image = dstack((self.data, self.beating_mask))

            def compensate_column_parameters(c):
                column = c[:, 0]
                mask = c[:, 1]

                column_on = array([[position, element] for position, element in enumerate(column) if mask[position]])
                column_off = array([[position, element] for position, element in enumerate(column) if not mask[position]])
                # Trovo parametri bright
                positions = column_on[:, 0]
                samples = column_on[:, 1]
                p0 = [samples.max() - samples.min(), 50, samples.min()]
                try:
                    result = optimize.curve_fit(fitting_function, positions, samples, p0)
                except Exception, e:
                    print e
                    result = (p0,)
                parameters_on = result[0]
                # Trovo parametri dark
                positions = column_off[:, 0]
                samples = column_off[:, 1]
                p0 = [samples.max()- samples.min(), 50, samples.min()]
                try:
                    result = optimize.curve_fit(fitting_function, positions, samples, p0)
                except Exception, e:
                    print e
                    result = (p0,)
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
            self.__unbleached_data = array(map(compensate_column, masked_image.swapaxes(0, 1))).swapaxes(0, 1)
            return self.__unbleached_data
        else:
            return self.__unbleached_data

    @property
    def beating_mask(self):
        if self.__beating_mask is None:
            probe_estimate = empty(self.data.shape, bool)
            # Stima iniziale
            for (position, value) in ndenumerate(self.data):
                probe_estimate[position] = value > self.data[:, position[1]].mean()

            def build_row_square(l, phi):
                x = arange(l)
                r = square((2 * pi) * ((self.shutter_frequency * x * 1/self.pixel_frequency) + phi))/2 + 0.5
                return r > 0.5

            def find_phase(row):
                r = 50
                c = row.shape[0]
                result_matrix = empty((r, c), float)
                for i in range(r):
                    result_matrix[i] = build_row_square(c, i/float(r))
                repeated_row = tile(row, (r, 1))
                error_matrix = abs(result_matrix - repeated_row)
                errors = apply_along_axis(sum, 1, error_matrix)
                e = argmin(errors)
                return e/float(r)
            # Miglioro la stima
            phases = apply_along_axis(find_phase, 1, probe_estimate)
            # Tolgo la ciclicità dalle fasi
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
            # Fit sul progredire delle fasi
            m, b = polyfit(arange(new_phases.shape[0]), new_phases, 1)
            print "Parametri sfasamento: {0}, {1}".format(m, b)
            line = arange(new_phases.shape[0])* m + b
            # Costruiamo finalmente la stima definitiva
            self.__beating_mask = empty_like(probe_estimate)
            l = self.__beating_mask.shape[1]
            for i, phi in enumerate(line):
                self.__beating_mask[i] = build_row_square(l, phi)
            self.__phases = line
            return self.__beating_mask
        else:
            return self.__beating_mask

    # Ora produco altre due matrici simili per prendere solo la parte CENTRALE degli on e degli off
    def build_row_square_subset(self, l, phi, on):
        x = arange(l)
        duty_cycle = 0.1
        r = square((2 * pi) * ((self.shutter_frequency * x / self.pixel_frequency) + phi - (0.5 - duty_cycle)/2 + 0.5 * (not on)), duty_cycle)/2 + 0.5
        return r >= 0.5

    @property
    def central_part_on(self):
        if self.__central_part_on is None:
            self.__central_part_on = empty_like(self.beating_mask)
            l = self.__central_part_on.shape[1]
            for i, phi in enumerate(self.__phases):
                self.__central_part_on[i] = self.build_row_square_subset(l, phi, True)
        return self.__central_part_on

    @property
    def central_part_off(self):
        if self.__central_part_off is None:
            self.__central_part_off = empty_like(self.beating_mask)
            l = self.__central_part_off.shape[1]
            for i, phi in enumerate(self.__phases):
                self.__central_part_off[i] = self.build_row_square_subset(l, phi, False)
        return self.__central_part_off

    @property
    def reconstructed_on(self):
        if self.__reconstructed_on is None:
            width = self.data.shape[1]
            self.__reconstructed_on = empty((width, ), float)
            ratio = empty((width, ), float)
            for i in range(width):
                comp_on = array([item for pos, item in enumerate(self.unbleached_data[:, i]) if self.central_part_on[pos, i]])
                self.__reconstructed_on[i] = comp_on.mean()
        return self.__reconstructed_on

    @property
    def reconstructed_off(self):
        if self.__reconstructed_off is None:
            width = self.data.shape[1]
            self.__reconstructed_off = empty((width, ), float)
            ratio = empty((width, ), float)
            for i in range(width):
                comp_off = array([item for pos, item in enumerate(self.unbleached_data[:, i]) if self.central_part_off[pos, i]])
                self.__reconstructed_off[i] = comp_off.mean()
        return self.__reconstructed_off

    @property
    def enhancement_ratios(self):
        if self.__enhancement_ratios is None:
            self.__enhancement_ratios = self.reconstructed_on / self.reconstructed_off
        return self.__enhancement_ratios


def BeatingImageRowFromPath(path, pixel_frequency=100.0, shutter_frequency=5.0):
    data = genfromtxt(path)
    data = data[:, 1:]
    return BeatingImageRow(data, pixel_frequency, shutter_frequency)


class BeatingImage(object):
    """docstring for BeatingImage"""
    def __init__(self, path, repetitions, pixel_frequency=100.0, shutter_frequency=5.856):
        super(BeatingImage, self).__init__()
        self.path = path
        self.pixel_frequency = pixel_frequency
        self.shutter_frequency = shutter_frequency
        self.data = genfromtxt(path)
        self.data = self.data[:, 1:]
        self.width = self.data.shape[1]
        self.data = self.data.reshape(-1,repetitions, self.width)
        self.rows = self.data.shape[0]
        print self.data.shape
        self.__reconstructed_on = None
        self.__reconstructed_off = None

    @property
    def reconstructed_on(self):
        if self.__reconstructed_on is None:
            self.__reconstructed_on = empty((self.rows, self.width), float)
            for row in xrange(self.rows):
                print "Creo riga {0}".format(row)
                beatingrow = BeatingImageRow(self.data[row,:,:], pixel_frequency=self.pixel_frequency, shutter_frequency=self.shutter_frequency)
                self.__reconstructed_on[row] = beatingrow.reconstructed_on
        return self.__reconstructed_on

if __name__ == '__main__':

    beatingrow = BeatingImageRowFromPath("dati/dati.dat", shutter_frequency=9.78/2)
    # beatingrow = BeatingImageRowFromPath("dati/misura03.dat", shutter_frequency=5.856/2)

    my_color_map = LinearSegmentedColormap("stdGreen",
                    {
                    'red': [(0.0, 0.0, 0.0),
                           (1.0, 0.0, 0.0)],
                   'green': [(0.0, 0.0, 0.0),
                             (1.0, 1.0, 1.0)],
                   'blue': [(0.0, 0.0, 0.0),
                            (1.0, 0.0, 0.0)],
                    })

    print "Dimensioni immagine (lxh): ", beatingrow.image_size
    print "Max: ", beatingrow.data.max()
    print "Min: ", beatingrow.data.min()

    pylab.figure(1)
    h, w = 3, 3
    pylab.subplot(h, w, 1)
    first_image = pylab.imshow(beatingrow.data, cmap=my_color_map)
    first_image.set_interpolation('nearest')
    pylab.title('Immagine originale')

    pylab.subplot(h, w, 2)
    estimate_plot = pylab.imshow(beatingrow.beating_mask, cmap=pylab.get_cmap("gray"))
    estimate_plot.set_interpolation('nearest')
    pylab.title('Stima ON/OFF media')

    pylab.subplot(h, w, 4)
    pylab.title('Sample verticale')
    pylab.xlabel('Distanza')
    pylab.ylabel('Valore')

    col_n = 50
    pylab.plot(beatingrow.data[:,col_n])
    pylab.plot(beatingrow.unbleached_data[:, col_n])

    pylab.subplot(h, w, 6)
    corrected_image = pylab.imshow(beatingrow.unbleached_data, cmap=my_color_map)
    corrected_image.set_interpolation('nearest')
    pylab.title('Immagine corretta per il bleaching')

    pylab.subplot(h, w, 7)
    pylab.plot(beatingrow.reconstructed_on)
    pylab.plot(beatingrow.reconstructed_off)

    pylab.subplot(h, w, 8)
    pylab.plot(beatingrow.enhancement_ratios)

    pylab.show()
