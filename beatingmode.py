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
import yaml
from colors import rate_color_map, ratio_color_map, gray_color_map
import argparse

DEBUG_COLUMNS_FIT = False
_ncpus = 1
_ncpus = multiprocessing.cpu_count()
print("Detected {0} CPUs".format(_ncpus))

SETTING_CENTRAL_CROP = False
SETTING_PARALLEL_PROCESSING = True
seterr(over='ignore')


def reconstruct(row):
    width = row.data.shape[1]
    reconstructed_on = empty((width, ), float)
    reconstructed_off = empty((width, ), float)
    for i in range(width):
        comp_on = array([item for pos, item in enumerate(
            row.unbleached_data[:, i]) if row.central_part_on[pos, i]])
        reconstructed_on[i] = comp_on.mean()
        comp_off = array([item for pos, item in enumerate(
            row.unbleached_data[:, i]) if row.central_part_off[pos, i]])
        reconstructed_off[i] = comp_off.mean()
    return (reconstructed_on, reconstructed_off)


def reconstruct_row_update(p):
    # TODO unificare con il metodo di cui sopra?
    row = p[0]
    queue = p[1]
    index = p[2]
    width = row.data.shape[1]
    reconstructed_on = empty((width, ), float)
    reconstructed_off = empty((width, ), float)
    for i in range(width):
        comp_on = array([item for pos, item in enumerate(
            row.unbleached_data[:, i]) if row.central_part_on[pos, i]])
        reconstructed_on[i] = comp_on.mean()
        comp_off = array([item for pos, item in enumerate(
            row.unbleached_data[:, i]) if row.central_part_off[pos, i]])
        reconstructed_off[i] = comp_off.mean()
    queue.put((index, reconstructed_on, reconstructed_off,
        row.unbleached_data, row.taus))
    return (index, reconstructed_on, reconstructed_off,
        row.unbleached_data, row.taus)


