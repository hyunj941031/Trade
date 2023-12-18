from . import StrategyAnalysis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

class CalculateReturns:
    def __init__(self):
        self.fp = StrategyAnalysis.FindProperday()
    def get_mean_returns(self, start_date=0, duration=90, stock_count=5, having_days=7):
        all_returns = []
        if start_date == 0:
            start_date = '2023-06-01'
        for d in range(duration):
            target_day = pd.to_datetime(start_date) + timedelta(days=d)
            target_day = target_day.strftime('%Y-%m-%d')
            
            vdm = StrategyAnalysis.ValidateDualMomentum()
            df = vdm.get_momentum_df(target_day=target_day, stock_count=stock_count, momentum_duration=90, having_days=having_days)
            if len(df) == 0:
                continue

            returns = []
            for company in df.company:
                returns.append(self.fp.get_the_best_return(company, target_day))
            all_returns.append(np.mean(returns))
        return np.mean(all_returns)