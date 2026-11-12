# Comparison: 0.747 vs v1 vs V2

Error is relative bytes: (announced size - actual size) / actual size. The announced size is
computed only from what Music Assistant knows before it sends the headers: source file size,
whole-second duration, source and output format, and the processing settings.

- **0.747** is the current behaviour: PCM size times 0.747.
- **v1** is the first source-size model (frozen 2026-11-11). For dynamic loudness normalization it
  falls back to 0.747.
- **V2** is the current model (frozen 2026-11-12).

## Development artists

330 FLAC tracks from one private library (72 artists) were split by artist: 70 % development,
30 % locked test. Everything below is from the 50 development artists (1,399 measurements,
encoded with ffmpeg 9.0.1 through Music Assistant's own pipeline code).

- V2's two fitted offsets are scored by artist-grouped 5-fold cross-validation: each track is
  predicted with offsets fitted on other artists.
- v1's offsets were set on all 330 tracks, so v1 is in-sample here.
- **The locked test artists have not been scored yet.** These are development numbers.
- The 24-bit rows rest on 5 artists.

### Median absolute error

| Setting | Source | Out | Regime | Tracks | 0.747 | v1 | V2 |
|---|---|---|---|---|---|---|---|
| No processing (bit-exact copy) | 16-bit | 16-bit | R0 | 159 | 18.1 % | 1.4 % | 1.4 % |
| No processing (bit-exact copy) | 24-bit | 24-bit | R0 | 31 | 13.3 % | 1.0 % | 1.0 % |
| Float path, no sample changed, 24-bit out | 16-bit | 24-bit | R1 | 159 | 73.0 % | 2.3 % | 1.5 % |
| Float path, no sample changed, 24-bit out | 24-bit | 24-bit | R1 | 31 | 13.3 % | 1.0 % | 1.0 % |
| Float path, 16-bit out (dither only) | 16-bit | 16-bit | R3 | 159 | 17.9 % | 1.4 % | 1.4 % |
| Float path, 16-bit out (dither only) | 24-bit | 16-bit | R3 | 31 | 51.8 % | 2.2 % | 2.7 % |
| Measured-loudness gain, 24-bit out | 16-bit | 24-bit | R1 | 2 | 84.0 % | 2.3 % | 1.8 % |
| Measured-loudness gain, 24-bit out | 16-bit | 24-bit | R2 | 157 | 3.5 % | 0.8 % | 0.8 % |
| Measured-loudness gain, 24-bit out | 24-bit | 24-bit | R2 | 31 | 11.9 % | 1.0 % | 1.1 % |
| Measured-loudness gain, 16-bit out | 16-bit | 16-bit | R3 | 159 | 17.6 % | 1.3 % | 1.4 % |
| Measured-loudness gain, 16-bit out | 24-bit | 16-bit | R3 | 31 | 49.3 % | 2.0 % | 2.6 % |
| Fixed gain -6 dB, 24-bit out | 16-bit | 24-bit | R2 | 159 | 5.3 % | 0.9 % | 0.8 % |
| Fixed gain -6 dB, 24-bit out | 24-bit | 24-bit | R2 | 31 | 21.0 % | 1.0 % | 1.2 % |
| Measured gain + 5-band EQ, 24-bit out | 16-bit | 24-bit | R2 | 159 | 3.1 % | 1.9 % | 1.8 % |
| Measured gain + 5-band EQ, 24-bit out | 24-bit | 24-bit | R2 | 31 | 13.3 % | 2.1 % | 2.1 % |
| Measured gain, resampled 96 to 48 kHz | 24-bit | 24-bit | R2 | 5 | 6.0 % | 0.2 % | 0.3 % |
| Dynamic loudness normalization, 24-bit out | 16-bit | 24-bit | R4 | 56 | 3.0 % | 2.9 % | 2.5 % |
| Dynamic loudness normalization, 24-bit out | 24-bit | 24-bit | R4 | 8 | 12.7 % | 13.0 % | 3.2 % |

### Share of tracks within 5 %, and worst cases

Worst cases are signed: negative means the announced size was too short.

| Setting | Source | Out | Tracks | 0.747 within 5 % | v1 within 5 % | V2 within 5 % | 0.747 worst short / long | v1 worst short / long | V2 worst short / long |
|---|---|---|---|---|---|---|---|---|---|
| No processing (bit-exact copy) | 16-bit | 16-bit | 159 | 14 % | 96 % | 96 % | -9 % / +196 % | -16 % / +13 % | -16 % / +12 % |
| No processing (bit-exact copy) | 24-bit | 24-bit | 31 | 26 % | 97 % | 97 % | -4 % / +36 % | -5 % / +2 % | -5 % / +2 % |
| Float path, no sample changed, 24-bit out | 16-bit | 24-bit | 159 | 0 % | 87 % | 92 % | +35 % / +319 % | -19 % / +6 % | -17 % / +11 % |
| Float path, no sample changed, 24-bit out | 24-bit | 24-bit | 31 | 26 % | 97 % | 97 % | -4 % / +36 % | -5 % / +2 % | -5 % / +2 % |
| Float path, 16-bit out (dither only) | 16-bit | 16-bit | 159 | 14 % | 95 % | 95 % | -9 % / +180 % | -16 % / +7 % | -16 % / +6 % |
| Float path, 16-bit out (dither only) | 24-bit | 16-bit | 31 | 0 % | 68 % | 65 % | +11 % / +105 % | -21 % / +4 % | -14 % / +106 % |
| Measured-loudness gain, 24-bit out | 16-bit | 24-bit | 2 | 0 % | 100 % | 100 % | +57 % / +111 % | -4 % / -1 % | -2 % / +2 % |
| Measured-loudness gain, 24-bit out | 16-bit | 24-bit | 157 | 66 % | 98 % | 98 % | -11 % / +14 % | -8 % / +4 % | -8 % / +4 % |
| Measured-loudness gain, 24-bit out | 24-bit | 24-bit | 31 | 29 % | 97 % | 90 % | -3 % / +30 % | -5 % / +2 % | -5 % / +30 % |
| Measured-loudness gain, 16-bit out | 16-bit | 16-bit | 159 | 9 % | 96 % | 95 % | -2 % / +56 % | -17 % / +8 % | -17 % / +7 % |
| Measured-loudness gain, 16-bit out | 24-bit | 16-bit | 31 | 0 % | 61 % | 58 % | +14 % / +88 % | -17 % / +4 % | -13 % / +86 % |
| Fixed gain -6 dB, 24-bit out | 16-bit | 24-bit | 159 | 45 % | 98 % | 98 % | -11 % / +61 % | -9 % / +4 % | -8 % / +4 % |
| Fixed gain -6 dB, 24-bit out | 24-bit | 24-bit | 31 | 10 % | 97 % | 90 % | +1 % / +47 % | -6 % / +2 % | -6 % / +47 % |
| Measured gain + 5-band EQ, 24-bit out | 16-bit | 24-bit | 159 | 67 % | 97 % | 98 % | -10 % / +17 % | -8 % / +5 % | -7 % / +5 % |
| Measured gain + 5-band EQ, 24-bit out | 24-bit | 24-bit | 31 | 26 % | 100 % | 94 % | -2 % / +32 % | -3 % / +3 % | -3 % / +32 % |
| Measured gain, resampled 96 to 48 kHz | 24-bit | 24-bit | 5 | 40 % | 100 % | 100 % | +3 % / +10 % | -1 % / +1 % | -1 % / +1 % |
| Dynamic loudness normalization, 24-bit out | 16-bit | 24-bit | 56 | 71 % | 71 % | 84 % | -12 % / +12 % | -12 % / +12 % | -10 % / +4 % |
| Dynamic loudness normalization, 24-bit out | 24-bit | 24-bit | 8 | 12 % | 12 % | 75 % | +0 % / +26 % | +1 % / +26 % | -10 % / +3 % |

## Constructed files (rule checks)

Files built to test specific cases. Each cell: median absolute error (worst short / worst long).
V2's one-channel dither term was set from the one-channel files in this set; every other row is a check, not a fit.

| Source kind | Setting | Tracks | 0.747 | v1 | V2 |
|---|---|---|---|---|---|
| Stereo file with identical channels | Float path, 16-bit out (dither only) | 24 | 67.0 % (+44 / +121) | 18.2 % (-26 / -15) | 18.5 % (-26 / -15) |
| Stereo file with identical channels | Dynamic loudness normalization, 24-bit out | 24 | 89.9 % (+74 / +124) | 90.3 % (+74 / +124) | 46.1 % (+38 / +58) |
| Stereo file with identical channels | No processing (bit-exact copy) | 24 | 120.2 % (+83 / +225) | 8.0 % (+2 / +22) | 7.5 % (+2 / +21) |
| Stereo file with identical channels | Fixed gain -6 dB, 24-bit out | 24 | 100.8 % (+78 / +149) | 44.0 % (+38 / +58) | 44.0 % (+38 / +58) |
| Stereo file with identical channels | Measured-loudness gain, 16-bit out | 24 | 69.2 % (+51 / +143) | 19.2 % (-37 / -7) | 19.6 % (-38 / -8) |
| Stereo file with identical channels | Measured-loudness gain, 24-bit out | 24 | 91.6 % (+75 / +148) | 47.0 % (+39 / +62) | 47.1 % (+39 / +62) |
| Stereo file with identical channels | Measured gain + 5-band EQ, 24-bit out | 24 | 95.0 % (+76 / +154) | 49.5 % (+41 / +65) | 49.6 % (+41 / +66) |
| Stereo file with identical channels | Float path, no sample changed, 24-bit out | 24 | 230.2 % (+174 / +387) | 7.4 % (+1 / +21) | 11.1 % (+5 / +26) |
| One-channel file | Float path, 16-bit out (dither only) | 24 | 67.0 % (+44 / +121) | 18.2 % (-26 / -15) | 1.0 % (-4 / +8) |
| One-channel file | Dynamic loudness normalization, 24-bit out | 24 | 85.4 % (+70 / +118) | 85.8 % (+71 / +119) | 1.8 % (-12 / +3) |
| One-channel file | No processing (bit-exact copy) | 24 | 120.2 % (+83 / +225) | 7.9 % (+2 / +22) | 2.4 % (-4 / +14) |
| One-channel file | Fixed gain -6 dB, 24-bit out | 24 | 100.8 % (+78 / +149) | 4.4 % (+1 / +12) | 1.7 % (-2 / +8) |
| One-channel file | Measured-loudness gain, 16-bit out | 24 | 62.8 % (+47 / +133) | 17.2 % (-26 / -12) | 1.7 % (-3 / +9) |
| One-channel file | Measured-loudness gain, 24-bit out | 24 | 86.9 % (+70 / +218) | 4.3 % (+1 / +10) | 1.7 % (-2 / +7) |
| One-channel file | Measured gain + 5-band EQ, 24-bit out | 24 | 89.8 % (+72 / +145) | 5.8 % (+3 / +13) | 2.7 % (-0 / +9) |
| One-channel file | Float path, no sample changed, 24-bit out | 24 | 230.2 % (+174 / +387) | 7.3 % (+1 / +21) | 3.6 % (-2 / +16) |
| MP3 decoded and stored as FLAC | Float path, 16-bit out (dither only) | 24 | 11.5 % (-10 / +76) | 1.1 % (-5 / +2) | 1.2 % (-6 / +2) |
| MP3 decoded and stored as FLAC | Dynamic loudness normalization, 24-bit out | 24 | 7.9 % (-13 / +15) | 7.7 % (-12 / +15) | 2.3 % (-11 / +5) |
| MP3 decoded and stored as FLAC | No processing (bit-exact copy) | 24 | 11.5 % (-10 / +77) | 1.2 % (-5 / +2) | 1.2 % (-6 / +2) |
| MP3 decoded and stored as FLAC | Fixed gain -6 dB, 24-bit out | 24 | 6.5 % (-12 / +30) | 0.9 % (-3 / +1) | 0.8 % (-3 / +1) |
| MP3 decoded and stored as FLAC | Measured-loudness gain, 16-bit out | 24 | 11.7 % (-4 / +89) | 1.2 % (-6 / +2) | 1.3 % (-7 / +2) |
| MP3 decoded and stored as FLAC | Measured-loudness gain, 24-bit out | 24 | 7.5 % (-12 / +26) | 0.8 % (-3 / +2) | 0.8 % (-3 / +2) |
| MP3 decoded and stored as FLAC | Measured gain + 5-band EQ, 24-bit out | 24 | 8.1 % (-11 / +29) | 1.3 % (-1 / +3) | 1.3 % (-1 / +3) |
| MP3 decoded and stored as FLAC | Float path, no sample changed, 24-bit out | 24 | 64.9 % (+32 / +165) | 3.4 % (-8 / -0) | 2.0 % (-6 / +3) |
| 16-bit audio in a 24-bit file | Float path, 16-bit out (dither only) | 24 | 11.5 % (-10 / +75) | 71.8 % (-96 / -58) | 11.5 % (-10 / +76) |
| 16-bit audio in a 24-bit file | Dynamic loudness normalization, 24-bit out | 24 | 7.8 % (-13 / +15) | 7.7 % (-12 / +15) | 7.7 % (-12 / +15) |
| 16-bit audio in a 24-bit file | No processing (bit-exact copy) | 24 | 65.0 % (+32 / +163) | 1.6 % (-3 / +8) | 1.7 % (-3 / +8) |
| 16-bit audio in a 24-bit file | Fixed gain -6 dB, 24-bit out | 24 | 6.5 % (-12 / +30) | 43.6 % (-58 / -38) | 6.3 % (-12 / +30) |
| 16-bit audio in a 24-bit file | Measured-loudness gain, 16-bit out | 24 | 11.8 % (-4 / +87) | 71.4 % (-96 / -62) | 12.0 % (-3 / +88) |
| 16-bit audio in a 24-bit file | Measured-loudness gain, 24-bit out | 24 | 7.3 % (-12 / +25) | 41.5 % (-55 / -37) | 7.7 % (-12 / +26) |
| 16-bit audio in a 24-bit file | Measured gain + 5-band EQ, 24-bit out | 24 | 7.7 % (-11 / +28) | 40.5 % (-54 / -36) | 7.8 % (-11 / +29) |
| 16-bit audio in a 24-bit file | Float path, no sample changed, 24-bit out | 24 | 65.0 % (+32 / +163) | 1.6 % (-3 / +8) | 1.7 % (-3 / +8) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Float path, 16-bit out (dither only) | 7 | 51.6 % (+1 / +69) | 95.5 % (-96 / -66) | 51.9 % (+1 / +70) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Dynamic loudness normalization, 24-bit out | 7 | 11.4 % (-7 / +20) | 11.7 % (-7 / +20) | 11.7 % (-7 / +20) |
| 24-bit audio cut to 16 bits, in a 24-bit file | No processing (bit-exact copy) | 7 | 126.6 % (+47 / +143) | 2.7 % (-12 / +4) | 2.8 % (-12 / +4) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Fixed gain -6 dB, 24-bit out | 7 | 20.7 % (-5 / +29) | 53.2 % (-60 / -41) | 20.9 % (-5 / +29) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Measured-loudness gain, 16-bit out | 7 | 50.1 % (+8 / +70) | 95.4 % (-96 / -70) | 50.5 % (+8 / +71) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Measured-loudness gain, 24-bit out | 7 | 12.3 % (-6 / +21) | 47.8 % (-59 / -41) | 12.7 % (-6 / +22) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Measured gain, resampled 96 to 48 kHz | 1 | 4.3 % (+4 / +4) | 48.5 % (-48 / -48) | 4.4 % (+4 / +4) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Measured gain + 5-band EQ, 24-bit out | 7 | 14.1 % (-5 / +24) | 46.6 % (-59 / -40) | 14.4 % (-5 / +25) |
| 24-bit audio cut to 16 bits, in a 24-bit file | Float path, no sample changed, 24-bit out | 7 | 126.6 % (+47 / +143) | 2.7 % (-12 / +4) | 2.8 % (-12 / +4) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Float path, 16-bit out (dither only) | 7 | 51.8 % (+1 / +70) | 45.1 % (-66 / -30) | 52.1 % (-37 / +70) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Dynamic loudness normalization, 24-bit out | 7 | 11.4 % (-7 / +20) | 11.7 % (-7 / +21) | 15.7 % (-19 / +21) |
| 24-bit audio cut to 20 bits, in a 24-bit file | No processing (bit-exact copy) | 7 | 50.5 % (+11 / +59) | 2.7 % (-10 / +3) | 2.7 % (-10 / +3) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Fixed gain -6 dB, 24-bit out | 7 | 21.0 % (-5 / +30) | 23.6 % (-35 / -19) | 21.2 % (-21 / +30) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Measured-loudness gain, 16-bit out | 7 | 50.1 % (+8 / +71) | 44.4 % (-73 / -33) | 50.5 % (-38 / +71) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Measured-loudness gain, 24-bit out | 7 | 12.3 % (-6 / +21) | 22.3 % (-34 / -19) | 18.5 % (-20 / +22) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Measured gain, resampled 96 to 48 kHz | 1 | 4.3 % (+4 / +4) | 26.8 % (-27 / -27) | 4.5 % (+4 / +4) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Measured gain + 5-band EQ, 24-bit out | 7 | 14.1 % (-5 / +25) | 20.5 % (-34 / -18) | 17.9 % (-19 / +25) |
| 24-bit audio cut to 20 bits, in a 24-bit file | Float path, no sample changed, 24-bit out | 7 | 50.5 % (+11 / +59) | 2.7 % (-10 / +3) | 2.7 % (-10 / +3) |
| 44.1 kHz upsampled to 96 kHz | Float path, 16-bit out (dither only) | 24 | 47.8 % (+9 / +146) | 11.1 % (-3 / +50) | 10.8 % (-3 / +50) |
| 44.1 kHz upsampled to 96 kHz | Dynamic loudness normalization, 24-bit out | 24 | 11.6 % (-2 / +36) | 11.9 % (-1 / +36) | 5.6 % (-7 / +19) |
| 44.1 kHz upsampled to 96 kHz | No processing (bit-exact copy) | 24 | 11.9 % (-6 / +44) | 6.5 % (-1 / +22) | 6.5 % (-1 / +22) |
| 44.1 kHz upsampled to 96 kHz | Fixed gain -6 dB, 24-bit out | 24 | 19.4 % (-0 / +56) | 6.8 % (-1 / +24) | 6.9 % (-1 / +24) |
| 44.1 kHz upsampled to 96 kHz | Measured-loudness gain, 16-bit out | 24 | 48.2 % (+19 / +176) | 11.5 % (-2 / +49) | 11.2 % (-3 / +48) |
| 44.1 kHz upsampled to 96 kHz | Measured-loudness gain, 24-bit out | 24 | 12.5 % (-1 / +54) | 6.6 % (-1 / +24) | 6.6 % (-1 / +24) |
| 44.1 kHz upsampled to 96 kHz | Measured gain, resampled 96 to 48 kHz | 24 | 8.0 % (-12 / +28) | 7.1 % (+1 / +21) | 7.1 % (+2 / +21) |
| 44.1 kHz upsampled to 96 kHz | Measured gain + 5-band EQ, 24-bit out | 24 | 13.8 % (-0 / +57) | 7.7 % (-0 / +27) | 7.8 % (-0 / +27) |
| 44.1 kHz upsampled to 96 kHz | Float path, no sample changed, 24-bit out | 24 | 11.9 % (-6 / +44) | 6.5 % (-1 / +22) | 6.5 % (-1 / +22) |

## DSP filters (rule checks)

30 development tracks, 25 artists, each filter alone, 24-bit output. Each cell: median absolute error (worst short / worst long).
V2 counts the gain filter's dB and half the balance attenuation; v1 ignores every filter.

| Filter | With measured-loudness gain | Tracks | 0.747 | v1 | V2 |
|---|---|---|---|---|---|
| Balance 30 | no | 30 | 5.2 % (-12 / +52) | 1.7 % (-3 / +7) | 0.9 % (-5 / +4) |
| Balance 30 | yes | 30 | 3.6 % (-9 / +23) | 1.6 % (-3 / +5) | 0.8 % (-5 / +4) |
| Gain -6 dB | no | 30 | 8.1 % (-9 / +61) | 6.0 % (+3 / +13) | 0.7 % (-4 / +4) |
| Gain -6 dB | yes | 30 | 3.8 % (-5 / +30) | 6.0 % (+3 / +11) | 0.7 % (-4 / +4) |
| Gain +3 dB | no | 30 | 6.3 % (-15 / +43) | 2.4 % (-7 / +0) | 0.8 % (-4 / +4) |
| Gain +3 dB | yes | 30 | 5.9 % (-12 / +18) | 2.4 % (-7 / +0) | 0.8 % (-4 / +3) |
| High-pass 80 Hz | no | 30 | 5.6 % (-13 / +49) | 0.7 % (-4 / +4) | 0.7 % (-4 / +4) |
| High-pass 80 Hz | yes | 30 | 3.8 % (-10 / +22) | 0.7 % (-4 / +4) | 0.8 % (-4 / +4) |
| Limiter -2 dB | no | 30 | 42.8 % (-3 / +319) | 43.6 % (-4 / +193) | 43.6 % (-4 / +193) |
| Limiter -2 dB | yes | 30 | 3.8 % (-10 / +22) | 0.7 % (-4 / +4) | 0.7 % (-4 / +4) |
| Limiter -6 dB | no | 30 | 14.8 % (-9 / +319) | 15.9 % (-4 / +193) | 16.0 % (-4 / +193) |
| Limiter -6 dB | yes | 30 | 3.7 % (-10 / +22) | 1.0 % (-4 / +4) | 1.0 % (-4 / +4) |
| Low-pass 8 kHz, 24 dB/oct | no | 30 | 7.1 % (-7 / +66) | 6.8 % (-0 / +16) | 6.8 % (-0 / +16) |
| Low-pass 8 kHz, 24 dB/oct | yes | 30 | 3.3 % (-3 / +30) | 6.8 % (-0 / +14) | 6.9 % (-0 / +14) |
| Parametric EQ, 5 bands, preamp -3 dB | no | 30 | 5.1 % (-13 / +52) | 1.9 % (-1 / +7) | 2.0 % (-1 / +7) |
| Parametric EQ, 5 bands, preamp -3 dB | yes | 30 | 3.2 % (-9 / +25) | 1.9 % (-1 / +5) | 2.0 % (-1 / +5) |
| Parametric EQ, two +6 dB shelves, preamp -6 dB | no | 30 | 5.2 % (-12 / +54) | 2.3 % (-1 / +8) | 2.4 % (-1 / +8) |
| Parametric EQ, two +6 dB shelves, preamp -6 dB | yes | 30 | 3.4 % (-9 / +26) | 2.3 % (-1 / +6) | 2.3 % (-1 / +6) |
| Tone +4 bass, +3 treble | no | 30 | 6.1 % (-14 / +47) | 1.6 % (-6 / +3) | 1.6 % (-6 / +3) |
| Tone +4 bass, +3 treble | yes | 30 | 5.4 % (-11 / +19) | 1.6 % (-6 / +2) | 1.6 % (-6 / +2) |
| Tone -6 bass, -6 treble | no | 30 | 6.3 % (-11 / +54) | 3.8 % (-0 / +8) | 3.8 % (-0 / +8) |
| Tone -6 bass, -6 treble | yes | 30 | 2.6 % (-7 / +26) | 3.8 % (-0 / +6) | 3.9 % (-0 / +6) |
