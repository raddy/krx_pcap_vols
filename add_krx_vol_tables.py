import sys,os
import pandas as pd
import numpy as np
from kospi_basis import nearby_calls_mask,nearby_puts_mask,kospi_strikes_from_symbols,option_symbols,synthetic_offset
from underlying_info import underlying_code,underlying_code_by_two_digit_code,underlyings
from krx_dtes import dte
from random_util import options_expiry_mask,altmoneys
from krx_save_functions import save_mids,save_vol_tables,save_dtes
from mids import mids
from krx_vols import krx_vols
import kf_linear



def result_dicts(some_mids,some_quotes,expiration_dict,trade_date,expiries):
    vol_results = dict()
    money_results = dict()
    dte_info = dict() #could be appended to expiry info but...

    #loop through all your expiries
    # -- append basis to your weighted mids table (we'll store this later)
    # -- store vols/moneyness info into dicts temporarily
    for exp in expiries:
        und_expiry_code = underlying_code_by_two_digit_code(exp)
        und_sym = underlying_code(und_expiry_code,underlyings(some_quotes)).values[0]
        exp_dte = dte(exp,trade_date,expiration_dict)
        print 'Expiry : ', exp, ' :: Corresponding Underlying: ',und_sym ,' :: DTE: ', exp_dte
        basis_code = exp+'-'+und_expiry_code+'-'+str(exp_dte)
        if und_expiry_code == exp: #quarterly
            spot_filtered = pd.Series(some_mids[und_sym].values,index=some_mids.index)
        else:
            spot = synthetic_offset(exp,und_sym,some_mids)
            if len(spot.valid()) == 0: #we were never able to calculate a synthetic basis and thus can't calc underlying
                continue
            spot_filtered = pd.Series(kf_linear.univariate_filter(spot,spot[spot.first_valid_index()],1,500).values+some_mids[und_sym].values,index=spot.index)
            some_mids[basis_code] = spot_filtered
        vol_results[exp] = krx_vols.imp_vols_cython(some_mids.ix[:,options_expiry_mask(some_mids.columns,exp).values],spot_filtered,exp_dte)
        money_results[exp] = pd.DataFrame(altmoneys(spot_filtered.fillna(method='ffill').fillna(method='bfill').values,
                    kospi_strikes_from_symbols(vol_results[exp].columns.values).values,exp_dte/261.0),
                    index = some_mids.index, columns = vol_results[exp].columns)
        dte_info[exp] = exp_dte
    return [vol_results,money_results,dte_info]

def add_vols(file_name):
    store = pd.HDFStore(file_name)
    pcap_info = store['pcap_data']
    quotes_only = pcap_info[np.logical_or(pcap_info.msg_type=='B6',pcap_info.msg_type=='G7')]
    del pcap_info
    
    todays_trade_date = pd.Timestamp(file_name.split('/')[-1].split('.pcap')[0].split('.')[-1][:8])
    
    if '/expiry_info' in store.keys():
        expiration_dict = store['expiry_info'].to_dict()[0]
        s = pd.Series(expiration_dict.values(),index=expiration_dict.keys())
        expiration_dict = s[s>=todays_trade_date.strftime('%Y%m%d')].to_dict()
    else: # we should read from config file...for now exit and warn
        store.close()
        sys.exit('CONFIG FILE NOT YET SUPPORTED')
    expiries = quotes_only.symbol.str[6:8].value_counts().index.values

    #time weighted mids via cython
    twmids = mids.quick_mids(todays_trade_date,quotes_only)
    #should be refactored into saving while building..but whatever
    vols,moneys,dtes = result_dicts(twmids,quotes_only,expiration_dict,todays_trade_date,expiries)
    
    #We are abusing python scoping to modify that twmids frame INSIDE the result_dicts()
    #-- This is a bad idea and should be changed to at least be more epxlicit
    
    save_dtes(store,dtes)
    save_mids(store,twmids)
    for exp in expiries:
        if vols.has_key(exp) and moneys.has_key(exp):
            save_vol_tables(store,exp,vols,moneys)
    print 'Finished saving vol tables to %s' %file_name
    print store
    store.close()


def main(file_name):
    print 'Appending vol table info to %s ....' %file_name
    add_vols(file_name)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('Usage: %s h5-path' % sys.argv[0])

    if not os.path.exists(sys.argv[1]):
        sys.exit('ERROR: Raw h5 file %s was not found!' % sys.argv[1])
    sys.exit(main(sys.argv[1]))