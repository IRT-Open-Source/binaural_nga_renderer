import numpy as np
from attr import attrs, attrib
from ear.options import OptionsHandler
from ear.core import bs2051, point_source
import pkg_resources
from ruamel.yaml import YAML
from . import sofa

"""this is a modified version of point_source.py from the EAR. It was modified to adapt to the binaural rendering structure."""

def _load_binaural_layouts():
    fname = "data/binaural_layouts.yaml"
    with pkg_resources.resource_stream(__name__, fname) as layouts_file:
        yaml = YAML(typ='safe', pure=True)
        layouts_data = yaml.load(layouts_file)

        layouts = list(map(bs2051._dict_to_layout, layouts_data))

        for layout in layouts:
            errors = []
            layout.check_positions(callback=errors.append)
            assert errors == []

        layout_names = [layout.name for layout in layouts]
        layouts_dict = {layout.name: layout for layout in layouts}

        return layout_names, layouts_dict

def _load_allo_positions_binaural():
    import pkg_resources
    from ruamel import yaml

    fname = "data/binaural_layouts_allo.yaml"
    with pkg_resources.resource_stream(__name__, fname) as layouts_file:
        yaml = YAML(typ='safe', pure=True)
        return yaml.load(layouts_file)

@attrs(slots=True)
class StereoPanDownmix_Binaural(point_source.RegionHandler): 
    """Stereo panning region handler.

    This implements a panning function similar to 0+5+0 with a BS.775 downmix,
    with corrected position and energy.

    Attributes:
        left_channel (int): Index of the left output channel.
        right_channel (int): Index of the right output channel.
    """
    left_channel = attrib(converter=int)
    right_channel = attrib(converter=int)

    psp = attrib(default=None)

    @property
    def output_channels(self):
        return np.array((self.left_channel, self.right_channel))

    def __attrs_post_init__(self):
        layout = sofa.get_binaural_layout(["binaural", "Quad_Downmix"])
        assert layout.channel_names == ["M+090", "M-090", "M+000", "M+180"]

        self.psp = configure(layout)

    def handle(self, position):
        # downmix as in ITU-R BS.775, but with the centre downmix adjusted to
        # preserve the velocity vector rather than the output power
        downmix = [
            [1.0000, 0.0000, np.sqrt(3) / 3, np.sqrt(3) / 3],
            [0.0000, 1.0000, np.sqrt(3) / 3, np.sqrt(3) / 3],
        ]

        # pan with 0+4+0, downmix and power normalise
        pv = self.psp.handle(position)
        pv_dmix = np.dot(downmix, pv)
        pv_dmix /= np.linalg.norm(pv_dmix)

        return pv_dmix

def _configure_stereo_binaural(layout):
    """Configure a point source panner assuming an 0+2+0 layout."""
    left_channel = layout.channel_names.index("M+090")
    right_channel = layout.channel_names.index("M-090")

    panner = StereoPanDownmix_Binaural(left_channel=left_channel, right_channel=right_channel)

    return point_source.PointSourcePanner([panner])


configure_options = OptionsHandler()


def configure(layout):
    """Configure a point source panner given a loudspeaker layout.

    Args:
        layout (.layout.Layout): Loudspeaker layout.

    Returns:
        PointSourcePanner: point source panner configured to output channels in
            the same order as layout.channels.
    """
    if layout.name == "0+2+0":
        return point_source._configure_stereo(layout)
    elif layout.name == "binaural_direct":
        return _configure_stereo_binaural(layout)
    else:
        return point_source._configure_full(layout)
