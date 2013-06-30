import pandas as pd
import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport exp, sqrt, pow, log, erf, abs, M_PI

cdef extern from "black.h" nogil:
    double std_norm_cdf( double x)
    double delta(double s,double k,double t, double v,double rf,double cp)
    double vega(double s,double k,double t, double v,double rf,double cp)
    double tv(double s,double k,double t, double v,double rf,double cp)

#takes a LIST/ARRAY of KRX Kospi symbols -- returns a list of float strikes
def kospi_strikes_from_symbols(symbol_list):
    strikes = pd.Series(symbol_list).str[8:11].astype(float)
    strikes[strikes%5 != 0 ] += .5
    return strikes * 100

@cython.cdivision(True)
@cython.boundscheck(False)
def implied_vol(double underlying, double price, double strike, double t, double rf, double cp):
    cdef long i = 0
    cdef double prices_guess, vol_guess = 1
    cdef double diff, delt
    
    for i in range(0,20):
        price_guess = tv(underlying,strike,t,vol_guess,rf,cp)
        diff = price - price_guess
        if abs(diff) < .001:
            return vol_guess
        vegalol = vega(underlying,strike,t,vol_guess,rf,cp)
        if vegalol<.01:
            return -1
        vol_guess += diff / vegalol
    return -1

#expects mids_df contents with underlying series and corresponding dte
# -- assumes mids_df contains ONLY option symbols
def imp_vols_cython(mids_df,underlying_series,some_dte,ir=.03,days_per_year=261.0):
    cdef:
        int i=0,j=0,mids_len = mids_df.shape[0],num_syms=mids_df.shape[1]
        double spot
        np.ndarray[np.double_t, ndim=2] vols = np.zeros([mids_len,num_syms], dtype=np.double) * np.NaN
    
    unds = underlying_series.values
    strikes = kospi_strikes_from_symbols(mids_df.columns.values)
    mids_values = mids_df.values
    
    option_types = np.repeat(1,num_syms) #assume they're all calls for a second
    is_put = pd.Series(mids_df.columns.values).str[2:4]=='43'
    option_types[is_put] = -1
    

    tte = some_dte/days_per_year
    
    while i<mids_len:
        spot = unds[i]
        if spot>0 and spot!=np.NaN:
            for j in range(0,num_syms):
                if mids_values[i,j] < 1: #the option is worth less than a tick!
                    vols[i,j] = -1
                else:
                    if (option_types[j]== -1 and strikes[j]>spot) or (option_types[j]==1 and strikes[j]<spot):
                        vols[i,j] = -1
                    else:
                        vols[i,j] = implied_vol(spot, mids_values[i,j], strikes[j], tte, ir, option_types[j])
            for j in range(0,num_syms):
                if vols[i,j]!= np.NaN and vols[i,j] < 0 : #this is placeholder
                    for k in range(0,num_syms):
                        if j!=k and strikes[j]==strikes[k]:
                            vols[i,j] = vols[i,k]
        i+=1
    return pd.DataFrame(vols,index=mids_df.index,columns=mids_df.columns).replace(-1,np.NaN)