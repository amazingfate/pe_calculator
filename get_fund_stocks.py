#!/usr/bin/python3.6
import requests
import json
import numpy as np
import pandas as pd
import bisect
from jqdatasdk import *
import time
import os

user_name = os.environ['JQDATA_USERNAME']
passwd = os.environ['JQDATA_PASSWD']
auth(user_name,passwd)
all_stocks = get_all_securities()
headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"}
url_list = ["https://danjuanapp.com/djapi/fund/detail/501029","https://danjuanapp.com/djapi/fund/detail/001550","https://danjuanapp.com/djapi/fund/detail/163402"]

def get_danjuan_data(url):
    danjuan_result = requests.get(url, headers = headers).json()
    code_list = []
    for stock in danjuan_result["data"]["fund_position"]["stock_list"]:
        stock_data = {}
        if stock["xq_symbol"][0:2] == "SH":
            stock_code = stock["code"] + ".XSHG"
        if stock["xq_symbol"][0:2] == "SZ":
            stock_code = stock["code"] + ".XSHE"
        stock_data["code"] = stock_code
        stock_data["weight"] = stock["percent"]
        stock_data["current_price"] = stock["current_price"]
        code_list.append(stock_data)
    return code_list

def get_stock_pe(stock_code, date):
    q = query(valuation).filter(valuation.code == stock_code)
    df = get_fundamentals(q, date)
    if len(df) > 0:
        price = df['circulating_market_cap'][0] * 10000 / df['circulating_cap'][0]
        round_price = round(price,2)
        return df['pe_ratio'][0],df['day'][0],round_price
    else:
        return float('NaN'),'NaN',float('NaN')

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

def cal_pe(stock_list):
    df_pe = pd.DataFrame()
    for stock in stock_list:
        df_pe[stock["code"]] = get_history_pe(stock["code"])

    today = pd.datetime.today()
    results = []
    for stock in stock_list:
        print("get pe of index %s on %s" % (stock["code"], today))
        weight = stock["weight"]
        pe,date,current_price = get_stock_pe(stock["code"], today)
        q_pes = [df_pe.quantile(i/10.0)[stock["code"]]  for i in range(11)]
        idx = bisect.bisect(q_pes,pe)
        if idx == 11:
            quantile = idx-1-(q_pes[idx-1]-pe)/(q_pes[idx-1]-q_pes[idx-2])
        elif idx == 0:
            quantile = idx-(q_pes[idx]-pe)/(q_pes[idx+1]-q_pes[idx])
        else:
            quantile = idx-(q_pes[idx]-pe)/(q_pes[idx]-q_pes[idx-1])
        stock_name = all_stocks.loc[stock["code"]].display_name
        results.append([stock_name,weight,current_price,'%.2f'% pe,'%.2f'% (quantile*10)]+['%.2f'%q  for q in q_pes]+[df_pe[stock["code"]].count(),date])
    df_pe.columns=np.array(results)[:,0]
    return results

today= pd.datetime.today()
for idx,stock_url in enumerate(url_list):
    code_list = get_danjuan_data(stock_url)
    results = []
    for stock in code_list:
        stock_list = []
        stock_list.append(stock)
        result = cal_pe(stock_list)
        results.append(result[0])
    columns=[u'名称',u'仓位',u'当前股价',u'当前PE',u'分位点%',u'最小PE']+['%d%%'% (i*10) for i in range(1,10)]+[u'最大PE' , u"数据个数" , u"数据更新时间"]
    result_df = pd.DataFrame(data=results,columns=columns)
    csv_file_name = "filtered_pe%s.csv" % idx
    result_df.to_csv(csv_file_name,index=0)
