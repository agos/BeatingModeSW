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

savetxt("out/reconstructed.dat", beatingimage.reconstructed_on, fmt="%3.4f0")
reconstructed_on_image = pylab.imshow(beatingimage.reconstructed_on, cmap=my_color_map)
reconstructed_on_image.set_interpolation('nearest')
pylab.show()