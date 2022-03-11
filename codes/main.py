from data_handle import *
from stop_loss import *
from GFTDV2 import *

# 获取 复权数据
d = GetData()
data = d.run()

time_freq_list = [1, 5, 15, 30, 60, 240]

for time_freq in time_freq_list[:4]:
    print(time_freq)
    data = transfer_timeFreq(data, time_freq, ic_multi=200)  # get_newFreq_datetime()        

    # 生成 指标
    data_factor = get_factor(data, n1, n2, n3) #.reset_index()
    ### 获取买卖信号
    data_factor = data_factor.reset_index()
    data_sig = get_trading_sig(data_factor)
    data_sig.rename(columns={'ud':'factor'},inplace=True)

    # 获取 买卖信号数据
    data_sig = get_trading_sig(data_factor)
    print(data_sig)
    draw_trade_sig(data_sig)