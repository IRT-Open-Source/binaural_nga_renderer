import numpy as np


class FDBuffer(object):
    """A block of possibly-zero frequency-domain samples of a given size.

    Attributes:
        is_zero (bool): Are all samples in this block zero? If False, then buffer is not Null.
        buffer (None or array): Complex samples.
    """
    def __init__(self, block_size):
        self.block_size = block_size
        self.is_zero = True
        self.buffer = None

    def alloc_buffer(self):
        if self.buffer is None:
            self.buffer = np.zeros(self.block_size + 1, dtype=np.complex)

    def clear(self):
        self.is_zero = True
        if self.buffer is not None:
            self.buffer.fill(0)

    def __iadd__(self, other):
        if not other.is_zero:
            self.alloc_buffer()
            self.buffer += other.buffer
            self.is_zero = False
        return self

    @classmethod
    def from_td(cls, block_size, td):
        b = cls(block_size)
        if np.any(td):
            b.is_zero = False
            b.buffer = np.fft.rfft(td, block_size * 2)
        return b

    def to_td(self, td):
        if not self.is_zero:
            td[:] = np.fft.irfft(self.buffer)[:self.block_size]


def FDBuffers_to_td(buffers):
    """Turn a list of frequency-domain buffers into an array of time-domain
    samples of the same shape."""
    td = np.zeros((len(buffers), buffers[0].block_size))

    for buf, td_channel in zip(buffers, td):
        buf.to_td(td_channel)

    return td


def fma(x, a, b):
    """Implement x += a * b for FDBuffer arguments"""
    if (not a.is_zero) and (not b.is_zero):
        x.alloc_buffer()
        x.buffer += a.buffer * b.buffer
        x.is_zero = False


class MatrixBlockConvolver(object):
    """Apply a matrix of time-domain filters.

    This can be more efficient than using OverlapSaveConvolver if some input or
    output channels are reused, as we only need to FFT each input and output
    channel once.

    Parameters:
        block_size (int): time domain block size for input and output blocks
        n_in (int): number of input channels
        n_out (int): number of output channels
        filters (list): Single-channel filters to apply. Each element is a
            3-tuple containing the input channel number, output channel number,
            and a single channel filter.
    """
    class FDConvolverChannel(object):
        """A single channel of concolution in the frequency domain."""
        def __init__(self, block_size, f):
            self.block_size = block_size

            self.filter_blocks_fd = []
            self.blocks_fd = []
            for start in range(0, len(f), self.block_size):
                end = min(len(f), start + self.block_size)

                self.filter_blocks_fd.append(
                    FDBuffer.from_td(self.block_size, f[start:end]))
                self.blocks_fd.append(FDBuffer(self.block_size))

        def filter_block(self, in_block_fd):
            # clear the returned block from the previous frame
            self.blocks_fd[-1].clear()

            for filter_block, block in zip(self.filter_blocks_fd,
                                           self.blocks_fd):
                fma(block, filter_block, in_block_fd)

            self.blocks_fd.append(self.blocks_fd.pop(0))
            return self.blocks_fd[-1]

    def __init__(self, block_size, n_in, n_out, filters):
        self.block_size = block_size

        self.filters = [(in_ch, out_ch,
                         self.FDConvolverChannel(block_size, filter))
                        for in_ch, out_ch, filter in filters]

        self.input_block = np.zeros((n_in, block_size * 2))
        self.out_block_fd = [FDBuffer(block_size) for _ in range(n_out)]

    @classmethod
    def per_channel(cls, block_size, nchannels, filters):
        """Convenience wrapper for per-channel filters.

        Parameters:
            block_size (int): time domain block size for input and output blocks
            nchannels (int): number of input and output channels
            f (array of (n, nchannels) floats): specification of nchannels length n
                FIR filters to convolve the input channels with.
        """
        return cls(block_size, nchannels, nchannels,
                   [(i, i, f) for i, f in enumerate(np.array(filters).T)])

    def filter_block(self, in_block_td):
        """Filter a time domain block of samples.

        Parameters:
            in_block_td (array of (block_size, n_in) floats): block of
                time domain input samples

        Returns:
            array of (block_size, n_out) floats: block of time domain
                output samples
        """
        self.input_block[:, self.block_size:] = self.input_block[:, :self.
                                                                 block_size]
        self.input_block[:, :self.block_size] = in_block_td.T

        in_block_fd = [
            FDBuffer.from_td(self.block_size, ch) for ch in self.input_block
        ]

        for out_block in self.out_block_fd:
            out_block.clear()

        for in_ch, out_ch, filter in self.filters:
            self.out_block_fd[out_ch] += filter.filter_block(
                in_block_fd[in_ch])

        return FDBuffers_to_td(self.out_block_fd).T


def OverlapSaveConvolver(block_size, nchannels, filters):
    """Wrapper around MatrixBlockConvolver for per-channel convolution,
    implementeing the old API.

    Parameters:
    block_size (int): time domain block size for input and output blocks
    nchannels (int): number of channels to process
    f (array of (n, nchannels) floats): specification of nchannels length n
        FIR filters to convolve the input channels with.
    """
    return MatrixBlockConvolver.per_channel(block_size, nchannels, filters)
