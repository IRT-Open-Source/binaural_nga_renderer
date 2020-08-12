import numpy as np
from ear.core import bs2051, allocentric, point_source, convolver
from . import binaural_point_source


def load_hdf5(file_url):
    """Load a HDF5 file from a URL of the form:

    `file:PATH`: load from file at PATH
    `resource:PATH`: load from package resource PATH
    """
    import h5py
    import pkg_resources

    scheme, path = file_url.split(':', 1)

    if scheme == "resource":
        real_path = pkg_resources.resource_filename(__name__, path)
    elif scheme == "file":
        real_path = path
    else:
        assert False, "unknown resource scheme {scheme}".format(scheme=scheme)

    return h5py.File(real_path, 'r')


class SOFAFileHRIR(object):
    """Simple SOFA interface allowing IRs to be extracted from a
    SimpleFreeFieldHRIR convention file.
    """
    def __init__(self, f):
        self.f = f

        self.check()

    def check(self):
        assert self.f.attrs[
            "SOFAConventions"] == b"SimpleFreeFieldHRIR" or b"MultiSpeakerBRIR"

        sp = self.f["SourcePosition"]
        assert sp.attrs["Type"] == b"spherical" or b"cartesian"
        assert sp.attrs[
            "Units"] == b"degree, degree, meter" or b"degree, degree, metre"

        ep = self.f["EmitterPosition"]
        assert ep.attrs["Type"] == b"cartesian"
        assert ep.attrs["Units"] == b"meter" or b"metre"

        assert self.f["Data.Delay"].shape in [(1, self.R), (self.M, self.R)]

    M = property(lambda self: self.f["Data.IR"].shape[0])
    R = property(lambda self: self.f["Data.IR"].shape[1])
    N = property(lambda self: self.f["Data.IR"].shape[2])

    def select_receivers(self):
        assert self.f["ReceiverPosition"].shape == (2, 3, 1)

        y = self.f["ReceiverPosition"][:, 1, 0]

        return [0, 1] if y[0] < y[1] else [1, 0]

    def source_positions(self):
        from ear.core.geom import cart
        sp = np.array(self.f["SourcePosition"])
        return cart(*sp.T)

    def select_sources(self, positions, exact):
        source_positions = self.source_positions()

        distances = np.linalg.norm(positions[:, np.newaxis] -
                                   source_positions[np.newaxis],
                                   axis=2)
        source_idxes = np.argmin(distances, 1)

        if exact:
            assert np.max(
                np.linalg.norm(source_positions[source_idxes] - positions,
                               axis=1)) < 1e-5

        return source_idxes

    def irs_for_positions(self, positions, exact=False):
        #assert self.f["Data.SamplingRate"][0] == fs

        sources = self.select_sources(positions, exact)
        recievers = self.select_receivers()

        irs = np.array(self.f["Data.IR"])[np.ix_(sources, recievers)]

        return irs

    def check_fs(self):
        return int(self.f["Data.SamplingRate"][0])

def calc_gain_of_irs(irs):
    list_of_gains = []
    for ir in irs:
        pow1L = np.sum(np.abs(ir[0])) / len(ir[0])
        pow1R = np.sum(np.abs(ir[1])) / len(ir[0])
        pow2L = 0.5 / len(ir[0])
        pow2R = 0.5 / len(ir[0])
        pow2Lnorm = pow2L / pow1L / 2
        pow2Rnorm = pow2R / pow1R / 2
        
        pow2LR_sum = pow2Lnorm+pow2Rnorm
        list_of_gains.append(pow2LR_sum)
    
    avg_gain = np.average(list_of_gains)
    return avg_gain
    
def calc_delay_of_irs(irs):
    list_min_delay = []
    for ir in irs:
        max_amp_l = np.argmax(ir[0, :])
        max_amp_r = np.argmax(ir[1, :])
        if max_amp_l <= max_amp_r:
            list_min_delay.append(max_amp_l)
        else:
            list_min_delay.append(max_amp_r)
        
    totalavg_mindelay = np.average(list_min_delay)
    
    return totalavg_mindelay
    
def get_binaural_layout(spec):
    bs2051.layout_names, bs2051.layouts = binaural_point_source._load_binaural_layouts()
    allocentric._allo_positions = binaural_point_source._load_allo_positions_binaural()
    
    return bs2051.get_layout(spec[1]).without_lfe
