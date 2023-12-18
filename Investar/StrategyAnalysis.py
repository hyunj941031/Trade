from datetime import datetime, timedelta
import pymysql
import pandas as pd
import numpy as np
from Investar import Analyzer
import matplotlib.dates as mdates

class ValidateDualMomentum:
    def __init__(self):
        self.mk = Analyzer.MarketDB()

    def get_momentum_df(self, target_day, stock_count=5, momentum_duration=90, having_days=7):
        """
            - target_day        : 모멘텀을 구할 기준날짜 ('2023-01-31')
            - momentum_duration : 모멘텀을 계산하기 위한 기간[일 수]
            - having_days       : 주식을 보유할 기간[일 수]
            - stock_count       : 모멘텀을 구할 종목 수
        """
        connection = pymysql.connect(host='localhost', user='root', port=3306, autocommit=True,
                                    password='myPassword', db='INVESTAR', charset='utf8')
        cursor = connection.cursor()
        
        # 모멘텀 계산 시작일
        target_day = pd.to_datetime(target_day)
        start_day = target_day - timedelta(days=momentum_duration)
        start_day = start_day.strftime('%Y-%m-%d')

        sql = f"SELECT MAX(date) FROM daily_price WHERE date <= '{start_day}'"
        cursor.execute(sql)
        result = cursor.fetchone()
        if (result[0] is None):
            print("start_date : {} -> returned None".format(sql))
            return
        start_day = result[0].strftime('%Y-%m-%d')
        
        # 모멘텀 계산 종료일
        end_day = target_day.strftime('%Y-%m-%d')
        sql = f"select max(date) from daily_price where date <= '{end_day}'"
        cursor.execute(sql)
        result = cursor.fetchone()
        if (result[0] is None):
            print("target_date : {} -> returned None".format(sql))
            return
        end_day = result[0].strftime('%Y-%m-%d')

        if target_day + timedelta(days=having_days) >= datetime.now():
            print("Days to make benefit is too small")
            return
        else:
            selling_stock_day = target_day + timedelta(days=having_days)
            selling_stock_day.strftime('%Y-%m-%d')
            sql = f"select max(date) from daily_price where date <= '{selling_stock_day}'"
            cursor.execute(sql)
            result = cursor.fetchone()
            if (result[0] is None):
                print("target_date : {} -> returned None".format(sql))
                return
            selling_stock_day = result[0].strftime('%Y-%m-%d')

        rows = []
        columns = ['code', 'company', 'old_price', 'new_price', 'returns', 'sell_price', 'sell_returns']
        for _, code in enumerate(self.mk.codes):
            sql = f"select close from daily_price where code='{code}' and date='{start_day}'"
            cursor.execute(sql)
            result = cursor.fetchone()
            if (result is None):
                continue
            old_price = int(result[0])

            sql = f"select close from daily_price where code='{code}' and date='{end_day}'"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result is None:
                continue
            new_price = int(result[0])

            sql = f"select close from daily_price where code='{code}' and date='{selling_stock_day}'"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result is None:
                continue
            sell_price = int(result[0])

            returns = (new_price / old_price - 1) * 100
            sell_returns = (sell_price / new_price - 1) * 100
            rows.append([code, self.mk.codes[code], old_price, new_price, returns, sell_price, sell_returns])
        
        df = pd.DataFrame(rows, columns=columns)
        df = df[['code', 'company', 'old_price', 'new_price', 'returns', 'sell_price', 'sell_returns']]
        df = df.sort_values(by='returns', ascending=False)
        df = df.head(stock_count)
        df.index = pd.Index(range(stock_count))
        connection.close()

        return df
    
