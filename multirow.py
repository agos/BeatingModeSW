#!/usr/bin/python
# -*- coding: utf-8 -*-

from beatingmode import BeatingImageRow, BeatingImage

beatingimage = BeatingImage(path="dati/samp6.dat", repetitions=90, shutter_frequency=5.856/2)

print beatingimage.reconstructed_on.shape
