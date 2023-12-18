from Investar import StrategyAnalysis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

start_time = time.time()
fp = StrategyAnalysis.FindProperday()
all_returns = []
for d in range(300):
    target_day = pd.to_datetime('2023-01-01') + timedelta(days=d)
    target_day = target_day.strftime('%Y-%m-%d')
    
    vdm = StrategyAnalysis.ValidateDualMomentum()
    df = vdm.get_momentum_df(target_day=target_day, stock_count=10, momentum_duration=90, having_days=7)
    returns = []
    for company in df.company:
        returns.append(fp.get_the_best_return(company, target_day))
    all_returns.append(np.mean(returns))

plt.plot(all_returns)
plt.show()

end_time = time.time()
print(f'Total Elapsed Time : {end_time - start_time}')
print(f'Mean returns : {np.mean(all_returns)}')