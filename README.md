# TopoStats for AFM

## Gwyddion Analyser

A collection of scripts to automate preprocessing of AFM images with gwyddion.

### Installation

 - Requires Python 2 (with glib)
 - [Gwyddion](http://gwyddion.net/) must be installed and ideally have the pygwy module added to the path.

### Usage
An example script is is `run_process.py`.

The following command will run the preprocessing with the default values show. Only `path` is required.
```
python2 gwy_analyser/gwy_process.py path --filetypes 'spm' 
--threshold 0.5 --min-area 400e-9 
--min-deviation 0.8 --max-deviation 1.5 
--crop-width 100e-9 --contour-length 302
```

More details on each of these options can be found with the command
```
python2 gwy_analyser/gwy_process.py --help
```

The cleanup methods used by gwyddion are set in `gwy_analyser/gwy_settings.py`.

Statistics are then calculated as set in  `gwy_analyser/gwy_settings.py`.

The image and statistics are then outputted as `json` files in the same path as the file (with the same filename). Optionally if `--save-all` is selected then a single json file will be outputted in the path entered.
