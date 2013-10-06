import pandas as pd
import numpy as np
from cy_utility import univariate_kf
import cubic_regression_spline as crs

def kf_vols(raw):
    simple_kf = raw.copy()
    for c in simple_kf.columns:
      seed = simple_kf[c][simple_kf[c].first_valid_index()]
      simple_kf[c] = univariate_kf(simple_kf[c].values,seed,seed/1000.,seed/10.)
    return simple_kf

def splined_kf_residualized(raw,simple_kf_vols,moneys):
    splined_kf_vols = crs.crs_vols(simple_kf_vols,moneys,deltas=np.array([]))

    splined_kf_adjusted = splined_kf_vols.copy()
    for c in splined_kf_vols.columns:
        residuals = (raw[c] - splined_kf_vols[c])
        filtered_residuals = univariate_kf(residuals.values,0,1,10000)
        splined_kf_adjusted[c] += filtered_residuals
    return splined_kf_adjusted