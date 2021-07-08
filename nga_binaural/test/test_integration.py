import subprocess
import os.path
import numpy.testing as npt
from ear.fileio import openBw64

files_dir = os.path.join(os.path.dirname(__file__), "data")

bwf_file = os.path.join(files_dir, "test-input.wav")
expected_file = os.path.join(files_dir, "test-expected-normalized.wav")


def read_audio_file(filename):
    with openBw64(filename, mode='r') as handle:
        samplerate = handle.sampleRate
        samples = handle.read(len(handle))
        return samples, samplerate


def test_rendering_file(tmpdir):
    rendered_file = os.path.join(tmpdir, "test_binaural_render.wav")
    args = ['nga-binaural', '-d', '-pn', bwf_file, rendered_file]
    assert subprocess.call(args) == 0

    samples, sr = read_audio_file(rendered_file)
    expected_samples, expected_sr = read_audio_file(expected_file)
    assert sr == expected_sr
    npt.assert_allclose(samples, expected_samples, atol=1e-4)
