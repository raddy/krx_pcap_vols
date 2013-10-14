import pandas as pd
import numpy as np
from underlying_info import underlying_code,underlying_code_by_two_digit_code,underlyings
from kospi_basis import kospi_strikes_from_symbols
from random_util import options_expiry_mask,altmoneys,is_kospi,kospi_strikes_from_symbols,kospi_types_from_symbols,kospi_fresh
from cycross import cycross
from bsm_implieds import fast_implieds,implied_futs,deltas,net_effect_cython

def save_mids(h5_pointer,some_mids):
    h5_pointer.put('twmids',some_mids)

def generic_save(h5_pointer,some_stuff,expiry_code,suffix='/vols'):
    if not some_stuff.empty:
        h5_pointer.put(expiry_code+suffix,some_stuff)

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
def save_syns(h5_pointer,syn_df):
    h5_pointer.put('basis',syn_df)

def save_supplementary(h5_pointer,pcap_info,vols_type):
    s = pd.Series(h5_pointer.keys())
    vol_series_list = []
    basis_series_list = []
    fut_bid_series_list = []
    fut_ask_series_list = []
    print 'Pcap Info Length entering: ',len(pcap_info)
    for k in s[s.str.contains(vols_type)]:
        two_digit_code = k[1:3]
        my_und = underlying_code(underlying_code_by_two_digit_code(two_digit_code),underlyings(pcap_info)).values[0]
        just_that_data = pcap_info[options_expiry_mask(pcap_info.symbol,two_digit_code)]
        just_that_fut = pcap_info[pcap_info.symbol==my_und]
        strikes = np.array(kospi_strikes_from_symbols(just_that_data.symbol.values),dtype=object)
        just_those_vols = h5_pointer[k]
        basis = h5_pointer['basis'][two_digit_code]
        basis.index = basis.index.astype(np.int64)
        just_that_data['vols'] = cycross.cross(strikes,just_that_data.index.astype(long),just_those_vols.index.astype(long),just_those_vols.columns.values,just_those_vols.values)
        just_that_data['basis'] = basis.asof(just_that_data.index).fillna(method='ffill')
        just_that_data['fut_bid'] = just_that_fut.bid1.asof(just_that_data.index).fillna(method='ffill')
        just_that_data['fut_ask'] = just_that_fut.ask1.asof(just_that_data.index).fillna(method='ffill')
        vol_series_list.append(just_that_data['vols'])
        basis_series_list.append(just_that_data['basis'])
        fut_bid_series_list.append(just_that_data['fut_bid'])
        fut_ask_series_list.append(just_that_data['fut_ask'])
    pcap_info['vols'] = pd.concat(vol_series_list).reindex_like(pcap_info)
    pcap_info['basis'] = pd.concat(basis_series_list).reindex_like(pcap_info)
    pcap_info['fut_bid'] = pd.concat(fut_bid_series_list).reindex_like(pcap_info)
    pcap_info['fut_ask'] = pd.concat(fut_ask_series_list).reindex_like(pcap_info)
    h5_pointer.remove('supplementary')
    print 'Pcap Info Length exiting: ',len(pcap_info)
    h5_pointer.append('supplementary',pcap_info.ix[:,['vols','basis','fut_bid','fut_ask']])


def save_implieds(h5_pointer, start_time,end_time,MAX_AGE=50,RISK_FREE=.03,GUESS=260):
    s = pd.Series(h5_pointer['twmids'].columns)
    front_syms = s[s.str.contains('-')].str[0:2].append(s[s.str.contains('-')].str[3:5]).unique()

    dat = h5_pointer.select('pcap_data',[pd.Term('index','>=',start_time),pd.Term('index','<=',end_time)])
    supp = h5_pointer.select('supplementary',[pd.Term('index','>=',start_time),pd.Term('index','<=',end_time)])
    recombined_dat = (dat.join(supp,how='outer'))
    recombined_dat = recombined_dat[is_kospi(dat.symbol).values]
    expiries = recombined_dat.symbol.str[6:8]
    recombined_dat = recombined_dat[expiries.isin(h5_pointer['dtes'].index).values]
    recombined_dat['tte'] = recombined_dat.symbol.str[6:8].replace(h5_pointer['dtes'].to_dict()[0]).astype(float) / 260.
    recombined_dat['strike'] = kospi_strikes_from_symbols(recombined_dat.symbol.values)
    recombined_dat['type'] = kospi_types_from_symbols(recombined_dat.symbol.values)
    recombined_dat = recombined_dat[recombined_dat.symbol.str[6:8].isin(front_syms).values]
    recombined_dat = recombined_dat[kospi_fresh(recombined_dat.symbol,recombined_dat.tte.values,MAX_AGE/260.)]
    implieds_frame = fast_implieds(recombined_dat.symbol,recombined_dat.bid1.astype(np.float64),recombined_dat.bidsize1,recombined_dat.bid2.astype(np.float64),recombined_dat.bidsize2,
            recombined_dat.ask1.astype(np.float64),recombined_dat.asksize1,recombined_dat.ask2.astype(np.float64),recombined_dat.asksize2,
              (recombined_dat.basis+recombined_dat.fut_bid),recombined_dat.basis,recombined_dat.vols,recombined_dat.tte,recombined_dat.strike.astype(np.float64),
                recombined_dat.type.astype(long),RISK_FREE,GUESS)
    implieds_frame.index = recombined_dat.index
    
    implieds_frame['delta_effect'] = net_effect_cython(recombined_dat.symbol,recombined_dat.bid1.astype(np.float64),recombined_dat.tradeprice.astype(np.float64),recombined_dat.tradesize)
    implieds_frame['delta'] = deltas(recombined_dat.fut_bid.astype(np.float64),recombined_dat.strike.astype(np.float64),recombined_dat.vols,recombined_dat.tte,recombined_dat.type.astype(long),.03)
    implieds_frame['implied_trd'] = implied_futs(recombined_dat.tradeprice.astype(np.float64),recombined_dat.strike.astype(np.float64),recombined_dat.vols,recombined_dat.tte,recombined_dat.type.astype(long),.03,26410) - recombined_dat.basis
    implieds_frame['implied_trd'][(implieds_frame.delta.abs()<.15).values] = np.NaN
    implieds_frame['delta'][(implieds_frame.delta.abs()<.15).values] = np.NaN
    implieds_frame['delta_effect'] *= implieds_frame['delta']
    implieds_frame = implieds_frame.drop_duplicates()
    if '/implieds' in h5_pointer.keys():
        print 'Deleteing old implieds frame...'
        h5_pointer.remove('implieds')
    h5_pointer.append('implieds',implieds_frame)
    