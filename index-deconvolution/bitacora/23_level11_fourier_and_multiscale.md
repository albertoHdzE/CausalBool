# Bitacora 23 — Level 11: The Fourier Split (a Confirmation) and the Multi-Scale Hawkes (an Honest Negative)

Date: 2026-07-13
Status: complete and verified

## Two questions from the assessor

Two follow-ups after the adversarial audit. First: does the Fourier transform, by
splitting a series into sinusoids, isolate the structure from the noise and perhaps
reveal a rhythm to trade? Second: does a multi-scale, power-law Hawkes kernel (open
door 2) beat the single exponential, which under-reproduced the clustering? Both were
run against controls. One confirms; one fails, and the failure is reported in full.

Level 11 is self-contained; Levels 1 to 10 are untouched.

## The Fourier split -- a confirmation in a second language

`level11/spectral.py` is a standard-library radix-2 FFT with a Welch-averaged
periodogram and a log-log slope (the spectral exponent: 0 is white / flat / noise,
negative is red / long-memory). The instrument is checked on two controls that must
behave: white noise returns a slope of -0.001 (flat) and a random walk returns -1.812
(the textbook -2). It separates them, so it can be trusted.

On the twelve long series, the mean spectral exponent of three signals:

    daily log-returns    +0.072   (white; controls' white noise -0.001)
    absolute returns     -0.320   (red; volatility has long memory)
    pivot activity clock -0.541   (red; the fractal clock)

The reading is unambiguous and, importantly, tells us nothing new -- it re-derives the
programme's central split in the language of spectra. The price *moves* are spectrally
white: no dominant frequency, no linear predictability, exactly the efficient-market
signature and consistent with the four independent proofs that direction is
unforecastable. The *volatility* and the *pivot clock* are red: energy piled at low
frequencies, the signature of long memory, consistent with the fractal Fano exponent of
Level 6. Crucially there is no discrete spectral line -- no hidden periodicity -- at any
frequency; the red spectrum is a smooth power law, self-similar, with nothing to phase-
lock a trade onto. So Fourier corroborates (values are noise, the clock is structured)
but does not rescue: it offers no new tradable component. A useful confirmation, not a
discovery.

## The multi-scale Hawkes -- a clean negative, and why

Level 9's single-exponential Hawkes regenerated a Fano clustering exponent of about
0.36 (mean over the twelve; 0.41 for SP500 alone in bitacora 20) against a real 0.51:
one timescale under-captures a self-similar process. The natural fix, and the
literature's, is a power-law kernel, phi(t) ~ t^-(1+gamma), realised as a sum of
exponentials on a fixed geometric grid of ten timescales, with the same three free
numbers (baseline, branching ratio, exponent gamma). `level11/kernels.py` implements it,
fit by exact maximum likelihood with the generalised Ogata recursion.

It failed, and worse than the single exponential:

    real clock Fano exponent        0.512
    single-exponential regenerates  0.355
    power-law regenerates          -0.003   (closer to real on 0 of 12 series)
    out-of-sample gain: single +0.059 vs power-law +0.001 nats/event

The power-law kernel regenerates essentially no clustering and barely beats a Poisson
out of sample. I did not report this at face value; I interrogated it, because a large
clean failure is as suspect as a large clean success. Fixing the branching ratio by
hand at n = 0.6 and sweeping gamma shows the mechanism: in this mixture parametrisation
the simulated clustering *decreases* monotonically with gamma (Fano 0.26 at gamma = 0
down to -0.02 at gamma = 1.5), and the maximum-likelihood fit does not choose a
clustered kernel at all -- it slides to gamma = 0 and, more tellingly, to a branching
ratio of only 0.11 with the baseline carrying 88 per cent of the intensity. The
likelihood-optimal power-law is very nearly Poisson.

The reason is a genuine mismatch, not a bug (the kernel reduces exactly to the Level 9
single exponential when given one component -- tested to 1e-6). The Hawkes
log-likelihood is a *local* object: it rewards explaining each event by the recent past.
With ten timescales available, the model can absorb local bunching into the fastest
components at low overall branching, and the likelihood never rewards reproducing the
*long-range* Fano clustering, which is a global statistic. The single exponential is
*forced* onto one intermediate timescale and a higher branching ratio to fit at all, and
so incidentally regenerates more of the clustering. Generalising the kernel gives the
optimiser room to walk away from the very structure we wanted it to capture.

Honest verdict: a naive power-law Hawkes fit by plain maximum likelihood does not close
the Level 9 clustering gap at daily resolution -- it widens it. The single exponential
remains the better three-number generator here. This does not refute the
market-microstructure literature, which fits power-law Hawkes near criticality; but that
work uses intraday tick data and constrained or regularised fits. The honest next step
is therefore not "a fancier kernel" but a fit whose objective targets the clustering (a
method-of-moments or a Fano-matching penalty), or finer sampling where the extra
timescales are actually populated. Reported as a negative and kept.

## What Level 11 adds

- A spectral confirmation of the programme's central result: values are white, the
  clock is red, no periodic line -- the same split the pivots found, and no new tradable
  structure. Answered the Fourier question honestly: it corroborates, it does not
  rescue.
- A documented negative: the naive multi-scale / power-law Hawkes does not beat the
  single exponential at daily resolution, and the reason (a local likelihood cannot be
  trusted to preserve a global clustering statistic once the kernel is enriched) is
  stated precisely. Open door 2 is not closed, but the naive version of it is.
- The notebook `notebooks/09_oracle_perfect_trader.ipynb` now also explains, for a naive
  reader, why the self-excitation is weaker on 100 stocks than on the twelve survivors
  (survivorship, with the strong-form point that softening-not-collapsing is the
  credential), shows the Fourier split, and keeps the multi-scale negative on the page.

## Verification

Reproduce: `python level11/exp32_multiscale_and_fourier.py` (writes
`results/exp32_multiscale_fourier.json`); `python notebooks/build_09.py` rebuilds the
notebook. Tests:
`python -m pytest level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 95 / 95 (8 new in `level11/test_level11.py`: FFT against a direct DFT, a known
frequency peak, the white/red control spectra, the exact branching ratio, reduction to
the single exponential, and a finite held-out fit). Levels 1 to 10 untouched.