class BeatingImageRow(object):
    """Class for a single logical row of a beating image.
        Multiple repetitions are present"""

    # TODO cambiare i __ con _
    def __init__(self, data, pixel_frequency=100.0, shutter_frequency=5.0,
        no_bleach=False):
        super(BeatingImageRow, self).__init__()
        self.pixel_frequency = pixel_frequency
        self.shutter_frequency = shutter_frequency
        self.data = data
        self.no_bleach = no_bleach
        self.image_height, self.image_width = self.data.shape
        self.image_size = (self.image_width, self.image_height)
        self.__unbleached_data = None
        self.__beating_mask = None
        self.__phases = None
        self.__central_part_on = None
        self.__central_part_off = None
        self._rec_on = None
        self._rec_off = None
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

            def compensate_column_parameters(c):
                c_on = ma.array(c.data, mask=~c.mask)
                c_off = c
                samples = arange(c.shape[0])
                val_on = c_on.compressed()
                val_off = c_off.compressed()
                pos_on = samples[c.mask]
                pos_off = samples[~c.mask]
                # Trovo parametri bright
                p0 = [val_on.max() - val_on.min(), 50, val_on.min()]
                failed = False
                try:
                    result = optimize.curve_fit(
                        fitting_function, pos_on, val_on, p0)
                except Exception, e:
                    failed = True
                if not failed:
                    a, b, c = parameters_on = result[0]
                    if any(parameters_on > 1000) or a < 0 or c < 0 or a < c:
                        failed = True
                if not failed:
                    expo = exponential(samples, parameters_on)
                    comp_on = (c_on - expo + expo.min())
                else:
                    parameters_on = [nan] * 3
                    comp_on = c_on
                # Trovo parametri dark
                p0 = [val_off.max() - val_off.min(), 50, val_off.min()]
                failed = False
                try:
                    result = optimize.curve_fit(
                        fitting_function, pos_off, val_off, p0)
                except Exception, e:
                    failed = True
                if not failed:
                    a,b,c = parameters_off = result[0]
                    if any(parameters_off > 1000) or a < 0 or c < 0 or a < c:
                        failed = True
                if not failed:
                    expo = exponential(samples, parameters_off)
                    comp_off = (c_off - expo + expo.min())
                else:
                    parameters_off = [nan] * 3
                    comp_off = c_off

                c = comp_on.filled(0) + comp_off.filled(0)
                return (c, parameters_on, parameters_off)

            if not self.no_bleach:
                masked_data = ma.array(self.data, mask=self.beating_mask)
                # TODO vedi vettorizzare di sopra
                comp_data = map(compensate_column_parameters, masked_data.T)
                comp_cols = [r[0] for r in comp_data]
                self.taus = [(r[1][1] + r[2][1]) / 2 for r in comp_data]
                self.__unbleached_data = array(comp_cols).T
            else:
                self.__unbleached_data = self.data
                self.taus = [nan] * self.data.shape[1]
            return self.__unbleached_data
        else:
            return self.__unbleached_data

    @property
    def beating_mask(self):
        if self.__beating_mask is None:
            # Stima iniziale
            probe_estimate = apply_along_axis(
                lambda c: c > c.mean(), 0, self.data)

            def build_row_square(l, phi):
                x = arange(l)
                shut_f = self.shutter_frequency
                pix_f = self.pixel_frequency
                r = square((2 * pi) * ((shut_f * x * 1 / pix_f) + phi))/2 + 0.5
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
            # TODO supervettorizzare
            for i in range(r):
                result_matrix[i] = build_row_square(c, i/float(r))
            # Miglioro la stima
            phases = apply_along_axis(find_phase, 1, probe_estimate)
            # Tolgo la ciclicità dalle fasi
            new_phases = empty_like(phases)
            # TODO cos'è sto schifo
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
            (m, b, fit_r_val, p_val, fit_stderr) = stats.linregress(
                arange(new_phases.shape[0]), new_phases)
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

    # Ora produco altre due matrici simili per prendere solo
    # la parte CENTRALE degli on e degli off
    def row_subset(self, l, phi, on, duty_cycle):
        x = arange(l)
        shut_f = self.shutter_frequency
        pix_f = self.pixel_frequency
        # TODO andrebbe riordinata, e magari unita con quella sopra
        r = square((2 * pi) *
            ((shut_f * x / pix_f) +
            phi - (0.5 - duty_cycle)/2 + 0.5 * (not on)), duty_cycle)/2 + 0.5
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
                part = self.row_subset(l, phi, True, duty_cycle)
                self.__central_part_on[i] = part
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
                part = self.row_subset(l, phi, False, duty_cycle)
                self.__central_part_off[i] = part
        return self.__central_part_off


