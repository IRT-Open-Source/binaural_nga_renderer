# Binaural NGA Renderer (NGA-Binaural)


The **Binaural NGA Renderer** **(*NGA-Binaural*)** is an addon that provides binaural rendering of ADM files by using the **EBU ADM Renderer** **(*EAR*)** to create virtual loudspeaker signals. The EAR will be installed together with this addon, if it is not already present.
This **Binaural NGA Renderer** provides an implementation of the rendering structure, as well as the optimization approaches that are described in the the  AES paper "Optimized binaural rendering of Next Generation Audio using virtual loudspeaker setups".


Further descriptions of the *EAR* algorithms and functionalities can be found in [EBU Tech 3388](https://tech.ebu.ch/publications/adm-renderer-for-use-in-nga-broadcasting).

## Test files
A initial set of ADM files to test the *NGA-Binaural* can be found under
  - https://ebu.io/qc/testmaterial and
  - http://cvssp.org/data/s3a/public/radiodrama_register.php

## Installation

To install the latest release from github:

```
$ git clone the repository
$ pip install path/to/repository
```

### Python versions

*NGA-Binaural* supports Python 2.7 and Python >=3.6
and runs on all major platforms (Linux, Mac OSX, Windows).


## Getting started

The *NGA-Binaural* comes with the following command line tool:

- `nga-binaural`

### Command line renderer

```bash
usage: nga-binaural [-h] [-d]
                    [-s target_system]
                    [--output-gain-db gain_db] [--fail-on-overload]
                    [--enable-block-duration-fix] [--programme id]
                    [--comp-object id]
                    [--apply-conversion {to_cartesian,to_polar}] [--strict]
                    input_file output_file

Binaural NGA Renderer

positional arguments:
  input_file
  output_file

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           print debug information when an error occurs
  --output-gain-db gain_db
                        output gain in dB (default: 0)
  --fail-on-overload, -c
                        fail if an overload condition is detected in the
                        output
  --enable-block-duration-fix
                        automatically try to fix faulty block format durations
  --programme id        select an audioProgramme to render by ID
  --comp-object id      select an audioObject by ID from a complementary group
  --apply-conversion {to_cartesian,to_polar}
                        Apply conversion to Objects audioBlockFormats before
                        rendering
  --strict              treat unknown ADM attributes as errors
```

To render an ADM file, the following two parameters must be given:
  - the name of the input file
  - the name of the output file

For example `nga-binaural input.wav output_binaural.wav` will render the BW64/ADM file `input.wav` and store the result in `output_binaural.wav`.

`-s` followed by a target, BS2051-output format can be used to render to a specific virtual loudspeaker setup. Otherwise, a virtual 49 speaker setup will be used that is optimized for rendering quality, but requires a lot of computational cost.

`--fail-on-overload` makes the rendering process fail in case an overload in the output channels occurs to ensure any signal clipping doesn't go unnoticed. Use `--output-gain-db` to adjust the output gain.

`--enable-block-duration-fix` automatically fixes durations of `audioBlockFormats` in case they are not continuous.
**Please note** that the proper way to handle this situation is to fix the input file.

`--strict` enables strict ADM parsing mode. Some of the currently available
ADM/BW64 files may not strictly adhere to the BS.2076 specification, for example by including xml attributes that are not part of the standard.
The default behaviour is to output a warning and continue processing.
When strict mode is enabled, warnings are turned into errors and processing is  stopped.


**Please note** that, depending on the size of the file, it may
take some time to render the file. At the time of writing, the parsing of the ADM XML data is relatively slow when the ADM is large (>= a few megabytes).

