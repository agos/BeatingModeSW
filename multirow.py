#!/usr/bin/python
# -*- coding: utf-8 -*-

from numpy import *
import pylab
from matplotlib.colors import LinearSegmentedColormap
from beatingmode import BeatingImageRow, BeatingImage

my_color_map = LinearSegmentedColormap("stdGreen",
                {
                'red': [(0.0, 0.0, 0.0),
                       (1.0, 0.0, 0.0)],
               'green': [(0.0, 0.0, 0.0),
                         (1.0, 1.0, 1.0)],
               'blue': [(0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0)],
                })

beatingimage = BeatingImage(path="dati/samp6.dat", repetitions=90, shutter_frequency=5.856/2)

print beatingimage.reconstructed_on.shape

savetxt("out/reconstructed_on.dat", beatingimage.reconstructed_on, fmt="%3.4f0")
savetxt("out/reconstructed_off.dat", beatingimage.reconstructed_off, fmt="%3.4f0")
savetxt("out/enhancement_ratios.dat", beatingimage.ratios, fmt="%3.4f0")

pylab.subplot(2,2,1)
reconstructed_on_image = pylab.imshow(beatingimage.reconstructed_on, cmap=my_color_map)
reconstructed_on_image.set_interpolation('nearest')

pylab.subplot(2,2,2)
reconstructed_off_image = pylab.imshow(beatingimage.reconstructed_off, cmap=my_color_map)
reconstructed_off_image.set_interpolation('nearest')

pylab.subplot(2,2,3)
enhancement_ratios_image = pylab.imshow(beatingimage.ratios, cmap=my_color_map)
enhancement_ratios_image.set_interpolation('nearest')

pylab.show()
