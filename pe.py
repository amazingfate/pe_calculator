#!/usr/bin/python3
import numpy as np
import pandas as pd
import bisect
from jqdatasdk import *
import time
import os

user_name = os.environ['JQDATA_USERNAME']
passwd = os.environ['JQDATA_PASSWD']
auth(user_name,passwd)

#总市值的和除以总盈利的和
def get_index_stock_pe_date_new(index_code, date):
    stocks = get_index_stocks(index_code, date)
    q = query(valuation).filter(valuation.code.in_(stocks))
    df = get_fundamentals(q, date)
    sum_p = 0
    sum_e = 0
    for i in range(0, len(df)):
        sum_p = sum_p + df['market_cap'][i]
        sum_e = sum_e +  df['market_cap'][i] / df['pe_ratio'][i]

    if sum_e > 0:
        pe = sum_p / sum_e
    else:
        pe = float('NaN')
    return pe

#股价加权和除以每股盈利的加权和
def get_index_stock_pe_date_weights(index_code, date):
    stock_pe_result = []
    stocks_weight = get_index_weights(index_code, date)
    stocks_weight.reset_index(inplace=True)
    q = query(valuation).filter(valuation.code.in_(stocks_weight['code'].tolist()))
    df = get_fundamentals(q, date)
    for data in stocks_weight['code'].tolist():
        weight = float(stocks_weight[stocks_weight['code'] == data].weight)
        display_name = stocks_weight[stocks_weight['code'] == data]['display_name'].values[0]
        date = stocks_weight[stocks_weight['code'] == data]['date'].values[0]
        if not (df[df['code'] == data].pe_ratio.empty):
            pe_ratio = float(df[df['code'] == data].pe_ratio)
            price = df[df['code'] == data].market_cap.values[0] / df[df['code'] == data].capitalization.values[0] * 10000
        else:
            print("code %s on date %s ratio is null" % (data, date))
            pe_ratio = 0
            price = 0
        stock_data = {
            "code" : data,
            "display_name" : display_name,
            "weight" : weight,
            "pe_ratio" : pe_ratio,
            "price" : price,
            "weight": weight,
            "date" : date
        }
        stock_pe_result.append(stock_data)
    p_sum = 0
    e_sum = 0
    for data in stock_pe_result:
        if not data['pe_ratio'] == 0:
            p_sum += data['price'] * data['weight']
            e_sum += data['price'] / data['pe_ratio'] * data['weight']
        else:
            print("stock %s pe is %s on date %s" % (data['code'], data['pe_ratio'], date))
    if len(df)>0:
        pe_sum_final = p_sum / e_sum
        pe = pe_sum_final
        return pe
    else:
        return float('NaN')

def get_index_pe_date(index_code,date):
    stocks = get_index_stocks(index_code, date)
    q = query(valuation).filter(valuation.code.in_(stocks))
    df = get_fundamentals(q, date)
    if len(df)>0:
        pe = len(df)/sum([1/p if p>0 else 0 for p in df.pe_ratio])
        return pe
    else:
        return float('NaN')
    
def calculate_index_pe(index_code,d,pes,dates,end):
    if d > end:
        print("day %s is in the future" % d)
    else:
        dates.append(d)
        pes.append(get_index_stock_pe_date_new(index_code,d))

def get_index_pe(index_code):
    start='2005-1-1'
    end = pd.datetime.today()
    dates=[]
    pes=[]
    for d in pd.date_range(start=end,periods = 120,freq='-2W-FRI'):
        if d > end:
            print("day %s is in the future" % d)
        else:
            dates.append(d)
            if index_code in ['000852.XSHG','399812.XSHE','399967.XSHE']:
                pes.append(get_index_pe_date(index_code,d))
            else:
                pes.append(get_index_stock_pe_date_new(index_code,d))
    return pd.Series(pes, index=dates)

all_index = get_all_securities(['index'])

index_choose =['000016.XSHG',
               '000300.XSHG',
               '000804.XSHG',
               '000978.XSHG',
               '000922.XSHG',
               '399006.XSHE',
               '000852.XSHG',
               '000989.XSHG',
               '000991.XSHG',
               '000993.XSHG',
               '000827.XSHG',
               '399812.XSHE',
               '399967.XSHE',
               '399971.XSHE'
              ]

#index_choose = ['000016.XSHG','000300.XSHG','000991.XSHG']

def cal_pe(index_choose):
    df_pe = pd.DataFrame()
    for code in index_choose:
        df_pe[code]=get_index_pe(code)

    today= pd.datetime.today()
    results=[]
    for code in index_choose:
        print("get pe of index %s on %s" % (code, today))
        pe = get_index_stock_pe_date_new(code,today)
        q_pes = [df_pe.quantile(i/10.0)[code]  for i in range(11)]
        idx = bisect.bisect(q_pes,pe)
        quantile = idx-(q_pes[idx]-pe)/(q_pes[idx]-q_pes[idx-1])
        index_name = all_index.ix[code].display_name
        results.append([index_name,'%.2f'% pe,'%.2f'% (quantile*10)]+['%.2f'%q  for q in q_pes]+[df_pe[code].count(),today])

    df_pe.columns=np.array(results)[:,0]
    df_pe.plot(figsize=(12,10))
    columns=[u'名称',u'当前PE',u'分位点%',u'最小PE']+['%d%%'% (i*10) for i in range(1,10)]+[u'最大PE' , u"数据个数" , u"数据更新时间"]
    return results

results = []
for index in index_choose:
    index_list = []
    index_list.append(index)
    result = cal_pe(index_list)
    results.append(result[0])

columns=[u'名称',u'当前PE',u'分位点%',u'最小PE']+['%d%%'% (i*10) for i in range(1,10)]+[u'最大PE' , u"数据个数" ,  u"数据更新时间"]
df = pd.DataFrame(data=results,columns=columns)
df.to_csv('pe.csv',index=0)
