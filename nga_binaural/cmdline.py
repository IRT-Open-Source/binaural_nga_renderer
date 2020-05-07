import argparse
from ear.cmdline.render_file import OfflineRenderDriver, handle_strict, PeakMonitor
from pydub import AudioSegment
from pydub.effects import normalize
from ear.fileio import openBw64, openBw64Adm
from ear.fileio.bw64.chunks import FormatInfoChunk
from .binaural_layout import BinauralOutput
from .renderer import BinauralRenderer
from itertools import chain
import sys

"""this is a modified version of render_file.py from the EAR. It was modified to adapt to the binaural rendering structure."""

def _run(driver, input_file, output_file):
    """Render input_file to output_file."""
    spkr_layout, upmix, n_channels = driver.load_output_layout()

    output_monitor = PeakMonitor(n_channels)

    with openBw64Adm(input_file, driver.enable_block_duration_fix) as infile:
        formatInfo = FormatInfoChunk(formatTag=1,
                                     channelCount=n_channels,
                                     sampleRate=infile.sampleRate,
                                     bitsPerSample=infile.bitdepth)
        with openBw64(output_file, "w", formatInfo=formatInfo) as outfile:
            for output_block in driver.render_input_file(driver, infile, spkr_layout, upmix):
                output_monitor.process(output_block)
                outfile.write(output_block)

    output_monitor.warn_overloaded()
    if driver.fail_on_overload and output_monitor.has_overloaded():
        sys.exit("error: output overloaded")

    normalized_output = normalize(AudioSegment.from_file(output_file), headroom=0.3)
    normalized_output.export(output_file, format="wav")

def _load_binaural_output_layout():
    spkr_layout = BinauralOutput()
    upmix = None
    n_channels = 2

    return spkr_layout, upmix, n_channels


def _render_input_file_binaural(driver, infile, spkr_layout, upmix=None):
    """Get sample blocks of the input file after rendering.

        Parameters:
            infile (Bw64AdmReader): file to read from
            spkr_layout (Layout): layout to render to
            upmix (sparse array or None): optional upmix to apply

        Yields:
            2D sample blocks
        """
    renderer = BinauralRenderer(spkr_layout,
                                sr=infile.sampleRate,
                                **driver.config)
    renderer.set_rendering_items(driver.get_rendering_items(infile.adm))

    for input_samples in chain(infile.iter_sample_blocks(driver.blocksize),
                               [None]):
        if input_samples is None:
            output_samples = renderer.get_tail(infile.sampleRate,
                                               infile.channels)
        else:
            output_samples = renderer.render(infile.sampleRate, input_samples)

        output_samples *= driver.output_gain_linear

        if upmix is not None:
            output_samples *= upmix

        yield output_samples


def add_commands_for_offline_driver(parser):
    """
    This is essentially a modified version of OfflineRendererDriver.add_args()
    for the binaural use case.
    """
    parser.add_argument("--output-gain-db",
                        type=float,
                        metavar="gain_db",
                        default=0,
                        help="output gain in dB (default: 0)")
    parser.add_argument(
        "--fail-on-overload",
        "-c",
        action="store_true",
        help="fail if an overload condition is detected in the output")
    parser.add_argument(
        "--enable-block-duration-fix",
        action="store_true",
        help="automatically try to fix faulty block format durations")

    parser.add_argument("--programme",
                        metavar="id",
                        help="select an audioProgramme to render by ID")
    parser.add_argument(
        "--comp-object",
        metavar="id",
        action="append",
        default=[],
        help="select an audioObject by ID from a complementary group")

    parser.add_argument(
        '--apply-conversion',
        choices=("to_cartesian", "to_polar"),
        help='Apply conversion to Objects audioBlockFormats before rendering')


def parse_command_line():
    parser = argparse.ArgumentParser(description="Binaural ADM renderer")

    parser.add_argument("-d",
                        "--debug",
                        help="print debug information when an error occurs",
                        action="store_true")

    add_commands_for_offline_driver(parser)

    parser.add_argument("input_file")
    parser.add_argument("output_file")

    parser.add_argument("--strict",
                        help="treat unknown ADM attributes as errors",
                        action="store_true")

    args = parser.parse_args()
    return args


def render_file():
    args = parse_command_line()

    handle_strict(args)

    try:
        driver = OfflineRenderDriver(
            target_layout='binaural',
            speakers_file=None,
            output_gain_db=args.output_gain_db,
            fail_on_overload=args.fail_on_overload,
            enable_block_duration_fix=args.enable_block_duration_fix,
            programme_id=args.programme,
            complementary_object_ids=args.comp_object,
            conversion_mode=args.apply_conversion,
        )

        driver.load_output_layout = _load_binaural_output_layout
        driver.render_input_file = _render_input_file_binaural
        driver.run = _run

        driver.run(driver, args.input_file, args.output_file)
    except Exception as error:
        if args.debug:
            raise
        else:
            sys.exit(str(error))