class FindProperday:
    def __init__(self):
        self.mk = Analyzer.MarketDB()

    def get_the_best_return(self, company_name, target_day, having_days=7, check_ea=1):
        end_day = datetime.now().strftime('%Y-%m-%d')
        df = self.mk.get_daily_price(company_name, target_day, end_day)
        df.index = pd.to_datetime(df.index)
        df = df.iloc[1:, :] # target day보다 하루 뒤부터 확인

        df['MA20'] = df['close'].rolling(window=20).mean()
        df['stddev'] = df['close'].rolling(window=20).std()
        df['upper'] = df['MA20'] + (df['stddev'] * 2)
        df['lower'] = df['MA20'] - (df['stddev'] * 2)
        # Percent B (%b) : 주가가 볼린져 밴드의 어에 위치하는지에 대한 지표 <하단 볼린저 밴드(0), 중간 볼린저 밴드(0.5), 상단 볼린저 밴드(1)>
        df['PB'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])
        # 볼린져 밴드 폭
        df['bandwidth'] = (df['upper'] - df['lower']) / df['MA20'] * 100
        # MFI(현금흐름지표)
        df['TP'] = (df['high'] + df['low'] + df['close']) / 3
        df['PMF'] = 0 # Positive Money Flow
        df['NMF'] = 0 # Negative Money Flow
        for i in range(len(df.close)-1):
            if df.TP.values[i] < df.TP.values[i+1]:
                df.PMF.values[i+1] = df.TP.values[i+1] * df.volume.values[i+1]
                df.NMF.values[i+1] = 0
            else:
                df.NMF.values[i+1] = df.TP.values[i+1] * df.volume.values[i+1]
                df.PMF.values[i+1] = 0
        df['MFR'] = df.PMF.rolling(window=10).sum() / df.NMF.rolling(window=10).sum() # Money Flow Ratio / 10일 기준
        df['MFI10'] = 100 - 100 / (1 + df['MFR'])

        df['II'] = (2*df['close']-df['high']-df['low']) / (df['high']-df['low']) * df['volume'] # 일중강도 (Intraday Intensity)
        df['IIP21'] = df['II'].rolling(window=21).sum() / df['volume'].rolling(window=21).sum()*100 # 일중강도율 (Intraday Intensity Percent)
        
        ema60 = df.close.ewm(span=60).mean()
        ema130 = df.close.ewm(span=130).mean()
        macd = ema60 - ema130
        signal = macd.ewm(span=45).mean()
        macdhist = macd - signal
        df = df.assign(ema130=ema130, ema60=ema60, macd=macd, signal=signal, macdhist=macdhist).dropna()

        df['number'] = df.index.map(mdates.date2num)
        ohlc = df[['number', 'open', 'high', 'low', 'close']]

        ndays_high = df.high.rolling(window=14, min_periods=1).max()
        ndays_low = df.low.rolling(window=14, min_periods=1).min()

        fast_k = (df.close - ndays_low) / (ndays_high - ndays_low) * 100
        slow_d = fast_k.rolling(window=3).mean()
        df = df.assign(fast_k=fast_k, slow_d=slow_d).dropna()

        buy_days_list = []
        buy_days_dict = {}
        sell_days_list = []
        sell_days_dict = {}
        for i in range(1, len(df.close)):
            buy_term = [0,0,0]
            sell_term = [0,0,0]
            # if (df.PB.values[i] > 0.8 and df.MFI10.values[i] > 80):
            #     buy_term[0] = 1
            # elif (df.PB.values[i] < 0.2 and df.MFI10.values[i] < 20):
            #     sell_term[0] = 1

            if (df.PB.values[i] < 0.05 and df.IIP21.values[i] > 0):
                buy_term[1] = 1
            elif (df.PB.values[i] > 0.95 and df.IIP21.values[i] < 0):
                sell_term[1] = 1

            if ((df.ema130.values[i-1] < df.ema130.values[i]) and (df.slow_d.values[i-1] >= 20) and (df.slow_d.values[i] < 20)):
                buy_term[2] = 1
            elif ((df.ema130.values[i-1] > df.ema130.values[i]) and (df.slow_d.values[i-1] <= 80) and (df.slow_d.values[i] > 80)):
                sell_term[2] = 1
            
            if sum(buy_term) >= 1:
                buy_days_list.append(df.index[i])
                buy_days_dict[df.index.values[i]] = buy_term
            if sum(sell_term) >= 1:
                sell_days_list.append(df.index.values[i])
                sell_days_dict[df.index[i]] = sell_term
                
        
        if len(buy_days_list) == 0:
            return 0
        
        start_price = df.loc[buy_days_list[0], 'close']
        if len(sell_days_list) == 0:
            final_price = df.loc[df.index.values[-1], 'close']
        else:
            if buy_days_list[0] >= sell_days_list[0]:
                return 0
            threshold_index = df.index.get_loc(buy_days_list[0]) + having_days
            threshold_day = df.index[threshold_index]
            if threshold_day <= sell_days_list[0]:
                final_price = df.loc[threshold_day, 'close']
            else:
                final_price = df.loc[sell_days_list[0], 'close']


        returns = (final_price / start_price - 1) * 100
        return returns
            