# gnuradio playground

## Install gnuradio
```
pip3 install pybombs
pybombs auto-config
pybombs recipes add-defaults
pybombs prefix init ~/.local/gnuradio/ -a gnuradio -R gnuradio-default
pybombs install rtl-sdr
sudo cp ~/.local/gnuradio/src/rtl-sdr/rtl-sdr.rules /etc/udev/rules.d/

pybombs install gqrx gr-osmosdr gr-soapy
```

I have a LimeMini so also:
```
pybombs install limesuite
pybombs install gr-limesdr
```

## scripts

```
# Receive 104.1 FM
./fm_recv 104100000
```

```
# Find frequencies with likely signals (still having stderr redirect issues)
./scanner.py 85000000 107900000
```
