"""Constants of the Alvi (2018) / GWP3 experimental design.

Every value here is fixed by the source experiment and must not be tuned. They
are collected in one module so that a change to any of them is a visible,
reviewable event rather than a silent edit inside a function.
"""

from __future__ import annotations

import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(BASE, "data")
REFERENCE = os.path.join(BASE, "reference")
RESULTS = os.path.join(BASE, "results")
FIGURES = os.path.join(BASE, "figures")

#: The 199 x 7 monthly panel, 2010-01-31 to 2026-07-31, as sterilised in GWP1.
PANEL_MONTHLY = os.path.join(DATA, "monthly", "sterilized_monthly_data.csv")

#: The GWP3 result record, used as the parity target for every ported routine.
GWP3_RESULTS = os.path.join(REFERENCE, "gwp3", "results.json")

#: Column order is the order used by GWP3; several routines index positionally.
SERIES = ["WTI_CL", "Brent_BZ", "USD_Idx", "CPI", "Fed_Funds", "Ind_Prod", "WTI_Spot"]

#: The series whose regime is forecast. Alvi calls it WTISPLC.
TARGET = "WTI_Spot"

#: Hidden states are ordered by the arithmetic mean of the underlying change, so
#: that the index carries an economic meaning rather than a fitting artefact.
LABELS = ["Bear", "Stagnant", "Bull"]

TRAIN_FRAC = 0.70
VAL_FRAC = 0.15

SEED = 42

#: Baum-Welch restarts; the highest-likelihood solution is retained.
N_RESTARTS = 10

#: Dirichlet pseudo-counts added to the transition diagonal (Fox et al.). This
#: is the probabilistic surrogate for an attractor; see bitacora/00_kickoff.md
#: section 3.2.
STICKY = 5.0

#: Number of hidden states per series.
N_STATES = 3