class BeatingImage(object):
    """docstring for BeatingImage"""

    def __init__(self, path, no_bleach=False):
        super(BeatingImage, self).__init__()
        self.no_bleach = no_bleach
        self.path = path
        input = open(path, 'r').read().split('---')
        y = yaml.load(input[0])
        self.acquired = y['acquired']
        self.repetitions = y['repetitions']
        self.shutter_frequency = y['shutter_frequency']
        self.pixel_frequency = y['pixel_frequency']
        self.h_step = y['h_step']
        self.w_step = y['w_step']
        header_length = len(input[0].split('\n'))
        self.data = loadtxt(path, skiprows=header_length)
        self.data = self.data[:, 1:]
        self.width = self.data.shape[1]
        self.data = self.data.reshape(-1, self.repetitions, self.width)
        self.height = self.data.shape[0]
        print("Rows, repetitions, columns: {0}".format(self.data.shape))
        self._rec_on = None
        self._rec_off = None
        self._ratios = None
        self.thresOn = 0.0
        self.thresOff = 0.0
        self.rows = []
        self.rows = [BeatingImageRow(self.data[row,:,:],
            pixel_frequency=self.pixel_frequency,
            shutter_frequency=self.shutter_frequency,
            no_bleach=no_bleach)
                for row in xrange(self.height)]

    def _reconstruct_rows(self):
        self._rec_on = empty((self.height, self.width), float)
        self._rec_off = empty((self.height, self.width), float)
        start = time.time()
        if SETTING_PARALLEL_PROCESSING:
            pool = multiprocessing.Pool(processes=_ncpus)
            reconstructed = pool.map(reconstruct, self.rows)
            pool.close()
            pool.join()
        else:
            reconstructed = map(reconstruct, self.rows)
        for index, row in enumerate(reconstructed):
            (self._rec_on[index], self._rec_off[index]) = reconstructed[index]
        print("Time to reconstruct: {0} s".format(time.time() - start))

    def reconstruct_with_update(self, queue, dialog):
        self._rec_on = empty((self.height, self.width), float)
        self._rec_off = empty((self.height, self.width), float)
        self._taus = empty((self.height, self.width), float)
        start = time.time()
        l = len(self.rows)
        if SETTING_PARALLEL_PROCESSING:
            pool = multiprocessing.Pool(processes=_ncpus)
            results = pool.map_async(reconstruct_row_update,
                [(x,queue,i) for (i,x) in enumerate(self.rows)])
            value = 0
            dialog.Update(value, newmsg="Reconstructing rows: 0/{0}".format(l))
            self.unbleached_array = empty((l, self.repetitions, self.width))
            for n in range(l):
                result = queue.get()
                i = result[0]
                self._rec_on[i], self._rec_off[i] = result[1], result[2]
                value += 100.0/l
                self.unbleached_array[i] = result[3]
                self._taus[i] = result[4]
                dialog.Update(value,
                    newmsg="Reconstructing rows: {0}/{1}".format(n+1, l))
        else:
            results = map(reconstruct_row_update,
                [(x,queue,i) for (i,x) in enumerate(self.rows)])
            self.unbleached_array = empty((l, self.repetitions, self.width))
            value = 0
            for n, result in enumerate(results):
                result = queue.get()
                i = result[0]
                self._rec_on[i], self._rec_off[i] = result[1], result[2]
                value += 100.0/l
                self.unbleached_array[i] = result[3]
                self._taus[i] = result[4]
                dialog.Update(value,
                    newmsg="Reconstructing rows: {0}/{1}".format(n+1, l))
        print("Time to reconstruct: {0} s".format(time.time() - start))
        return results

    @property
    def reconstructed_on(self):
        if self._rec_on is None:
            self._reconstruct_rows()
        return ma.array(self._rec_on, mask=less(self._rec_on, self.thresOn))

    @property
    def reconstructed_off(self):
        if self._rec_off is None:
            self._reconstruct_rows()
        return ma.array(self._rec_off, mask=less(self._rec_off, self.thresOff))

    @property
    def ratios(self):
        # TODO implementare caching
        return self.reconstructed_on / self.reconstructed_off

    @property
    def taus(self):
        pixel_t = 1000 / self.pixel_frequency
        mask = ma.logical_or(
                 ma.logical_or(
                   self.reconstructed_on.mask,
                   self.reconstructed_off.mask),
                 isnan(self._taus))
        return ma.array(self._taus, mask=mask) * pixel_t


if __name__ == '__main__':
    description = 'A tool to do multi-row beating mode images reconstruction'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('path', metavar='PATH', nargs=1,
                            help='the path for the scan file')
    args = parser.parse_args()

    bimg = BeatingImage(path=args.path[0])
    rec_on = bimg.reconstructed_on
    rec_off = bimg.reconstructed_off
    ratios = bimg.ratios
    max_rate = max(rec_on.max(), rec_off.max())

    print("Immagine ricostruita: {0}".format(rec_on.shape))
    print("Valore massimo: {0}".format(max_rate))

    savetxt("out/reconstructed_on.dat", rec_on, fmt="%10.5f", delimiter="\t")
    savetxt("out/reconstructed_off.dat", rec_off, fmt="%10.5f", delimiter="\t")
    savetxt("out/enhancement_ratios.dat", ratios, fmt="%10.5f", delimiter="\t")

    pylab.subplot(2, 2, 1)
    pylab.imshow(rec_on, cmap=rate_color_map,
        interpolation='nearest', vmin=0.0, vmax=max_rate)
    pylab.subplot(2, 2, 2)
    pylab.imshow(rec_off, cmap=rate_color_map,
        interpolation='nearest', vmin=0.0, vmax=max_rate)
    pylab.colorbar()
    pylab.subplot(2, 2, 3)
    pylab.imshow(ratios, cmap=ratio_color_map, interpolation='nearest')
    pylab.colorbar()

    pylab.show()
