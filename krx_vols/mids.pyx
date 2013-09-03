import pandas as pd
import numpy as np
cimport numpy as np

def krx_tick_width(some_symbol,bid_price):
    if (some_symbol[2:4]=='43' or some_symbol[2:4]=='42') and bid_price<300:
        return 1
    return 5

cdef inline double wmid(double bidp, double bids, double askp, double asks,double tick_width):
    if (bids+asks)<=0:
        return np.NaN
    if (askp - bidp) > (tick_width * 3):
        return np.NaN
    if (askp - bidp) > tick_width:
        return (bidp+askp)/2.
    else:
        return (bidp*asks+askp*bids)*1.0/(bids+asks)

def quick_mids(todays_date,some_md,bucketsize=1):
    
    all_symbols = some_md.symbol.value_counts().index.values
    num_syms = len(all_symbols)
    enum_dict = dict(zip(all_symbols,np.arange(num_syms)))
    
    
    cdef:
        long today_9am = todays_date.value+9*60*60*long(1e9) #korean market open (throw out stuff before then)
        long today_305pm = todays_date.value+15*60*60*long(1e9)+5*60*long(1e9) #korean market close (throw out stuff after then)
        long timestamp,nanos_past,bid,bidsize,ask,asksize
        long bucket_size = long(bucketsize*1e9) #convert bucketsize paramter to nanoseconds
        long num_buckets = (today_305pm-today_9am) / bucket_size
        int bucket = -1,prev_bucket=-1, tw, col, remainder
        np.ndarray[np.double_t, ndim=2] wmids = np.zeros([num_buckets,num_syms], dtype=np.double)#holder for all wmids info
        np.ndarray[np.int64_t,ndim=1] last_time = np.zeros(num_syms,dtype=np.int64) #array (ref'd by dict) of last timestamps
        np.ndarray[np.double_t,ndim=1] last_prices = np.zeros(num_syms,dtype=np.double) #array (ref'd by dict) of last wmid info

    for tup in some_md.itertuples():
        timestamp,symbol,bid,bidsize,ask,asksize = tup[:6]
        if today_9am <= timestamp <= today_305pm:
            bucket = ((long)(timestamp - today_9am)) / bucket_size
            col = enum_dict[symbol]
            prev_bucket = ((long)(last_time[col] - today_9am)) / bucket_size
            tw = krx_tick_width(symbol,bid)
            if bucket>=0:
                nanos_past = ((long)(timestamp - today_9am)) % bucket_size #how many nanoseconds into this bucket are we?
                if prev_bucket<0: #this is the first time bucket of the day! (or first observation)
                    wmids[bucket,col] +=  nanos_past * wmid(bid,bidsize,ask,asksize,tw)
                else: #regular bucket
                    if (bucket!=prev_bucket): 
                        remainder = bucket_size  - ((long)(last_time[col] - today_9am) % bucket_size)
                        wmids[prev_bucket,col] += remainder * last_prices[col]
                        wmids[prev_bucket,col] /= 1.0*bucket_size
                        prev_bucket+=1
                        while(prev_bucket<bucket):
                            wmids[prev_bucket,col] = last_prices[col]
                            prev_bucket+=1
                        wmids[bucket,col] += nanos_past * last_prices[col]
                    else:
                        wmids[bucket,col] += (timestamp - last_time[col]) * last_prices[col]
            last_time[col] = timestamp  
            last_prices[col] = wmid(bid,bidsize,ask,asksize,tw)
    #the above is close to what we want...
    #the last bucket needs to be fixed and filled down
    for i in range(0,num_syms):
        prev_bucket = ((long)(last_time[i] - today_9am)) / bucket_size;
        if prev_bucket >=0 : #THIS ENSURES THE SYMBOL TRADED -- YES THIS MATTERS
            remainder = bucket_size  - (((long)(last_time[i] - today_9am)) % bucket_size)
            wmids[prev_bucket,i] += remainder * last_prices[i]
            wmids[prev_bucket,i] /= bucket_size
            #and then 'fill' down
            prev_bucket+=1
            while(prev_bucket<num_buckets):
                wmids[prev_bucket,i] = last_prices[i]
                prev_bucket+=1
    return pd.DataFrame(wmids,index=pd.to_datetime(range(today_9am,today_305pm,bucket_size)),columns=sorted(enum_dict,key=enum_dict.get)).replace(0,np.NaN)