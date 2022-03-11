"""
复现《A股量化择时模型GFTD第二版》的止损部分
"""
import numpy as np


# 调整 sig 数据，假设【不持有空头】&【止损机制】  
def adjust_trading_sig_withStoploss(data, stop_data):
    '''
    Parameters
        data [dateframe]    因子数据（字段['sig']）
        data [dateframe]    止损价格数据（字段['buy_n','sell_n','buystop','sellstop']）
    Return
        data [dateframe]    信号数据（字段['sig','pos']）
    '''
    ### 调整多空头: 不考虑空头，保证【多头、空头交错】
    buy_idx = data[ data.sig==1 ].index.tolist()
    sell_idx = data[ data.sig==-1 ].index.tolist()
    buy_sell_idx = [buy_idx, sell_idx] # 列表嵌套列表

    sig_list = []
    sig_list.append(buy_sell_idx[0][0])
    i,j = 0,1
    while i<len(buy_sell_idx[0]) and j< len(buy_sell_idx[1])+1:
        # sell_index和 buy相比，大于则纳入sig
        if len(sig_list)%2==1:
            if buy_sell_idx[1][i] > sig_list[-1]:
                sig_list.append(buy_sell_idx[1][i])
                i += 1
            elif buy_sell_idx[1][i] <= sig_list[-1]:
                del buy_sell_idx[1][i]
        # buy_index和 sell相比，大于则纳入sig
        elif len(sig_list)%2==0:
            if buy_sell_idx[0][j]>sig_list[-1]:
                sig_list.append(buy_sell_idx[0][j])
                j += 1
            elif buy_sell_idx[0][j]<=sig_list[-1]:
                del buy_sell_idx[0][j]
        else:
            raise ValueError('')
    
    # 若结果sell/buy有多，截取
    if len(buy_sell_idx[0])<len(buy_sell_idx[1]):
        buy_sell_idx[1] = buy_sell_idx[1][:len(buy_sell_idx[0])]
        print('减去了sell')
    elif len(buy_sell_idx[0])>len(buy_sell_idx[1]):        
        buy_sell_idx[0] = buy_sell_idx[0][:len(buy_sell_idx[1])]
        print('减去了buy')
    print('\n','#'*8, len(buy_sell_idx[0]), len(buy_sell_idx[1]))
    print(buy_sell_idx[0], buy_sell_idx[1])
    print('????????????????')

    ### 止损机制
        # 买入信号，若price达到止损点，卖出平仓；否则，等到卖出信号再平仓。
        # 卖出信号，若price达到止损点，买入平仓；否则，等到买入信号再平仓。
    # 当一组买卖信号之间 的价格达到buystop，则第一个满足该条件的点变为卖出信号，原卖出信号取消
    data['stop_price'] = np.nan
    for i in range(len(buy_sell_idx[0])):
        # 获取该买入对应的 止损price
        buy_n = data['buy_n'].iloc[buy_sell_idx[0][i]]
        stop_price = stop_data[ stop_data['buy_n']==buy_n ]['buystop'].iloc[0] # 切片出来是series
        ### 判断 这一组【买卖】之间是否触发止损
        data_slice = data.iloc[buy_sell_idx[0][i]:buy_sell_idx[1][i]]
        data_slice.loc[:,'stop_price'] = stop_price
        data_slice.loc[:,'stop'] = data_slice.apply(lambda x:1 if x['open']<x['stop_price'] else np.nan, axis=1)
        # 若['stop']不是全为空==>【触发止损】，替换卖空信号点
        if len(data_slice['stop'].unique())>1:
            # 替换sell_index为第一个非nan值
            stop_point = data_slice['stop']
            print('#'*80,'\n','触发一次止损机制')
            print('在原先的卖出信号点', buy_sell_idx[1][i], end='')
            buy_sell_idx[1][i] = list(data_slice['stop'][data_slice['stop'].notnull()].index)[0]
            print(' 前的 %d 处触发止损机制' % buy_sell_idx[1][i])        
        #print(data_slice[['date_time','buy_n','sig','stop_price','open']])

    # 修正 sig 数据
    data['sig'] = 0
    data.loc[buy_sell_idx[0],'sig'] = 1
    data.loc[buy_sell_idx[1],'sig'] = -1

    # 修正 sig 数据
    data['sig'] = 0
    data['sig'][buy_sell_idx[0]] = 1
    data['sig'][buy_sell_idx[1]] = -1
    # 信号的第二天再真正交易
    data['sig'] = data['sig'].shift(1).fillna(0)
    data['pos'] = np.cumsum(data['sig'])
    return data
