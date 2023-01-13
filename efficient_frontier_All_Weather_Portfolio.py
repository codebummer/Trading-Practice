import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pandas_datareader.data as web
import yfinance as yf
from datetime import datetime
import sqlite3

start = datetime(2010, 7, 23)
end = datetime.today()
years = end.year - start.year + 0.5

yf.pdr_override()
def fetch_prices(stocks):
    df = pd.DataFrame([])
    for ticker, stock in stocks.items():
         df[stock] = (web.get_data_yahoo(ticker, start, end)['Close'])
    return df

stocks = {
  'SPY' : 'US Stocks',
  'EFA' : 'Non-US Dveloped Market Stocks',
  'EEM' : 'Emerging Market Stocks',
  'DBC' : 'Commodities',
  'GLD' : 'Gold',
  'EDV' : 'Extended Duration Teasuries',
  'LTPZ' : 'Tresuary Inflation-Protected Securities',
  'LQD' : 'US Corporate Bonds',
  'EMLC' : 'Emerging Market Bonds'
}

df = fetch_prices(stocks)

with sqlite3.connect('allweather_portfolio.db') as db:
  df.to_sql('All_Weather_Portfolio', db, if_exists='replace')

# with sqlite3.connect('allweather_portfolio.db') as db:
#   df = pd.read_sql('SELECT * from [All_Weather_Portfolio]', db)  

# BIZDAYS_A_YEAR = (end-start).days / years #This is wrong
BIZDAYS_A_YEAR = 252
daily_ret = df.pct_change().add(1).cumprod()
annual_ret = np.power(daily_ret[-1:], 1/years) - 1
daily_cov = df.pct_change().cov()
annual_cov = daily_cov * BIZDAYS_A_YEAR

port_ret, port_risk, port_weights = [], [], []

for _ in range(20_000):
    weights = np.random.random(len(stocks))
    weights /= np.sum(weights)
    
    returns = np.dot(weights, annual_ret.iloc[0])
    risk = np.sqrt(np.dot(weights.T, np.dot(annual_cov, weights)))
    # risk = np.sqrt(np.multiply(weights.T, np.dot(annual_cov, weights))) # same as above
    # risk = np.sqrt(weights.T * np.dot(annual_cov, weights))) # same as above
    
    port_ret.append(returns)
    port_risk.append(risk)
    port_weights.append(weights)

portfolio = {'Returns' : port_ret, 'Risk' : port_risk}
for i, s in enumerate(stocks.values()):
    portfolio[s] = [weight[i] for weight in port_weights]

df = pd.DataFrame(portfolio)
df = df[['Returns', 'Risk'] + [s for s in stocks.values()]]

df.plot.scatter(x='Risk', y='Returns', figsize=(8,6), grid=True)
plt.title('Efficient Frontier')
plt.xlabel('Risk')
plt.ylabel('Expected Returns')
plt.show()