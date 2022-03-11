from data_handle import *
from stop_loss import *
from GFTDV2 import *


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