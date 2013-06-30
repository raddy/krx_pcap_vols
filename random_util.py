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