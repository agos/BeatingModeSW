#!/usr/bin/python
# -*- coding: utf-8 -*-

import pylab
import time
import itertools
import sys
from math import pi
import csv
from numpy import *
from scipy import optimize
from scipy import stats
from scipy.signal import square
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import cbook
import functools
from itertools import product
import multiprocessing

DEBUG_COLUMNS_FIT = False
_ncpus = 1
_ncpus = multiprocessing.cpu_count()
print("CPU rilevate: {0}".format(_ncpus))

SETTING_CENTRAL_CROP = False
SETTING_PARALLEL_PROCESSING = True
seterr(over='ignore')


def reconstruct(row):
    width = row.data.shape[1]
    reconstructed_on = empty((width, ), float)
    reconstructed_off = empty((width, ), float)
    for i in range(width):
        comp_on = array([item for pos, item in enumerate(row.unbleached_data[:, i]) if row.central_part_on[pos, i]])
        reconstructed_on[i] = comp_on.mean()
        comp_off = array([item for pos, item in enumerate(row.unbleached_data[:, i]) if row.central_part_off[pos, i]])
        reconstructed_off[i] = comp_off.mean()
    return (reconstructed_on, reconstructed_off)


class BeatingImageRow(object):
    """Class for a single logical row of a beating image.
        Multiple repetitions are present"""

    # TODO cambiare i __ con _
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
                failed = False
                try:
                    result = optimize.curve_fit(fitting_function, positions, samples, p0)
                except Exception, e:
                    # print e
                    failed = True
                if not failed:
                    parameters_on = result[0]
                    if any(parameters_on > 1000) or parameters_on[0] < 0 or parameters_on[2] < 0 or parameters_on[0] < parameters_on[2]:
                        failed = True
                if not failed:
                    # print("Compenso con parametri {0}".format(parameters_on))
                    compensated_on = array([compensate(item, parameters_on, column.shape[0]) for item in column_on])
                else:
                    parameters_on = (p0,)
                    compensated_on = column_on
                # Trovo parametri dark
                positions = column_off[:, 0]
                samples = column_off[:, 1]
                p0 = [samples.max()- samples.min(), 50, samples.min()]
                failed = False
                try:
                    result = optimize.curve_fit(fitting_function, positions, samples, p0)
                except Exception, e:
                    # print e
                    failed = True
                if not failed:
                    parameters_off = result[0]
                    if any(parameters_off > 1000) or parameters_off[0] < 0 or parameters_off[2] < 0 or parameters_off[0] < parameters_off[2]:
                        failed = True
                if not failed:
                    # print("Compenso con parametri {0}".format(parameters_off))
                    compensated_off = array([compensate(item, parameters_off, column.shape[0]) for item in column_off])
                else:
                    parameters_off = (p0,)
                    compensated_off = column_off
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
                repeated_row = tile(row, (r, 1))
                error_matrix = abs(result_matrix - repeated_row)
                errors = apply_along_axis(sum, 1, error_matrix)
                e = argmin(errors)
                return e/float(r)

            r = 50
            c = probe_estimate.shape[1]
            result_matrix = empty((r, c), float)
            for i in range(r):
                result_matrix[i] = build_row_square(c, i/float(r))
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
            (m, b, fit_r_value, fit_p_value, fit_stderr) = stats.linregress(arange(new_phases.shape[0]), new_phases)
            # print "Parametri sfasamento: {0}, {1}".format(m, b)
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
    def build_row_square_subset(self, l, phi, on, duty_cycle):
        x = arange(l)
        r = square((2 * pi) * ((self.shutter_frequency * x / self.pixel_frequency) + phi - (0.5 - duty_cycle)/2 + 0.5 * (not on)), duty_cycle)/2 + 0.5
        return r >= 0.5

    @property
    def central_part_on(self):
        if self.__central_part_on is None:
            if SETTING_CENTRAL_CROP:
                duty_cycle = 0.1
            else:
                duty_cycle = 0.5
            self.__central_part_on = empty_like(self.beating_mask)
            l = self.__central_part_on.shape[1]
            for i, phi in enumerate(self.__phases):
                self.__central_part_on[i] = self.build_row_square_subset(l, phi, True, duty_cycle)
        return self.__central_part_on

    @property
    def central_part_off(self):
        if self.__central_part_off is None:
            if SETTING_CENTRAL_CROP:
                duty_cycle = 0.1
            else:
                duty_cycle = 0.5
            self.__central_part_off = empty_like(self.beating_mask)
            l = self.__central_part_off.shape[1]
            for i, phi in enumerate(self.__phases):
                self.__central_part_off[i] = self.build_row_square_subset(l, phi, False, duty_cycle)
        return self.__central_part_off


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
        self.height = self.data.shape[0]
        print self.data.shape
        self.__reconstructed_on = None
        self.__reconstructed_off = None
        self._ratios = None
        self.rows = []
        self.rows = [BeatingImageRow(self.data[row,:,:], pixel_frequency=self.pixel_frequency, shutter_frequency=self.shutter_frequency) for row in xrange(self.height)]

    def _reconstruct_rows(self):
        self.__reconstructed_on = empty((self.height, self.width), float)
        self.__reconstructed_off = empty((self.height, self.width), float)
        start = time.time()
        if SETTING_PARALLEL_PROCESSING:
            pool = multiprocessing.Pool(processes=_ncpus)
            reconstructed = pool.map(reconstruct, self.rows)
            pool.close()
            pool.join()
        else:
            reconstructed = map(reconstruct, self.rows)
        for index, row in enumerate(reconstructed):
            (self.__reconstructed_on[index], self.__reconstructed_off[index]) = reconstructed[index]
        print("Tempo impiegato: {0}".format(time.time()- start))

    @property
    def reconstructed_on(self):
        if self.__reconstructed_on is None:
            self._reconstruct_rows()
        return self.__reconstructed_on

    @property
    def reconstructed_off(self):
        if self.__reconstructed_off is None:
            self._reconstruct_rows()
        return self.__reconstructed_off

    @property
    def ratios(self):
        if self._ratios is None:
            self._ratios = empty((self.height, self.width), float)
            # self._ratios = ma.masked_less(self.__reconstructed_on, 20.0)
            # self._ratios.harden_mask()
            for index, row in enumerate(self.rows):
                self._ratios[index] = self.__reconstructed_on[index] / self.__reconstructed_off[index]
        return self._ratios


if __name__ == '__main__':

    # beatingrow = BeatingImageRowFromPath("dati/dati.dat", shutter_frequency=9.78/2)
    # beatingrow = BeatingImageRowFromPath("dati/misura03.dat", shutter_frequency=5.856/2)
    # beatingimage = BeatingImage(path="dati/generated.dat", repetitions=15, shutter_frequency=9.78/2)

    beatingimage = BeatingImage(path="dati/samp6.dat", repetitions=90, shutter_frequency=5.865/2)
    beatingrow = BeatingImageRow(data=beatingimage.data[3,:,:], pixel_frequency=100.0, shutter_frequency=5.865 / 2)

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
