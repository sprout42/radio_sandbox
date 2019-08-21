#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import argparse
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.fft import logpwrfft
from gnuradio.filter import firdes
from optparse import OptionParser
import osmosdr
import time

# https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/
from contextlib import contextmanager
import ctypes
import io
import os, sys
import tempfile

libc = ctypes.CDLL(None)
c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

@contextmanager
def redirect_stderr(stream):
    # The original fd stderr points to. Usually 1 on POSIX systems.
    original_stderr_fd = sys.stderr.fileno()

    def _redirect_stderr(to_fd):
        """Redirect stderr to the given file descriptor."""
        # Flush the C-level buffer stderr
        libc.fflush(c_stderr)
        # Flush and close sys.stderr - also closes the file descriptor (fd)
        sys.stderr.close()
        # Make original_stderr_fd point to the same file as to_fd
        os.dup2(to_fd, original_stderr_fd)
        # Create a new sys.stderr that points to the redirected fd
        sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, 'wb'))

    # Save a copy of the original stderr fd in saved_stderr_fd
    saved_stderr_fd = os.dup(original_stderr_fd)
    try:
        # Create a temporary file and redirect stderr to it
        tfile = tempfile.TemporaryFile(mode='w+b')
        _redirect_stderr(tfile.fileno())
        # Yield to caller, then redirect stderr back to the saved fd
        yield
        _redirect_stderr(saved_stderr_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stderr_fd)


class scanner(gr.top_block):
    def __init__(self, ppm, bin_size, sample_rate, bandwidth, **kwargs):
        gr.top_block.__init__(self, "scanner")

        ##################################################
        # Variables
        ##################################################
        self.freq = freq = 879000000
        self.bin_size = bin_size
        self.bandwidth = bandwidth
        self.sample_rate = sample_rate
        self.ppm = ppm

        self.freq_min = freq_min = freq - (bandwidth  / 2)
        self.freq_max = freq_max = freq + (bandwidth  / 2)
        self.fft_bins = fft_bins = bandwidth / bin_size

        ##################################################
        # Blocks
        ##################################################
        self.rtlsdr_source_0 = osmosdr.source(args="numchan=1")
        self.rtlsdr_source_0.set_sample_rate(sample_rate)
        self.rtlsdr_source_0.set_center_freq(freq, 0)
        self.rtlsdr_source_0.set_freq_corr(ppm, 0)
        self.rtlsdr_source_0.set_dc_offset_mode(2, 0)
        self.rtlsdr_source_0.set_iq_balance_mode(2, 0)
        self.rtlsdr_source_0.set_gain_mode(True, 0)
        self.rtlsdr_source_0.set_gain(10, 0)
        self.rtlsdr_source_0.set_if_gain(20, 0)
        self.rtlsdr_source_0.set_bb_gain(20, 0)
        self.rtlsdr_source_0.set_antenna('', 0)
        self.rtlsdr_source_0.set_bandwidth(bandwidth, 0)

        self.fft_probe = blocks.probe_signal_vf(fft_bins)
        self.logpwrfft_x_0 = logpwrfft.logpwrfft_c(
        	sample_rate=sample_rate,
        	fft_size=fft_bins,
        	ref_scale=2,
        	frame_rate=30,
        	avg_alpha=1.0,
        	average=True,
        )
        self.freq_probe = blocks.probe_signal_f()
        self.blocks_short_to_float_0 = blocks.short_to_float(1, 1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_short*1)
        self.blocks_multiply_const_xx_0 = blocks.multiply_const_ff(bin_size)
        self.blocks_argmax_xx_0 = blocks.argmax_fs(fft_bins)
        self.blocks_add_const_vxx_0 = blocks.add_const_vff((freq_min, ))
        self.bin_probe = blocks.probe_signal_s()

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_add_const_vxx_0, 0), (self.freq_probe, 0))
        self.connect((self.blocks_argmax_xx_0, 0), (self.bin_probe, 0))
        self.connect((self.blocks_argmax_xx_0, 1), (self.blocks_null_sink_0, 0))
        self.connect((self.blocks_argmax_xx_0, 0), (self.blocks_short_to_float_0, 0))
        self.connect((self.blocks_multiply_const_xx_0, 0), (self.blocks_add_const_vxx_0, 0))
        self.connect((self.blocks_short_to_float_0, 0), (self.blocks_multiply_const_xx_0, 0))
        self.connect((self.logpwrfft_x_0, 0), (self.blocks_argmax_xx_0, 0))
        self.connect((self.logpwrfft_x_0, 0), (self.fft_probe, 0))
        self.connect((self.rtlsdr_source_0, 0), (self.logpwrfft_x_0, 0))

    def get_output_fft(self):
        return self.fft_probe.level()

    def get_output_fft_bin(self):
        return self.bin_probe.level()

    def get_output_freq(self):
        return self.freq_probe.level()

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.set_freq_min(self.freq - (self.bandwidth  / 2))
        self.rtlsdr_source_0.set_center_freq(self.freq, 0)
        self.set_freq_max(self.freq + (self.bandwidth  / 2))

    def get_bin_size(self):
        return self.bin_size

    def set_bin_size(self, bin_size):
        self.bin_size = bin_size
        self.set_fft_bins(self.bandwidth / self.bin_size)
        self.blocks_multiply_const_xx_0.set_k(self.bin_size)

    def get_bandwidth(self):
        return self.bandwidth

    def set_bandwidth(self, bandwidth):
        self.bandwidth = bandwidth
        self.set_freq_min(self.freq - (self.bandwidth  / 2))
        self.set_fft_bins(self.bandwidth / self.bin_size)
        self.rtlsdr_source_0.set_bandwidth(self.bandwidth, 0)
        self.set_freq_max(self.freq + (self.bandwidth  / 2))

    def get_sample_rate(self):
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.rtlsdr_source_0.set_sample_rate(self.sample_rate)
        self.logpwrfft_x_0.set_sample_rate(self.sample_rate)

    def get_ppm(self):
        return self.ppm

    def set_ppm(self, ppm):
        self.ppm = ppm
        self.rtlsdr_source_0.set_freq_corr(self.ppm, 0)

    def get_freq_min(self):
        return self.freq_min

    def set_freq_min(self, freq_min):
        self.freq_min = freq_min
        self.blocks_add_const_vxx_0.set_k((self.freq_min, ))

    def get_freq_max(self):
        return self.freq_max

    def set_freq_max(self, freq_max):
        self.freq_max = freq_max

    def get_fft_bins(self):
        return self.fft_bins

    def set_fft_bins(self, fft_bins):
        self.fft_bins = fft_bins

