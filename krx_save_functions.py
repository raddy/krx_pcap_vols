import pandas as pd
import numpy as np
from kospi_basis import kospi_strikes_from_symbols

def save_mids(h5_pointer,some_mids):
    h5_pointer.put('twmids',some_mids)
def save_vol_tables(h5_pointer,expiry_code,vol_results_dict,money_results_dict):
    is_call = pd.Series(vol_results_dict[expiry_code].columns.values).str[2:4]=='42' 
    call_options = vol_results_dict[expiry_code].ix[:,is_call.values].sort_index(axis=1)
    call_options.columns = kospi_strikes_from_symbols(call_options.columns)
    call_moneys = money_results_dict[expiry_code].ix[:,is_call.values].sort_index(axis=1)
    call_moneys.columns = call_options.columns
    if not call_options.empty: #don't store empty tables (it's confusing for later analysis, no?
        h5_pointer.put(expiry_code+'/vols',call_options)
        h5_pointer.put(expiry_code+'/moneys',call_moneys)
def save_dtes(h5_pointer,some_dte_dict):
    h5_pointer.put('dtes',pd.DataFrame(some_dte_dict.values(),index=some_dte_dict.keys()))