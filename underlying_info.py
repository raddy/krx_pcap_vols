import pandas as pd
import numpy as np

def underlying_code_by_two_digit_code(code):
    single_codes = ['1','2','3','4','5','6','7','8','9','A','B','C']
    return str(code[0])+dict(zip(single_codes,np.repeat(['3','6','9','C'],3).tolist()))[code[1]]
def underlyings(some_md):
    s = pd.Series(some_md.symbol.value_counts().index.values)
    return s[s.str[2:4]=='41']
def underlying_code(exp_code,u):
    return u[u.str[6:8]==exp_code]
def front_code(some_dict_of_expirys):
    return sorted(some_dict_of_expirys,key=some_dict_of_expirys.get)[0]