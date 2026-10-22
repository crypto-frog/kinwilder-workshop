<CsoundSynthesizer>
<CsOptions>
-d -W -o sound.wav
</CsOptions>
<CsInstruments>
sr = 22050
ksmps = 32
nchnls = 1
0dbfs = 1
instr 1
aenv linen 0.12, 0.15, p3, 0.8
anote oscili aenv, p4, 1
out anote
endin
</CsInstruments>
<CsScore>
f 1 0 4096 10 1
i 1 0 2.8 261.63
i 1 1.2 3.2 329.63
i 1 2.8 4.2 392.00
i 1 5.8 3.2 293.66
i 1 7.5 4.5 261.63
e
</CsScore>
</CsoundSynthesizer>
