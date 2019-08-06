#!/usr/bin/env python2
"""
Example script to run the gwyddion preprocessing
and save the data in python3-compatible hickle (i.e. hdf5)
"""

import os
import pickle
import subprocess

import hickle

path = './data/'
threshold = 3.0
min_area=200e-9
min_deviation=0.5
max_deviation=1.5

command = [
    'python2', 'gwy_analyser/gwy_process.py', path,
    '-t', str(threshold),
    '--min-area', str(min_area),
    '--min-deviation', str(min_deviation),
    '--max-deviation', str(max_deviation)]
subprocess.call(command)

with open(os.path.join(path, 'all_data.pkl'), 'rb') as f:
    data = pickle.load(f, encoding='latin1')

hickle.dump(data, os.path.join(path,'afm-data.hkl'), mode='w', compression='lzf')
