#!/usr/bin/env python2
"""
Script to process data using gwyddion and own methods
Then export this in a pickle object to import using
python 3 to do analysis on processed data.

Unlike previous scripts remove *all* saving of images
as this is done better later on with modern cmaps etc.
"""
from __future__ import print_function

import argparse
import os
import pickle

import numpy as np
import pandas as pd
from pandas.io.json import json_normalize

from glib import GError
from gwy_analyser import afmAnalyser
from pathlib2 import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help='directory path to files')
    parser.add_argument("--filetypes", help='afm filetypes to choose', type=str, default='spm')
    parser.add_argument("-t", "--threshold", help='threshold used to mask outliers', type=float, default=0.5)
    parser.add_argument("--min-area", help='minimum grain area', type=float, default=400e-9)
    parser.add_argument("--min-deviation", help='allowable deviation from median px size', type=float, default=0.8)
    parser.add_argument("--max-deviation", help='allowable deviation from median px size', type=float, default=1.5)
    parser.add_argument("--crop-width", help='size of cropped window', type=float, default=100e-9)
    parser.add_argument("--contour-length", help='contour length in bp', type=int, default=302)
    parser.add_argument("--save-all", help='create a single pkl file', action='store_true')

    args = parser.parse_args()

    # Find files in directory if given
    path = Path(args.path)
    if path.is_file():
        spm_files = [args.path]
        args.path = os.path.dirname(args.path)
    else:
        spm_files = []
        for file_ext in args.filetypes.split(','):
            for filename in path.glob('*.' + file_ext):
                spm_files.append(str(filename.absolute()))
        print(len(spm_files), "files found")

    data_exports = {}

    for i, spm_file in enumerate(spm_files):
        name = '.'.join(os.path.basename(spm_file).split('.')[:-1])
        if not args.save_all:
            dirname = os.path.join(os.path.dirname(spm_file), 'processed')
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        try:
            analyser = afmAnalyser(spm_file, args.contour_length * 0.34e-9)
            print('Analysing', os.path.basename(spm_file))
        except GError:
            print('ERROR:', os.path.basename(spm_file), 'contains no (importable) data... skipping')
            continue

        analyser.choose_channels()  # right now just using the single channel
        analyser.preprocess_image()
        image_details = analyser.get_image_details()

        mask, grains = analyser.find_grains(args.threshold, args.min_area)
        median_pixel_area = analyser.find_median_pixel_area()
        mask, grains = analyser.remove_objects(args.max_deviation, removal_type='max')
        mask, grains = analyser.remove_objects(args.min_deviation, removal_type='min')
        print('There were', max(grains), 'grains found')

        grain_data = analyser.analyse_grains()
        # skeleton, mask = analyser.thin_grains()  # skeletonizes
        skeleton = None
        cropped_ids, cropped_datafields = analyser.generate_cropped_datafields(args.crop_width)

        try:
            data_export = analyser.export_data()
            if args.save_all:
                data_exports[name] = data_export
            else:
                fname = os.path.join(dirname, name + '.json')
                pd.DataFrame(json_normalize(data_export)).to_json(fname)
        except AttributeError:
            print("ERROR: ", spm_file, "failed")

        analyser.close_file()

    if args.save_all:
        # write to a jsonlines file
        pd.DataFrame(json_normalize(data_exports)).to_json('gwy_analyser_data.jsonl', orient ='records', lines=True)
