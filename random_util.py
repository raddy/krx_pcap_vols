import pandas as pd
import numpy as np

def options_expiry_mask(symbol_list,expiry_code):
    is_call = pd.Series(symbol_list).str[2:4]=='42' 
    is_put = pd.Series(symbol_list).str[2:4]=='43'
    is_option = np.logical_or(is_call,is_put)
    is_expiry = pd.Series(symbol_list).str[6:8]==expiry_code
    return np.logical_and(is_option,is_expiry)

#calculates adjusted moneyness (explain later)
def altmoneys(underlying_array, strikes, tte):
    us = (np.log(np.outer(strikes,1/underlying_array))).transpose()
    us = us / np.sqrt(tte)
    us = (us*1000).astype(int) * 1.0 / 1000
    return us

def is_kospi(symbol_list):
    s = pd.Series(symbol_list)
    is_call = s.str[2:6]=='4201'
    is_put = s.str[2:6]=='4301'
    is_fut = s.str[2:6]=='4101'
    return np.logical_or(is_call,np.logical_or(is_put,is_fut))

def kospi_types_from_symbols(symbol_list):
    res = np.zeros(len(symbol_list))
    is_call = pd.Series(symbol_list).str[2:4]=='42'
    is_put = pd.Series(symbol_list).str[2:4]=='43'
    res[is_call] = 1
    res[is_put] = -1
    return res

def kospi_strikes_from_symbols(symbol_list):
    strikes = pd.Series(symbol_list).str[8:11].astype(float)
    strikes[strikes%5 != 0 ] += .5
    return (strikes * 100).values

def kospi_fresh(symbol_list,tte_list,age):
    s = pd.Series(symbol_list)
    is_call = s.str[2:6]=='4201'
    is_put = s.str[2:6]=='4301'
    is_fut = s.str[2:6]=='4101'
    is_option = np.logical_or(is_call,is_put)
    fresh_options = np.logical_and(is_option,tte_list<age)
    return np.logical_or(is_fut,fresh_options)