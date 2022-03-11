"""
导入数据 并 进行数据处理
"""
import numpy as np
import pandas as pd
import datetime


class GetData():
    def __init__(self, future='IC', time_frequency=240) -> None:
        self.future = future
        self.time_frequency = time_frequency
        # 直接 cd 路径，不用内部限死 self.path
        self.future_data = pd.read_csv('data\IC_1_min.csv', header=0, index_col=0)
        self.factor_data = pd.read_csv('data\IC_info.csv', header=0, index_col=0)[['date', 'factor']]

    def __str__(self) -> str:
        param_list = ['future', 'time_frequency']
        value = [(name, getattr(self, name)) for name in param_list]
        f_string = ''
        for i, (item, count) in enumerate(value):
            f_string += (f'#{i+1}: '
                         f'{item.title():<10s} = '
                         f'{count}\n')
        return f_string
    
    @staticmethod
    def get_date_time(data, time_frequency=240):
        """获取 datetime类型数据

        Args:
            data (dataframe): 期权行情数据，含字段['date',('time')]
            daily (bool, optional): _description_. Defaults to False.

        Raises:
            TypeError: Unvaild value for "time_frequency"!

        Returns:
            datetime: 一列数据
        """        
        if time_frequency == 240: # 无 'time' 字段
            return data.apply(lambda x:datetime.datetime.strptime(str(int(x['date']))\
                    +' '+str(1500),'%Y%m%d %H%M'), axis=1) 
        elif time_frequency < 240:
            return data.apply(lambda x:datetime.datetime.strptime(str(int(x['date']))\
                    +' '+str(int(x['time']))[:-5],'%Y%m%d %H%M'), axis=1)
        else: 
            raise TypeError('Unvaild value for "time_frequency"!')
    
    # 获取 复权价格数据，后续要存储起来
    def get_refactor_price(self):
        """获取 复权后的期货数据

        Returns:
            dataframe: 复权后的期货数据 含字段['r_high', 'r_low', 'r_open', 'r_close']
        """        
        self.data = pd.merge(self.future_data, self.factor_data, on='date')
        # 复权
        col_list = ['high','low','open','close']
        for i in col_list:
            self.data['r_'+ i] = np.multiply(self.data[i], self.data['factor'])
        return self.data

    def run(self):
        self.future_data['date_time'] = self.get_date_time(self.future_data) # 计算因子需要
        option_data = self.get_refactor_price()
        return option_data



# 转换数据 时间频率
def transfer_timeFreq(ori_data, time_freq, ic_multiplier=200):
    '''
    Parameters
        ori_data  [dataframe]    原始数据（字段[ ])
        time_freq [int]          时间频率（单位：分钟）
        ic_multiplier  [int]          ic乘数（分钟内均价 turnover/volume，需要除ic乘数）
    '''
    if time_freq==1:
        return ori_data
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
    data_list = [get_lastday, max_high, min_low, last_close, get_sum]
    temp = pd.concat(data_list,axis=1)
    data_newfreq = temp.reset_index()
    data_newfreq['preclose'] = data_newfreq['close'].shift(-1)
    data_newfreq['average_price'] = np.divide(data_newfreq['all_turnover'],
        data_newfreq['all_volume'])/ic_multiplier

    #### 若交易量为 0 （数据缺失或触发了熔断），删除数据
    nan_vloume_date = list(set(data_newfreq[data_newfreq['all_volume']==0].date))
    data_newfreq.drop(data_newfreq[data_newfreq.date.isin(nan_vloume_date)].index , inplace=True)
    # 重设连续index
    data_newfreq.index = (range(data_newfreq.shape[0]))
    data_newfreq['date_time'] = GetData().get_date_time(data_newfreq['date_time'])
    return data_newfreq


if __name__ == '__main__': 
    d = GetData()
    data = d.run()
    print(data)