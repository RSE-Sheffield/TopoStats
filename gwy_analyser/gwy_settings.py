#!/usr/bin/env python2
try:
    import gwy
except ImportError:
    import sys
    sys.path += ["/usr/share/gwyddion/pygwy", "/usr/local/share/gwyddion/pygwy"]
    import gwy

CLEANUP_METHODS = [
    "align_rows",
    "level",  # flatten the data
    'flatten_base',
    'zero_mean',
    'scars_remove',
]

VALUES_TO_COMPUTE = {
    'projected area': gwy.GRAIN_VALUE_PROJECTED_AREA,
    'laplace volume': gwy.GRAIN_VALUE_VOLUME_LAPLACE,
    'zero volume': gwy.GRAIN_VALUE_VOLUME_0,
    'min volume': gwy.GRAIN_VALUE_VOLUME_MIN,
    'max height': gwy.GRAIN_VALUE_MAXIMUM,
    'median height': gwy.GRAIN_VALUE_MEDIAN,
    'mean height': gwy.GRAIN_VALUE_MEAN,
    'center x': gwy.GRAIN_VALUE_CENTER_X,
    'center y': gwy.GRAIN_VALUE_CENTER_Y,
    'curvature centre x': gwy.GRAIN_VALUE_CURVATURE_CENTER_X,
    'curvature centre y': gwy.GRAIN_VALUE_CURVATURE_CENTER_Y,
    'curvature centre z': gwy.GRAIN_VALUE_CURVATURE_CENTER_Z,
    'pixel area': gwy.GRAIN_VALUE_PIXEL_AREA,
    'half heightarea': gwy.GRAIN_VALUE_HALF_HEIGHT_AREA,
}
