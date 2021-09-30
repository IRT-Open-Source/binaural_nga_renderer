import copy
from ear.options import Option, OptionsHandler
from ear.core.metadata_input import ObjectRenderingItem
from ear.core import point_source
from ear.fileio.adm.elements import ObjectPolarPosition
import numpy as np
from scipy import signal
from . import sofa, binaural_point_source
from .matrix_convolver import MatrixBlockConvolver
from .convolver import VariableBlockSizeAdapter
from .align_irs import align_irs
from .binaural_layout import BinauralOutput

binaural_output_options = OptionsHandler(
    block_size=Option(
        default=512,
        description="block size for convolution",
    ),
    virtual_layout_hrir=Option(
        default=("binaural", "all_defined"),
        description="loudspeaker layout to render to before applying HRIRs",
    ),
    virtual_layout_brir=Option(
        default=("binaural", "BRIR"),
        description="loudspeaker layout to render to before applying BRIRs",
    ),
    hrir_file=Option(
        default="resource:data/HRIR_FULL2DEG.sofa",
        description="SOFA file to get HRIRs from",
    ),
    brir_file=Option(
        default=
        "resource:data/BRIR_KU100_60ms.sofa",
        description="SOFA file to get BRIRs from",
    ),
)

class BinauralWrapper(object):
    """Wrapper around multiple loudspeaker renderers which returns the binaural rendering."""
    @binaural_output_options.with_defaults
    def __init__(self,
                 renderer_cls,
                 layout,
                 virtual_layout,
                 sr,
                 block_size,
                 virtual_layout_hrir,
                 virtual_layout_brir,
                 hrir_file,
                 brir_file,
                 renderer_opts={}):

        point_source.configure = binaural_point_source.configure

        """load layouts for all three renderings"""
        
        if virtual_layout is None:
            hrir_layout = sofa.get_binaural_layout(virtual_layout_hrir)
        else:
            hrir_layout = sofa.get_binaural_layout(('bs2051', virtual_layout))
        if len(hrir_layout.channels) < 22:
            brir_layout = hrir_layout
        else:
            brir_layout = sofa.get_binaural_layout(virtual_layout_brir)
        dirir_layout = sofa.get_binaural_layout(("binaural", "binaural_direct"))

        """define three renderers"""
        self.renderer_hrir = renderer_cls(hrir_layout, **renderer_opts)
        self.renderer_brir = renderer_cls(brir_layout, **renderer_opts)
        self.renderer_direct = renderer_cls(dirir_layout, **renderer_opts)

        """load impulse responses according to the prior defined layouts and apply gain and delay for correct summation"""
        hrir_sofa_file = sofa.SOFAFileHRIR(sofa.load_hdf5(hrir_file))
        hrirs = hrir_sofa_file.irs_for_positions(hrir_layout.positions)
        hrirs = align_irs(hrirs)
        if hrir_sofa_file.check_fs() != sr:
            hrirs = signal.resample(
                hrirs, int(len(hrirs) / hrir_sofa_file.check_fs() * sr))
        hrirs = hrirs / sofa.calc_gain_of_irs(hrirs) * 0.20885643426029013 / 2

        brir_sofa_file = sofa.SOFAFileHRIR(sofa.load_hdf5(brir_file))
        brirs = brir_sofa_file.irs_for_positions(brir_layout.positions)
        if brir_sofa_file.check_fs() != sr:
            brirs = signal.resample(
                brirs, int(len(brirs) / brir_sofa_file.check_fs() * sr))
        brirs = brirs / sofa.calc_gain_of_irs(
            brirs) * 0.05542830927315457 / 2 
        brirs = np.concatenate(
            (np.zeros([len(brirs), 2,
                       int(sofa.calc_delay_of_irs(hrirs)) - 1]), brirs), axis=2)

        dirirs = np.concatenate((np.zeros(
            [2, 2, int(sofa.calc_delay_of_irs(hrirs)) - 1]), np.ones([2, 2, 1])), axis=2)
        dirirs = dirirs * 0.37

        """prepare filter matrix for MatrixBlockConvolver"""
        filter_matrix_hrir = [(in_ch, out_ch, ir)
                              for in_ch, ir_pair in enumerate(hrirs)
                              for out_ch, ir in enumerate(ir_pair)]

        filter_matrix_brir = [(in_ch, out_ch, ir)
                              for in_ch, ir_pair in enumerate(brirs)
                              for out_ch, ir in enumerate(ir_pair)]

        filter_matrix_dirir = [(in_ch, out_ch, ir)
                               for in_ch, ir_pair in enumerate(dirirs)
                               for out_ch, ir in enumerate(ir_pair)]

        """define convolver for all three parts"""
        convolver_hrir = MatrixBlockConvolver(block_size,
                                              len(hrir_layout.channels), 2,
                                              filter_matrix_hrir)

        convolver_brir = MatrixBlockConvolver(block_size,
                                              len(brir_layout.channels), 2,
                                              filter_matrix_brir)

        convolver_dirir = MatrixBlockConvolver(block_size,
                                               len(dirir_layout.channels), 2,
                                               filter_matrix_dirir)

        """convolution with variable block size"""
        self.convolver_vbs_hrir = VariableBlockSizeAdapter(
            block_size, (len(hrir_layout.channels), 2),
            convolver_hrir.filter_block)

        self.convolver_vbs_brir = VariableBlockSizeAdapter(
            block_size, (len(brir_layout.channels), 2),
            convolver_brir.filter_block)

        self.convolver_vbs_dirir = VariableBlockSizeAdapter(
            block_size, (len(dirir_layout.channels), 2),
            convolver_dirir.filter_block)


    """filter items to be rendered for different renderers (binaural, non-binaural)"""
    def filter_rendering_items_hrir(self, rendering_items):
        rendering_items_hrir = copy.deepcopy(rendering_items)

        for objects in enumerate(rendering_items_hrir):
            if isinstance(objects[1], ObjectRenderingItem):

                for audioBlock in objects[1].adm_path.audioChannelFormat.audioBlockFormats[:]:
                    if isinstance(audioBlock.position, ObjectPolarPosition):
                        if audioBlock.position.distance <= 0.3:
                            audioBlock.gain *= (audioBlock.position.distance / 0.3)
                        audioBlock.position.distance = 1

        return rendering_items_hrir

    def filter_rendering_items_brir(self, rendering_items):
        rendering_items_brir = copy.deepcopy(rendering_items)

        for objects in enumerate(rendering_items_brir):
            if isinstance(objects[1], ObjectRenderingItem):

                for audioBlock in objects[1].adm_path.audioChannelFormat.audioBlockFormats[:]:
                    if isinstance(audioBlock.position, ObjectPolarPosition):
                        if audioBlock.position.distance <= 1 and audioBlock.position.distance > 0.2:
                            audioBlock.gain *= (audioBlock.position.distance - 0.2) / 0.8
                        if audioBlock.position.distance <= 0.2:
                            audioBlock.gain = 0
                        audioBlock.position.distance = 1

        return rendering_items_brir

    def filter_rendering_items_direct(self, rendering_items):
        rendering_items_direct = copy.deepcopy(rendering_items)

        for objects in enumerate(rendering_items_direct):
            if isinstance(objects[1], ObjectRenderingItem):

                for audioBlock in objects[1].adm_path.audioChannelFormat.audioBlockFormats[:]:
                    if isinstance(audioBlock.position, ObjectPolarPosition):
                        if audioBlock.position.distance > 0.3:
                            audioBlock.gain = 0
                        if audioBlock.position.distance <= 0.3:
                            audioBlock.gain *= 1 - (audioBlock.position.distance / 0.3)
                        audioBlock.position.distance = 1
                    else:
                        audioBlock.gain = 0

            else:
                rendering_items_direct = []

        return rendering_items_direct

    """sets rendering items and applies filtering"""
    def set_rendering_items(self, rendering_items):

        self.renderer_brir.set_rendering_items(self.filter_rendering_items_brir(rendering_items))
        self.renderer_hrir.set_rendering_items(self.filter_rendering_items_hrir(rendering_items))
        self.renderer_direct.set_rendering_items(self.filter_rendering_items_direct(rendering_items))

    @property
    def overall_delay(self):
        """check delays for all renderers"""

        return self.convolver_vbs_hrir.delay(self.renderer_hrir.overall_delay)

    """take output of all rednerers and convolve accordingly, return complete summed rendering"""
    def render(self, sample_rate, start_sample, samples):

        loudspeaker_signals_brir = self.renderer_brir.render(
            sample_rate, start_sample, samples)
        brir_rendering = self.convolver_vbs_brir.process(
            loudspeaker_signals_brir)

        loudspeaker_signals_hrir = self.renderer_hrir.render(
            sample_rate, start_sample, samples)
        hrir_rendering = self.convolver_vbs_hrir.process(
            loudspeaker_signals_hrir)

        loudspeaker_signals_direct = self.renderer_direct.render(
            sample_rate, start_sample, samples)
        direct_rendering = self.convolver_vbs_dirir.process(
            loudspeaker_signals_direct)

        rendering = (hrir_rendering + brir_rendering + direct_rendering) / 2

        return rendering
