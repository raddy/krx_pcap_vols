import pandas as pd
import numpy as np
#nearby strike mask for put option symbols
def nearby_puts_mask(futures_price,strike_array,symbol_list,strike_width):
    nearby_strike = abs(strike_array-futures_price)<strike_width
    is_puts = pd.Series(symbol_list).str[2:4]=='43'
    return np.logical_and(nearby_strike,is_puts)

#nearby strike mask for call option symbols
def nearby_calls_mask(futures_price,strike_array,symbol_list,strike_width):
    nearby_strike = abs(strike_array-futures_price)<strike_width
    is_call = pd.Series(symbol_list).str[2:4]=='42'
    return np.logical_and(nearby_strike,is_call)

#takes a LIST/ARRAY of KRX Kospi symbols -- returns a list of float strikes
def kospi_strikes_from_symbols(symbol_list):
    strikes = pd.Series(symbol_list).str[8:11].astype(float)
    strikes[strikes%5 != 0 ] += .5
    return strikes * 100

#takes an expiry code (2 digit) plus a LIST/ARRAY of KRX Kospi symbols -- returns a pandas series
#  -- said panda series is a list of option issue codes that are both options and of matching expiry
def option_symbols(expiry_code,symbol_list):
    s = pd.Series(symbol_list)
    are_options = np.logical_or(s.str[2:4]=='43',s.str[2:4]=='42')
    matching_code = s.str[6:8]==expiry_code
    return s[np.logical_and(are_options,matching_code)]

#takes an expiry code, its corresponding underlying code, and a dataframe of calculated weighted mid prices
# -- calculates the cash-futures basis between an expiry code and its underlying
# -- it does this with the intention of piping to a simple 1-d kalman filter
# -- theres a fourth "hidden" parameter that dictates how many strikes to use
# -- this is by default 750 ticks, which is "3 strikes wide"
# -- this is incorrect because of the need to NPV the relative carry by synthetic
# -- that is a very small amount however
# -- this is pretty different than how its done in production but I think that it's more illustrative

def synthetic_offset(expiry_code,underlying_expiry_code,some_mids,strike_width=750):
    underlying_mids = some_mids[underlying_expiry_code].values #nparray
    one_mids =  some_mids.ix[:,option_symbols(expiry_code,some_mids.columns.values).values]
    strikes = kospi_strikes_from_symbols(one_mids.columns).values
    implied_synthetics = []
    i=0
    for row in one_mids.itertuples():
        call_mask = nearby_calls_mask(underlying_mids[i],strikes,one_mids.columns.values,strike_width)
        close_calls = pd.Series(row[1:])[call_mask]
        close_calls.index = strikes[call_mask]
        #close_calls.replace(0,np.NaN,inplace=True)
        put_mask = nearby_puts_mask(underlying_mids[i],strikes,one_mids.columns.values,strike_width)
        close_puts = pd.Series(row[1:])[put_mask]
        close_puts.index = strikes[put_mask]
        #close_puts.replace(0,np.NaN,inplace=True)
        res =  close_calls - close_puts
        res = (res + res.index.values).dropna()
        if len(res)<3:
            implied_synthetics.append(np.NaN)
        else:
            implied_synthetics.append(res.mean() - underlying_mids[i])
        i+=1
    return pd.Series(np.array(implied_synthetics),index=one_mids.index)