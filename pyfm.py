#!/usr/bin/env python

import sys
import time
import argparse

from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
import osmosdr


def main():
    parser = argparse.ArgumentParser(prog='pyfm', description='fm tuner with gnuradio and rtl-sdr')
    parser.add_argument('-s', '--sample-rate', default=2400000)
    parser.add_argument('-p', '--ppm', default=0)
    parser.add_argument('-f', '--freq', required=True)
    args = parser.parse_args()

    tb = gr.top_block()

    ##################################################
    # Blocks
    ##################################################
    rtlsdr_source_0 = osmosdr.source(args="numchan=1")
    rtlsdr_source_0.set_sample_rate(args.sample_rate)
    rtlsdr_source_0.set_center_freq(float(args.freq), 0)
    rtlsdr_source_0.set_freq_corr(args.ppm, 0)
    rtlsdr_source_0.set_dc_offset_mode(2, 0)
    rtlsdr_source_0.set_iq_balance_mode(2, 0)
    rtlsdr_source_0.set_gain_mode(True, 0)
    rtlsdr_source_0.set_gain(10, 0)
    rtlsdr_source_0.set_if_gain(20, 0)
    rtlsdr_source_0.set_bb_gain(20, 0)
    rtlsdr_source_0.set_antenna('', 0)
    rtlsdr_source_0.set_bandwidth(0, 0)

    rational_resampler_xxx_0 = filter.rational_resampler_ccc(
            interpolation=480000,
            decimation=args.sample_rate / 10,
            taps=None,
            fractional_bw=None,
    )

    low_pass_filter_0 = filter.fir_filter_ccf(10, firdes.low_pass(
    	1, args.sample_rate, 100000, 10000, firdes.WIN_HANN, 6.76))

    audio_sink_0 = audio.sink(48000, '', True)

    analog_wfm_rcv_pll_0 = analog.wfm_rcv_pll(
    	demod_rate=480000,
    	audio_decimation=10,
    )

    ##################################################
    # Connections
    ##################################################
    tb.connect((analog_wfm_rcv_pll_0, 0), (audio_sink_0, 0))
    tb.connect((analog_wfm_rcv_pll_0, 1), (audio_sink_0, 1))
    tb.connect((low_pass_filter_0, 0), (rational_resampler_xxx_0, 0))
    tb.connect((rational_resampler_xxx_0, 0), (analog_wfm_rcv_pll_0, 0))
    tb.connect((rtlsdr_source_0, 0), (low_pass_filter_0, 0))

    tb.start()
    try:
        raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
