'''
复现研报《A股量化择时模型GFTD第二版》中的因子

绘制买卖信号
'''
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from data_handle import *
from stop_loss import *



# 获取 价格关系比较结果 ud_i
def get_ud(data, n1):
    # 求变化量 Δx = x(t) - x(t-1)
    data['close-n1'] = data['close'].shift(n1)
    data['ud'] = data.apply(lambda x:1 if x['close']-x['close-n1']>0 else(-1 
                                if x['close']-x['close-n1']<0 else 0),axis=1 )
    #print('!'*80)
    #print(data[['date_time','close','close-n1','ud']])
    data.drop(['close-n1'], axis=1,inplace=True)
    print(data[['ud']])
    return data

# 判断 买入启动/卖出启动
def get_factor(data, n1, n2, n3):
    """计算因子

    Args:
        data (dateframe): 因子数据（字段['factor']）
        n1 (int): 因子制定参数之ud参数
        n2 (int): 因子制定参数之买卖启动参数
        n3 (int): 因子制定参数之买卖信号参数

    Returns:
        dateframe: 信号数据（字段['buy_n','buy_sum','sig']）
    """    
    # 1.计算 ud_i 
    data = get_ud(data, n1)
    # 2.对 ud_i 进行累加计算，且当其值与上一个值不等时，停止本次累加
    data['ud_last'] = data['ud'].shift(1)
    data['sum_ud'] = np.nan
    data['sum_ud'].iloc[0] = data['ud'].iloc[0]
    for i in range(data.shape[0]-2):
        if data['ud'].iloc[i+1] == data['ud_last'].iloc[i+1]:
            data['sum_ud'].iloc[i+1] = data['ud'].iloc[i+1] + data['sum_ud'].iloc[i]
        else:
            data['sum_ud'].iloc[i+1] = data['ud'].iloc[i+1]
    data['buy_start'] = data['sum_ud'].apply(lambda x:1 if x==n2 else(-1 if x==-n2 else np.nan))

    # 3.当 ud_i 的累加计算结果为 n2 时为一个卖出启动的形成，当计算结果为 −n2 时为一个买入启动的形成。
    buy_start_idx = list(data[data['sum_ud']==n2].index)
    sell_start_idx = list(data[data['sum_ud']==-n2].index)
    data['buy_count'] = np.nan
    data['sell_count'] = np.nan

    # 4.判断买入卖出信号:
    #于买入【卖出】启动形成的随后 1 根 K线位置开始买入【卖出】计数，在某一个 K线上同时满足如下三个条件时买入【卖出】计数累加 1:
        # A. 收盘价大于或等于之前第 2 根 K 线最高价【最低价】；
        # B. 最高价【最低价】大于之前第 1 根 K 线的最高价【最低价】；
        # C. 收盘价大于之前第 1 个《计数》的收盘价。
    #当计数累加至n3发出买入信号。当形成一组新的买入【卖出】启动时，取消上一组未最终形成买入【卖出】信号的买入【卖出】计数。
    
    # 买入，每次【买入启动】后是一个循环
    for i in range(len(buy_start_idx)-1):
        n = buy_start_idx[i]
        if i<len(buy_start_idx)-1:
            m = buy_start_idx[i+1]
        else:
            m = data.shape[0]
        buy_count_index = []
        if n < m:
            # 从 n+1个开始买入计数
            n += 1
            # 若此前还没有计数，则【C.】和前一个k线收盘价比
            if data['close'].iloc[n] >= data['high'].iloc[n-2] and \
                    data['high'].iloc[n] >= data['high'].iloc[n-1] and \
                    (len(buy_count_index)==0 or data['close'].iloc[n] >= data['close'].iloc[ buy_count_index[-1] ]):
                data['buy_count'].iloc[n] = 1
                buy_count_index.append(n)

    for i in range(len(sell_start_idx)):
        n = sell_start_idx[i]
        if i < len(sell_start_idx) - 1:
            m = sell_start_idx[i+1]
        else:
            m = data.shape[0]
        sell_count_index = []
        if n < m:
            # 从 n+1个开始买入计数
            n += 1
            if data['close'].iloc[n] >= data['low'].iloc[n-2] and \
                    data['low'].iloc[n] >= data['low'].iloc[n-1] and \
                    (len(sell_count_index) == 0 or data['close'].iloc[n] >= data['close'].iloc[ sell_count_index[-1] ]):
                data['sell_count'].iloc[n] = 1
                sell_count_index.append(n)
    # 买卖计数累加
    data['buy_sum'] = data['buy_count'].cumsum() % n3 #cumsum之后!=0，可不考虑0//n3的情况
    data['sell_sum'] = data['sell_count'].cumsum() % n3
    # 使得计数累加为 1，2，3，4的都属于一个buy_n
    data['buy_n'] = (data['buy_count'].cumsum() - 1) // n3
    data['sell_n'] = (data['sell_count'].cumsum() - 1) // n3
    print(data[['sum_ud', 'buy_n', 'sell_n']])
    return data


