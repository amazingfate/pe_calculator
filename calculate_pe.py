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

#股价加权和除以每股盈利的加权和
def get_index_stock_pe_date_weights(index_code, date):
    stock_pe_result = []
    stocks_weight = get_index_weights(index_code, date)
    stocks_weight.reset_index(inplace=True)
    if not len(stocks_weight) == 0:
        q = query(valuation).filter(valuation.code.in_(stocks_weight['code'].tolist()))
        df = get_fundamentals(q, date)
        for data in stocks_weight['code'].tolist():
            weight = float(stocks_weight[stocks_weight['code'] == data].weight)
            display_name = stocks_weight[stocks_weight['code'] == data]['display_name'].values[0]
            date = stocks_weight[stocks_weight['code'] == data]['date'].values[0]
            if not df[df['code'] == data].market_cap.empty:
                market_cap = df[df['code'] == data].market_cap.values[0] * 10000
            else:
                market_cap = 0
                print("code %s on date %s market_cap is null" % (data, date))
            if not df[df['code'] == data].market_cap.empty:
                capitalization = df[df['code'] == data].capitalization.values[0]
            else:
                capitalization = 0
                print("code %s on date %s capitalization is null" % (data, date))
            if not capitalization == 0:
                price = market_cap / capitalization
            else:
                price = 0
            if not (df[df['code'] == data].pe_ratio.empty):
                pe_ratio = float(df[df['code'] == data].pe_ratio)
            else:
                print("code %s on date %s ratio is null" % (data, date))
                pe_ratio = 0
            stock_data = {
                "code" : data,
                "display_name" : display_name,
                "weight" : weight,
                "pe_ratio" : pe_ratio,
                "market_cap" : market_cap,
                "capitalization" : capitalization,
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
        if not e_sum == 0:
            pe_sum_final = p_sum / e_sum
            pe_weight = pe_sum_final
        else:
            pe_weight = float('NaN')

        sum_p = 0
        sum_e = 0
        for data in stock_pe_result:
            if not data['pe_ratio'] == 0:
                sum_p = sum_p + data['market_cap']
                sum_e = sum_e +  data['market_cap'] / data['pe_ratio']

        if sum_e > 0:
            pe = sum_p / sum_e
        else:
            pe = float('NaN')
        return pe, pe_weight
    else:
        return float('NaN'), float('NaN')


def get_index_pe(index_code):
    end = pd.datetime.today()
    dates=[]
    pes1=[]
    pes2=[]
    for d in pd.date_range(start=end,periods = 120,freq='-2W-FRI'):
        if d > end:
            print("day %s is in the future" % d)
        else:
            dates.append(d)
            pe = get_index_stock_pe_date_weights(index_code,d)
            pe1 = pe[0]
            pe2 = pe[1]
            pes1.append(pe1)
            pes2.append(pe2)
    return pd.Series(pes1, index=dates), pd.Series(pes2, index=dates)

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

#index_choose = ['000852.XSHG']

def cal_pe(index_choose):
    df_pe1 = pd.DataFrame()
    df_pe2 = pd.DataFrame()
    for code in index_choose:
        df_pe = get_index_pe(code)
        df_pe1[code] = df_pe[0]
        df_pe2[code] = df_pe[1]

    today= pd.datetime.today()
    results1=[]
    results2=[]
    for code in index_choose:
        print("get pe of index %s on %s" % (code, today))
        pe = get_index_stock_pe_date_weights(code,today)
        pe1 = pe[0]
        pe2 = pe[1]
        q_pes1 = [df_pe1.quantile(i/10.0)[code]  for i in range(11)]
        q_pes2 = [df_pe2.quantile(i/10.0)[code]  for i in range(11)]
        idx1 = bisect.bisect(q_pes1,pe1)
        idx2 = bisect.bisect(q_pes2,pe2)
        quantile1 = idx1-(q_pes1[idx1]-pe1)/(q_pes1[idx1]-q_pes1[idx1-1])
        quantile2 = idx2-(q_pes2[idx2]-pe2)/(q_pes2[idx2]-q_pes2[idx2-1])
        index_name = all_index.ix[code].display_name
        results1.append([index_name,'%.2f'% pe1,'%.2f'% (quantile1*10)]+['%.2f'%q  for q in q_pes1]+[df_pe1[code].count(),today])
        results2.append([index_name,'%.2f'% pe2,'%.2f'% (quantile2*10)]+['%.2f'%q  for q in q_pes2]+[df_pe2[code].count(),today])

    return results1, results2

results1 = []
results2 = []
for index in index_choose:
    index_list = []
    index_list.append(index)
    result = cal_pe(index_list)
    result1 = result[0]
    result2 = result[1]
    results1.append(result1[0])
    results2.append(result2[0])

columns=[u'名称',u'当前PE',u'分位点%',u'最小PE']+['%d%%'% (i*10) for i in range(1,10)]+[u'最大PE' , u"数据个数" ,  u"数据更新时间"]
df = pd.DataFrame(data=results1,columns=columns)
df.to_csv('pe1.csv',index=0)

df = pd.DataFrame(data=results2,columns=columns)
df.to_csv('pe2.csv',index=0)
