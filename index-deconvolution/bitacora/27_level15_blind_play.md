# Bitacora 27 — Level 15: Playing the Buy and Sell Formulae Blindly (Timing Works, Money Does Not)

Date: 2026-07-13
Status: complete and verified

## The brief

Before fusing the two formulae, play them separately and blindly on the historical data,
out of sample, and find a graphical, understandable, rigorous way to prove whether they
work. If they do, the fusion step is licensed. The assessor also insisted -- rightly --
on scientific rigour and on a sector-diverse panel.

Two questions, kept strictly apart because they have opposite answers: does the formula
predict the timing of the next turn (timing), and does trading its signals blindly make
money (money). Level 15 is self-contained; Levels 1 to 14 are untouched.

## The instrument

`level15/blindplay.py`. Each formula is fitted on the first seventy per cent of time
only. On the held-out thirty per cent, at each day, the causal Hawkes intensity (built
solely from past events) gives the predicted chance of a turn within the next ten days;
the label is whether a turn truly arrived in that window. The ranking is scored by the
ROC area (0.5 is a coin flip), the Brier score, and a reliability curve, against a
return-shuffle that must sit at 0.5. Separately, a blind causal trading play acts at the
confirmed turns -- buy when a downturn confirms, sell when an upturn confirms, no
look-ahead -- and its terminal wealth is compared with buy-and-hold and with the
look-ahead oracle.

## Result 1 — timing works, weakly but for real (against the shuffle, across sectors)

On the 100-stock panel, out of sample:

    pattern   mean ROC-AUC   excess over shuffle   beats shuffle
    BUY          0.554            +0.055              83 / 100
    SELL         0.555            +0.055              84 / 100

The shuffle sits exactly at 0.5. The formula's out-of-sample AUC is a small but
consistent 0.055 above it, on more than four fifths of the panel, with roughly calibrated
probabilities (the reliability curve tracks the diagonal on a representative stock). This
is a genuine, weak timing edge, the honest out-of-sample face of the self-exciting clock.

Sector rigour. The 100 stocks span eleven GICS sectors by construction. Stratifying the
AUC-excess within each sector, the edge is positive in essentially every sector -- it is a
broad market property, not an artefact of one industry. This directly answers the
assessor's demand for a sector-diverse test.

An honest note on variance: the edge is a panel property, not a guarantee per stock.
About one stock in six shows no edge at all (KO, for instance, sits at AUC 0.50); the
illustration stock in the notebook (CVS, AUC 0.555) was chosen to sit at the panel mean,
neither the strongest nor the weakest, and the full spread -- including the null cases --
is shown in the panel histogram rather than hidden.

## Result 2 — money does not (the ceiling, made visible)

The same events, traded blindly and causally:

    play                         terminal wealth (median across the panel)
    blind causal play            0.08x of buy-and-hold
    look-ahead oracle            ~2e18x of buy-and-hold

The blind causal play beats buy-and-hold on only 11 of 100 stocks with no cost, and 3 of
100 after a tenth-of-a-per-cent trading cost; its median outcome is eight per cent of
simply holding. The look-ahead oracle, by contrast, beats buy-and-hold by eighteen orders
of magnitude -- because it cheats, knowing the future by construction. The chasm between
them is the value of the crystal ball, which no causal play has. Timing skill is not
trading skill: sensing when turbulence clusters (a weak, real edge) does not tell you
which way the price will go, and the confirmed turns lag the extremes by the reversal
threshold, so acting on them loses to holding. This is the Level 8 ceiling, now shown as
two equity curves rather than asserted.

## The verdict, and the green light for fusion

Timing works, weakly and out of sample and across sectors, beating the shuffle on more
than four fifths of a hundred stocks. Money does not, and the programme always said it
would not. So the fusion step is licensed -- but strictly as a better timing model, never
a money machine. The honest question fusion must answer is whether coupling the buy and
sell strands (a mutually-exciting bivariate Hawkes, in which a buy raises the chance of
the next sell and a sell the next buy) forecasts the timing better than the two formulae
apart. That is the next level. This one earned the right to attempt it, and drew the line
around what it can hope to achieve.

## The notebook

`notebooks/11_blind_play.ipynb` shows the whole thing graphically for a naive reader: the
ROC curve above the diagonal with its shuffle on it, the reliability curve, the
walk-forward intensity rising where turns cluster on unseen data, the two equity curves
(blind play far below buy-and-hold, oracle off the chart), the panel AUC-excess
histogram, the per-sector breakdown, and the panel money histogram. Executed end to end
from a foreign working directory: seven embedded plots, zero errors.

## Verification

Reproduce: `python level15/exp37_blind_play.py` (writes `results/exp37_blind_play.json`);
`python notebooks/build_11.py` rebuilds the notebook. Tests:
`python -m pytest level15 level14 level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 122 / 122 (7 new in `level15/test_level15.py`: the ROC area on perfect, wrong,
tied and degenerate inputs, the Brier bounds, the reliability binning, the forecast
shapes and labels, that a genuine Hawkes stream is forecastable above chance, and the
causal-equity and buy-and-hold helpers). Levels 1 to 14 untouched.
