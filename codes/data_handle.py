import numpy as np
import pandas as pd
import datetime

# 转换数据 时间频率
def transfer_timeFreq(ori_data, time_freq, ic_multi=200):
    '''
    Parameters
        ori_data  [dataframe]    原始数据（字段[ ])
        time_freq [int]          时间频率（单位：分钟）
        ic_multi  [int]          ic乘数（分钟内均价 turnover/volume，需要除ic乘数）
    '''
    if time_freq==1:
        return get_newFreq_datetime(ori_data)
    ori_data.reset_index(inplace=True)
    ori_data['flag_data'] = ori_data.groupby(['wind_id','date']).index.rank()-1
    ori_data['flag'] = ori_data['flag_data'].apply(lambda x:x//time_freq)
    grouped = ori_data.groupby(['date','flag'])
    # groupby来调整数据频率
    get_lastday = grouped[['wind_id','time','open']].nth(0)
    max_high = grouped['high'].max()
    min_low = grouped['low'].min()
    last_close = grouped['close','io'].nth(-1)
    get_sum = grouped[['all_volume','all_turnover']].sum()
    # 数据合并
    data_list = [get_lastday,max_high,min_low,last_close,get_sum]
    temp = pd.concat(data_list,axis=1)
    data_newfreq = temp.reset_index()
    data_newfreq['preclose'] = data_newfreq['close'].shift(-1)
    data_newfreq['average_price'] = np.divide(data_newfreq['all_turnover'],
        data_newfreq['all_volume'])/ic_multi
    # 生成每条数据对应 日期时间
    data_newfreq = get_newFreq_datetime(data_newfreq)

    #### 若交易量为 0 （数据缺失或触发了熔断），删除数据
    nan_vloume_date = list(set(data_newfreq[data_newfreq['all_volume']==0].date))
    data_newfreq.drop( data_newfreq[data_newfreq.date.isin(nan_vloume_date)].index , inplace=True)
    # 重设连续index
    data_newfreq.index = (range(data_newfreq.shape[0]))
    return data_newfreq


# 获得转换时间频率后的 datetime数据（日期+时间型）
def get_newFreq_datetime(data_newfreq):
    try: 
        data_newfreq['date_time'] = data_newfreq.apply(lambda x:datetime.datetime.strptime\
            (str(int(x['date']))+' '+str(int(x['time']))[:-5],'%Y%m%d %H%M'), axis=1) 
    except KeyError: # 若报错，一般为缺乏 'time' 字段
        data_newfreq['date_time'] = data_newfreq.apply(lambda x:datetime.datetime.strptime\
            (str(int(x['date']))+' '+str(1500),'%Y%m%d %H%M'), axis=1) 
    
    return data_newfreq

# 给价格后复权，并保留未复权价格：后复权价 = 价格*后复权因子
def get_fuquan_data(data):
    '''
    Parameters
        data [dataframe]    数据(字段['factor'（复权因子）,'high','low','open','close'])
    '''
    col_list = ['high','low','open','close']
    for i in col_list:
        data['fq_'+ i] = np.multiply(data[i], data['factor'])
    data.drop(['factor'], axis=1, inplace=True) # 后面的因子也取名叫factor
    return data