# 生成买卖信号数据: 买入=1，卖出=-1；考虑 止损机制
def get_trading_sig(data):
    """生成买卖信号数据

    Args:
        data (dateframe): 因子数据（字段['factor']）

    Returns:
        dateframe: 信号数据（字段['factor','sig']）
    """    
    # 买入、卖出计数形 成买卖信号
    data['sig'] = data.apply(lambda x:1 if (x['buy_sum']==0) else(
        -1 if (x['sell_sum']==0) else 0), axis=1)
    
    # 在买入卖出信号之间，若price达止损点，则止损点变为卖出点
    stop_data = get_stopprice(data)
    data = adjust_trading_sig_withStoploss(data, stop_data)
    return data

# 绘制买卖信号图
def draw_trade_sig(sig_data, time_freq, startdt=20120000, enddt=20220000):
    """绘制买卖信号图

    Args:
        sig_data (dataframe): 原始数据（字段['date_time','date','open','sig'])
        time_freq (int): 原始数据的时间频率
        startdt (int, optional): 时间区间的开始日期. Defaults to 20120000.
        enddt (int, optional): 时间区间的结束日期. Defaults to 20220000.
    """    
    data = sig_data[ (sig_data.date>=int(startdt)) & (sig_data.date<=int(enddt)) ]
    data.set_index(['date_time'], inplace=True)
    buy_idx = list(data[ data.sig==1 ].index)
    sell_idx = list(data[ data.sig==-1 ].index)
    plt.figure(figsize=(16, 8))
    plt.plot(data['open'],label="open price",color='k',linewidth=1)
    plt.plot(data['open'][buy_idx],'^',color='red',label="buy", markersize=8)
    plt.plot(data['open'][sell_idx],'gv',label="sell", markersize=8)
    plt.legend()
    plt.grid(True)
    plt.show()
    # plt.savefig(r"data\result_data\{}_min_trading_sig.png".format(time_freq))
    plt.close()

if __name__ == '__main__':    
    # 定义策略中需要用到的参数
    n1, n2, n3 = 4, 4, 4
    s = 0 

    # 获取 复权数据
    d = GetData()
    data = d.run()

    # 在不通的时间频率下 计算因子并获得交易信号
    time_freq_list = [1, 5, 15, 30, 60, 240]
    for time_freq in time_freq_list[2:3]:
        # 转换 时间频率
        data = transfer_timeFreq(data, time_freq, ic_multiplier=200)
        # 生成 指标
        data_factor = get_factor(data, n1, n2, n3) #.reset_index()
        ### 获取买卖信号
        data_factor = data_factor.reset_index()
        data_sig = get_trading_sig(data_factor)
        data_sig.rename(columns={'ud':'factor'},inplace=True)

        # 获取 买卖信号数据
        data_sig = get_trading_sig(data_factor)
        data_sig.to_csv(r'data\result_data\{}min_signal.csv'.format(time_freq))
        print(data_sig)
        draw_trade_sig(data_sig, time_freq)