def main():
    parser = argparse.ArgumentParser(description='Scan frequency range for strong signals')
    parser.add_argument('start_freq', type=int)
    parser.add_argument('stop_freq', type=int)

    parser.add_argument('-s', '--sample-rate', default=2400000)
    parser.add_argument('-p', '--ppm', default=0)
    parser.add_argument('-B', '--bin-size', default=100)
    parser.add_argument('-b', '--bandwidth', default=100000)
    parser.add_argument('-t', '--sample-time', type=float, default=0.2)
    args = parser.parse_args()

    tb = scanner(**vars(args))

    try:
        # Suppress annoying gnuradio error messages
        #new_stderr = open('/dev/null', 'w')
        #new_stderr = io.BytesIO()
        #with redirect_stderr(new_stderr):
        # Loop from start to stop aiming the center frequency being scanned to 
        # be bandwidth / 2 Hz above the start and below the stop
        for freq_min in range(args.start_freq, args.stop_freq + 1, args.bandwidth):
            if freq_min + args.bandwidth > args.stop_freq:
                bandwidth = args.stop_freq - freq_min
            else:
                bandwidth = args.bandwidth

            freq = freq_min + (bandwidth / 2)

            tb.set_freq(freq)
            tb.set_bandwidth(bandwidth)
            tb.set_bandwidth(bandwidth)

            tb.start()
            time.sleep(args.sample_time)
            tb.stop()
            tb.wait()

            output_fft_bin = tb.get_output_fft_bin()
            output_freq = tb.get_output_freq()
            output_fft = tb.get_output_fft()

            print('{}: {}\t{}\t{}'.format(freq, output_fft_bin, output_freq, output_fft[output_fft_bin]))
    except Exception as e:
        #print(new_stderr.getvalue().decode('utf-8'))
        raise e


if __name__ == '__main__':
    main()
