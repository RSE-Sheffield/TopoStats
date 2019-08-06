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

from gwy_analyser import afmAnalyser

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

    args = parser.parse_args()
    if not args.path.split('.')[-1] in args.filetypes.strip('.').split(','):
        spm_files = []
        for dirpath, subdirs, filenames in os.walk(args.path):
            for filename in filenames:
                if os.path.splitext(filename)[1][1:] in args.filetypes.split(',') and filename[0] != '.':
                    spm_files.append(os.path.join(dirpath, filename))
        print(len(spm_files), "files found")
    else:
        spm_files = [args.path]
        args.path = os.path.dirname(args.path)

    data_exports = {}

    for i, spm_file in enumerate(spm_files):
        print('Analysing', os.path.basename(spm_file))
        analyser = afmAnalyser(spm_file, args.contour_length*.34e-9)
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

        data_export = analyser.export_data()
        name =  '.'.join(os.path.basename(spm_file).split('.')[:-1])

        data_exports[name] = data_export

    with open(os.path.join(args.path, 'all_data.pkl'), 'w') as f:
        pickle.dump(data_exports, f, protocol=0)
