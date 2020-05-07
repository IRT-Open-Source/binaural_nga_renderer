import numpy as np
from scipy import signal

"""a function to align IRs of different emitter-positions"""

def align_irs(irs):

    oversample_fact = 2
    irs_os = []
    for ir in irs:
        irs_os.append(signal.resample(ir, len(ir[0]) * oversample_fact, axis=1))

    irs = np.array(irs_os)
    listofdelays = []
    listLmax = []
    listRmax = []
    list_min_delay = []
    list_of_peaks = []

    posorneg = np.max(irs)
    for ir in irs:
        if posorneg < 0:
            max_amp_l = np.argmax(-ir[0, :])
            max_amp_r = np.argmax(-ir[1, :])
        elif posorneg > 0:
            max_amp_l = np.argmax(ir[0, :])
            max_amp_r = np.argmax(ir[1, :])


        if max_amp_l <= max_amp_r:
            if posorneg < 0:
                peak = signal.find_peaks(-ir[0, :], height=0.2)
            else:
                peak = signal.find_peaks(ir[0, :], height=0.2)

            if len(peak[0]) >= 2 and peak[0][0] <= peak[0][1] and max_amp_r - max_amp_l <= oversample_fact * 20:
                max_amp_l = peak[0][0]
            list_of_peaks.append(peak[0])
            list_min_delay.append(max_amp_l)

        else:
            if posorneg < 0:
                peak = signal.find_peaks(-ir[1, :], height=0.2)
            else:
                peak = signal.find_peaks(ir[1, :], height=0.2)

            if len(peak[0]) >= 2 and peak[0][0] <= peak[0][1] and max_amp_l-max_amp_r <= oversample_fact * 20:
                max_amp_r = peak[0][0]
            list_of_peaks.append(peak[0])
            list_min_delay.append(max_amp_r)
    
        maxamp_avg = np.average([max_amp_l, max_amp_r])
        listofdelays.append(maxamp_avg)
        listLmax.append(max_amp_l)
        listRmax.append(max_amp_r)

    maxdelay = int(np.amax(list_min_delay))


    irs_aligned = []
    list_of_lengths = []
    for i_idx, ir in enumerate(irs):
        if listLmax[i_idx] <= listRmax[i_idx]:
            irs_aligned.append(np.concatenate(((np.zeros((2, maxdelay-listLmax[i_idx]))), ir[:, :]), axis=1))
        else:
            irs_aligned.append(np.concatenate(((np.zeros((2, maxdelay-listRmax[i_idx]))), ir[:, :]), axis=1))
        list_of_lengths.append(np.shape(irs_aligned[i_idx])[1])

    max_length = np.amax(list_of_lengths)

    irs_final = []
    for ir_aligned in irs_aligned:
        irs_final.append(np.concatenate(((ir_aligned[:], np.zeros((2, max_length - np.shape(ir_aligned[0])[0])))), axis=1))

    irs_final = signal.resample(irs_final, int(len(irs_final[0][0]) / oversample_fact), axis=2)           

    return irs_final