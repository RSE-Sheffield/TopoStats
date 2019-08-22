#!/usr/bin/env python2
"""
Use gwyddion to preprocess AFM images.

FUNCTIONS STILL TO ADD
- heightediting
- double check remove(large/small)objects
- grainthinning
- boundbox
- splitimage
- savecroppedfiles

"""
from __future__ import print_function

from copy import deepcopy

import numpy as np

from gwy_settings import CLEANUP_METHODS, VALUES_TO_COMPUTE

try:
    import gwy
    import gwyutils
except ImportError:
    import sys
    sys.path += ["/usr/share/gwyddion/pygwy", "/usr/local/share/gwyddion/pygwy"]
    import gwy
    import gwyutils


class afmAnalyser:
    def __init__(self, filename, contour_length):
        self.filename = filename
        self.data =  gwy.gwy_file_load(self.filename, gwy.RUN_NONINTERACTIVE)
        gwy.gwy_app_data_browser_add(self.data)

        self.contour_length = contour_length

        self.settings = gwy.gwy_app_settings_get()  # from ~/.gwyddion/settings
        self.settings["/module/pixmap/ztype"] = 0  # Turn colour bar off 
        # Define the settings for image processing functions e.g. align rows here
        self.settings['/module/linematch/method'] = 1  # uses median
        self.settings["/module/linematch/max_degree"] = 0

    def choose_channels(self, channel='ZSensor'):
        # ids = gwy.gwy_app_data_browser_get_data_ids(self.data)
        self.chosen_ids = gwy.gwy_app_data_browser_find_data_by_title(self.data, channel)
        self.chosen_ids = self.chosen_ids if self.chosen_ids else gwy.gwy_app_data_browser_find_data_by_title(self.data, 'Height')
        return self.chosen_ids

    def preprocess_image(self, cleanup_methods=CLEANUP_METHODS, chosen_id=None, gaussian=False):
        if not chosen_id:
            self.chosen_id = self.chosen_ids[0]
        gwy.gwy_app_data_browser_select_data_field(self.data, self.chosen_id)
        for cleanup_method in cleanup_methods:
            gwy.gwy_process_func_run(cleanup_method, self.data, gwy.RUN_IMMEDIATE)
        self.datafield = gwy.gwy_app_data_browser_get_current(gwy.APP_DATA_FIELD)
        if gaussian:
            self.datafield.filter_gaussian(1.5)

    def get_image_details(self):
        self.image_details = {
            'x_px': self.datafield.get_xres(),
            'y_px': self.datafield.get_yres(),
            'x_real': self.datafield.get_xreal(),
            'y_real': self.datafield.get_yreal(),
        }
        try:
            self.image_details.update({
                'x_res': self.datafield.get_xreal() / self.datafield.get_xres(),
                'y_res': self.datafield.get_yreal() / self.datafield.get_yres(),
            })
        except:
            self.image_details.update({
                'x_res': self.datafield.get_dx(),
                'y_res': self.datafield.get_dy()
            })
            
        return self.image_details

    def find_grains(self, threshold, min_area):
        self.mask = gwy.DataField.new_alike(self.datafield, False)

        # Mask data that are above thresh*RMSD(heights) from average height.
        # This criterium corresponds to the usual Gaussian distribution outliers detection if thresh is 3.
        self.datafield.mask_outliers(self.mask, threshold)

        # excluding mask, zero mean
        stats = self.datafield.area_get_stats_mask(
            self.mask, gwy.MASK_EXCLUDE, 0, 0, self.datafield.get_xres(), self.datafield.get_yres())
        self.datafield.add(-stats[0])

        self.mask.grains_remove_touching_border()  # Remove grains touching the edge of the mask

        min_feature_size = int(min_area / self.image_details['x_res'])  # nm -> px
        self.mask.grains_remove_by_size(min_feature_size)

        self.grains = self.mask.number_grains()  # Numbering grains for grain analysis
        return self.mask, self.grains

    def find_median_pixel_area(self, grains=None):
        # print values_to_compute.keys()
        grains = grains if grains else self.grains
        grain_pixel_area = np.array(self.datafield.grains_get_values(grains, gwy.GRAIN_VALUE_PIXEL_AREA))
        self.median_pixel_area = np.median(grain_pixel_area)
        return self.median_pixel_area

    def remove_objects(self, deviation, median_pixel_area=None, removal_type=None):
        if removal_type not in ['min', 'max']:
            raise ValueError('removal type must be set to min or max')

        mask2 = gwy.DataField.new_alike(self.datafield, False)
        # Mask data that are above thresh*RMSD from average height. If thresh=3 same as gaussian outliers
        self.datafield.mask_outliers(mask2, 1)

        # Intersect with inverse of small grains with original mask to remove large objects e.g. aggregates
        median_pixel_area = median_pixel_area if median_pixel_area else self.median_pixel_area
        size_to_remove = int(deviation * median_pixel_area)
        mask2.grains_remove_by_size(size_to_remove)
        if type == 'max':
            mask2.grains_invert()
        
        self.mask.grains_intersect(mask2)
        self.grains = self.mask.number_grains()
        return self.mask, self.grains
    
    def analyse_grains(self, values_to_compute=VALUES_TO_COMPUTE, grains=None, datafield=None, as_list=False):
        grains = grains if grains else self.grains
        datafield = datafield if datafield else self.datafield
        # Do not add the 0th value in all arrays - this corresponds to the background
        self.grain_data = {stat: datafield.grains_get_values(grains, gwy_key)[1:] \
                        for stat, gwy_key in values_to_compute.iteritems()}

        if as_list:
            num_grains = len(set(grains)) - 1 # first grain is ignored
            self.grain_data = [{stat: self.grain_data[stat][i] for stat in values_to_compute.keys()} for i in range(num_grains)] 
        return self.grain_data
    
    def generate_cropped_datafields(self, crop_width, grains=None, return_image=False):
        grains = grains if grains else self.grains
        
        original_ids = gwy.gwy_app_data_browser_get_data_ids(self.data)

        bboxes = self.datafield.get_grain_bounding_boxes(grains)
        center_xs = self.datafield.grains_get_values(grains, gwy.GRAIN_VALUE_CENTER_X)
        center_ys = self.datafield.grains_get_values(grains, gwy.GRAIN_VALUE_CENTER_Y)

        crop_width = int(crop_width / self.image_details['x_res'])

        self.cropped_datafields = []
        self.cropped_masks = []
        self.cropped_skeletons = []
        self.cropped_ids = []

        for i, (center_x, center_y) in enumerate(zip(center_xs, center_ys)):
            if i == 0:
                continue  # skip first grain (background)
            px_center_x = int(center_x / self.image_details['x_res'])
            px_center_y = int(center_y / self.image_details['y_res'])
            ULcol = px_center_x - crop_width if (px_center_x - crop_width) > 0  else 0
            ULrow = px_center_y - crop_width if (px_center_y - crop_width) > 0 else 0
            BRcol = px_center_x + crop_width if (px_center_x + crop_width) < self.image_details['x_px'] else self.image_details['x_px']
            BRrow = px_center_y + crop_width if (px_center_y + crop_width) < self.image_details['y_px'] else self.image_details['y_px']
            
            # add cropped datafield to active container
            cropped_datafield = self.datafield.duplicate()
            cropped_datafield.resize(ULcol, ULrow, BRcol, BRrow)
            cropped_id = i + len(original_ids)

            cropped_mask = self.mask.duplicate()
            cropped_mask.resize(ULcol, ULrow, BRcol, BRrow)

            gwy.gwy_app_data_browser_add_data_field(cropped_datafield, self.data, cropped_id)
            self.cropped_datafields.append(cropped_datafield)
            self.cropped_masks.append(cropped_mask)
            self.cropped_ids.append(cropped_id)

        # # Generate list of datafields including cropped fields
        # self.cropped_ids = gwy.gwy_app_data_browser_get_data_ids(self.data)
        
        return self.cropped_ids, self.cropped_datafields
    
    def thin_grains(self, mask=None):
        # Calculate gaussian width in pixels from real value using pixel size
        mask = mask if mask else self.mask
        old_mask = deepcopy(gwyutils.data_field_data_as_array(mask))
        guassian_size = 2e-9 / self.image_details['x_res']
        self.datafield.filter_gaussian(guassian_size)
        
        mask.grains_thin()  # skeletonizes to get traces
        return  mask, old_mask
    
    # def get_image(self, datafield):
    #     get_subimages

    def export_data(self, mask=None, skeleton=None, min_length=40):
        """
        Try getting the grain data here all in one so that we can pair all the values together?
        """
        data_export = {'datafield': gwyutils.data_field_data_as_array(self.datafield)}

        mask = mask if mask else self.mask
        if isinstance(mask, (np.ndarray, np.generic)):
            data_export['mask'] = mask
        elif mask:    
            data_export['mask'] = gwyutils.data_field_data_as_array(mask)
        if skeleton:
            data_export['skeleton'] = gwyutils.data_field_data_as_array(skeleton)

        data_export['image details'] = self.image_details

        data_export['grain data'] = []
        self.analyse_grains(as_list=True)  # saves to object as self.grain_data

        for grain_data, cropped_mask, cropped_datafield in zip(self.grain_data, self.cropped_masks, self.cropped_datafields):
            grain_data['image'] = gwyutils.data_field_data_as_array(cropped_datafield)
            grain_data['mask'] = gwyutils.data_field_data_as_array(cropped_mask)
            grain_data['filename'] = self.filename
            data_export['grain data'].append(grain_data)
            # http://gwyddion.net/documentation/head/pygwy/gwy.DataField-class.html#mark_extrema
        return data_export

    def close_file(self):
        gwy.gwy_app_data_browser_remove(self.data)
