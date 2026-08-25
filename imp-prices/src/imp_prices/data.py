"""Loading and chronological allocation of the monthly panel.

Ported from ``reference/gwp3/gwp3_pipeline.py`` and asserted against
``reference/gwp3/results.json`` in ``tests/test_reference_parity.py``. The port
is deliberately literal: any deviation would silently invalidate every
comparison this package intends to make.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import PANEL_MONTHLY, SERIES, TARGET, TRAIN_FRAC, VAL_FRAC


@dataclass(frozen=True)
class Split:
    """A chronological allocation of the panel.

    The division respects the arrow of time: every observation used for model
    selection postdates every observation used for estimation, and every
    observation used for testing postdates both.
    """

    full: pd.DataFrame
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame

    def __iter__(self):
        return iter((self.full, self.train, self.val, self.test))

    @property
    def sizes(self) -> tuple[int, int, int]:
        return len(self.train), len(self.val), len(self.test)


def load_panel(path: str = PANEL_MONTHLY) -> pd.DataFrame:
    """Read the sterilised monthly panel, columns in the GWP3 order."""
    return pd.read_csv(path, parse_dates=["Date"], index_col="Date")[SERIES]


def load_and_split(train_frac: float = TRAIN_FRAC,
                   val_frac: float = VAL_FRAC,
                   path: str = PANEL_MONTHLY) -> Split:
    """Allocate the panel 70 / 15 / 15 by position, exactly as GWP3 does.

    ``int(round(n * frac))`` is reproduced literally; on 199 observations it
    yields 139 / 30 / 30.
    """
    df = load_panel(path)
    n = len(df)
    n_tr, n_va = int(round(n * train_frac)), int(round(n * val_frac))
    return Split(df, df.iloc[:n_tr], df.iloc[n_tr:n_tr + n_va], df.iloc[n_tr + n_va:])


def split_summary(split: Split) -> pd.DataFrame:
    """Reproduce GWP3 Table 3: descriptive statistics of the target in each window."""
    rows = []
    for name, part in [("Training", split.train), ("Validation", split.val),
                       ("Testing", split.test)]:
        r = np.log(part[TARGET]).diff().dropna()
        rows.append(dict(Set=name, Months=len(part),
                         Start=str(part.index[0].date()),
                         End=str(part.index[-1].date()),
                         Share=round(100 * len(part) / len(split.full), 1),
                         Mean_price=round(float(part[TARGET].mean()), 2),
                         Mean_logret=round(float(r.mean()), 4),
                         Vol_logret=round(float(r.std()), 4),
                         Min_price=round(float(part[TARGET].min()), 2),
                         Max_price=round(float(part[TARGET].max()), 2)))
    return pd.DataFrame(rows)
