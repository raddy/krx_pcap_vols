import pandas as pd
import numpy as np

def krx_holidays():
    return []

def expiration(symbol,expiration_dict):
    return pd.Timestamp(expiration_dict[symbol])

def dte(symbol,trade_date,expiration_dict):
    drange = pd.date_range(start=pd.Timestamp(trade_date),end=expiration(symbol,expiration_dict))
    s = (pd.Series(pd.to_datetime(drange).tolist(),index=drange).asfreq(pd.tseries.offsets.BDay())).isin(krx_holidays())
    return len(s[s==False])