from __future__ import annotations

from config import config as cf

import pandas as pd
import random
import numpy as np
import multiprocessing as mp
from tqdm import tqdm
from typing import TypeVar
from enum import Enum

T = TypeVar("T")

DATA_DIR = cf.PROJECT_ROOT / "data"
OUTPUT_GAMS_DIR = DATA_DIR / "Modele_chronologique"
PRODVALUES_PATH = OUTPUT_GAMS_DIR / "prodValues.csv"


class Regime(Enum):
    REGIME_1 = 1
    REGIME_2 = 2


PARAMETERS = {
    Regime.REGIME_1: cf.REGIME_1,
    Regime.REGIME_2: cf.REGIME_2,
}

TRANSITION_WEIGHTS = {
    Regime.REGIME_1: {"solar": cf.TRANSITION_MATRIX["p11_solar"], "wind": cf.TRANSITION_MATRIX["p11_wind"]},
    Regime.REGIME_2: {"solar": cf.TRANSITION_MATRIX["p21_solar"], "wind": cf.TRANSITION_MATRIX["p21_wind"]},
}

HISTORIC_ELECTRICITY_PRICE = cf.HISTORIC_ELECTRICITY_PRICE # €/MWh
ITERATIONS = cf.ITERATIONS
DURATION = cf.DURATION  # hours
SHIFT = cf.SHIFT  # hours
SEED = cf.SEED


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def sample(values: list[T], weights: list[float] | None = None) -> T:
    if not weights:
        return random.choice(values)
    return random.choices(values, weights=weights, k=1)[0]


def logit(regime: Regime, share_solar: float, share_wind: float) -> float:
    return 1 / (
        1
        + np.exp(
            -TRANSITION_WEIGHTS[regime]["solar"] * share_solar
            - TRANSITION_WEIGHTS[regime]["wind"] * share_wind
        )
    )


def run_iteration(rload: np.ndarray, share_solar: np.ndarray, share_wind: np.ndarray) -> list[dict]:
    regime = sample(list(Regime))
    rows = []

    for timestep in range(DURATION):
        p11 = logit(Regime.REGIME_1, share_solar[timestep], share_wind[timestep])
        p21 = logit(Regime.REGIME_2, share_solar[timestep], share_wind[timestep])
        p12 = 1 - p11
        p22 = 1 - p21

        price_log = (
            PARAMETERS[regime]["c"]
            + PARAMETERS[regime]["rload"] * rload[timestep]
            + PARAMETERS[regime]["share_solar"] * share_solar[timestep]
            + PARAMETERS[regime]["share_wind"] * share_wind[timestep]
        )

        price_t = np.sinh(price_log) + HISTORIC_ELECTRICITY_PRICE

        rows.append(
            {"timestep": timestep + SHIFT, "regime": regime.value, "price": price_t}
        )

        regime = sample(
            list(Regime),
            weights=[
                p11 if regime == Regime.REGIME_1 else p21,
                p12 if regime == Regime.REGIME_1 else p22,
            ],
        )

    return rows

