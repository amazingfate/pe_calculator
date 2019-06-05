#!/usr/bin/python3.6
import numpy as np
import pandas as pd
import bisect
from jqdatasdk import *
import time
import os

user_name = os.environ['JQDATA_USERNAME']
passwd = os.environ['JQDATA_PASSWD']
auth(user_name,passwd)

index_code = '000300.XSHG'

def get_stock_pe(stock_code, date):
    q = query(valuation).filter(valuation.code == stock_code)
    df = get_fundamentals(q, date)
    if len(df) > 0:
        return df['pe_ratio'][0],df['day'][0]
    else:
        return float('NaN'),'NaN'

def get_history_pe(stock_code):
    end = pd.datetime.today()
    dates = []
    pes = []
    for d in pd.date_range(start=end,periods = 120,freq='-2W-FRI'):
        if d > end:
            print("day %s is in the future" % d)
        else:
            dates.append(d)
            pes.append(get_stock_pe(stock_code, d)[0])
    return pd.Series(pes, index=dates)
all_index = get_all_securities(['stock'])
def cal_pe(stock_list):
    df_pe = pd.DataFrame()
    for stock in stock_list:
        df_pe[stock] = get_history_pe(stock)

    today = pd.datetime.today()
    results = []
    for stock in stock_list:
        print("get pe of index %s on %s" % (stock, today))
        pe,date = get_stock_pe(stock, today)
        q_pes = [df_pe.quantile(i/10.0)[stock]  for i in range(11)]
        idx = bisect.bisect(q_pes,pe)
        if idx == 11:
            quantile = idx-1-(q_pes[idx-1]-pe)/(q_pes[idx-1]-q_pes[idx-2])
        elif idx == 0:
            quantile = idx-(q_pes[idx]-pe)/(q_pes[idx+1]-q_pes[idx])
        else:
            quantile = idx-(q_pes[idx]-pe)/(q_pes[idx]-q_pes[idx-1])
        stock_name = all_index.loc[stock].display_name
        results.append([stock_name,'%.2f'% pe,'%.2f'% (quantile*10)]+['%.2f'%q  for q in q_pes]+[df_pe[stock].count(),date])
    df_pe.columns=np.array(results)[:,0]
    columns=[u'名称',u'当前PE',u'分位点%',u'最小PE']+['%d%%'% (i*10) for i in range(1,10)]+[u'最大PE' , u"数据个数" , u"数据更新时间"]
    return results
today= pd.datetime.today()
stocks = get_index_stocks(index_code,today)
results = []
for stock in stocks:
    stock_list = []
    stock_list.append(stock)
    result = cal_pe(stock_list)
    results.append(result[0])

columns=[u'名称',u'当前PE',u'分位点%',u'最小PE']+['%d%%'% (i*10) for i in range(1,10)]+[u'最大PE' , u"数据个数" ,  u"数据更新时间"]
filter_data = []
for data in results:
    if float(data[3]) > 0 and float(data[2]) < 10:
        filter_data.append(data)
result_df = pd.DataFrame(data=filter_data,columns=columns)
result_df.to_csv('filtered_pe.csv',index=0)
