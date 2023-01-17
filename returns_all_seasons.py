import pandas as pd
import pandas_datareader.data as web
import yfinance as yf
import numpy as np
from datetime import datetime
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import os
os.chdir(r'D:\myprojects')

start = datetime(2006, 2, 6)
end = datetime.today()
years = tuple(range(start.year, end.year+1))

yf.pdr_override()
def fetch_prices(stocks):
    df = pd.DataFrame([])
    for ticker, stock in stocks.items():
        df[ticker] = (web.get_data_yahoo(ticker, start, end)['Close'])
    return df

stocks = {
    'SPY' : 'US Stocks',
    'IEF' : 'US Tresuary 7-10 Years',
    'TLT' : 'US Treasury 20 Years',
    'GLD' : 'Gold',
    'DBC' : 'Commodities'
}

prices = fetch_prices(stocks)

weights = {
    'SPY' : 30,
    'IEF' : 15,
    'TLT' : 40,
    'GLD' : 7.5,
    'DBC' : 7.5
}   

weights = pd.Series(weights) 
invested = 10_000

usd = fetch_prices({'KRW=X':'USD/KRW'})
usd['change'] = usd.pct_change()
usd_cumprod = pd.DataFrame()
for year in years:
    usd_cumprod = pd.concat([usd_cumprod, usd.loc[usd.index.year==year,'change'].add(1).cumprod()])
usd = pd.concat([usd,usd_cumprod], axis='columns')
usd.columns = list(usd.columns)[:-1]+['cumprod']

holdings = invested * weights/weights.sum() / prices.iloc[0,:]
holdings = holdings.round().astype('int')
diff = (weights/weights.sum() - holdings*prices.iloc[0,:]/(holdings*prices.iloc[0,:]).sum())*100
if any(diff > 1):
    print('Warning: the following shows discrepancies in the designated asset allocation\n')
    print(diff.loc[diff>1])    
holdings = holdings.to_frame(name=pd.Timestamp(start))
holdings = holdings.T

values = holdings * prices.iloc[0,:]

yearly_prices = pd.DataFrame(prices.iloc[0,:], columns=[prices.index[0]])
for year in years:
    yearly_prices = pd.concat([yearly_prices, prices.loc[prices.index.year==year].iloc[-1,:]], axis='columns')
yearly_prices = yearly_prices.T

daily_ret = prices.pct_change()
yearly_cumprod = pd.DataFrame()
for year in years:
    yearly_cumprod = pd.concat([yearly_cumprod, daily_ret.loc[daily_ret.index.year==year].add(1).cumprod().iloc[-1,:]], axis='columns')
yearly_cumprod = yearly_cumprod.T

# rebalancing portfolio assets according to asset allocation plans, or 'weights' in this code
for yearend in yearly_prices.index:    
    if yearend == yearly_prices.index[0]:
        continue
    add = pd.DataFrame(yearly_prices.loc[yearend] * holdings.iloc[-1,:], columns=[yearend]).T
    values = pd.concat([values, add])    
    add = values.loc[yearend]/yearly_prices.loc[yearend]
    holdings = pd.concat([holdings, add.round(decimals=1).astype('int').to_frame().T])
    off_values = values.loc[yearend] - weights/100*values.loc[yearend].sum()    
    off_qty = (off_values/yearly_prices.loc[yearend]).round(decimals=1).astype('int')     
    gains = off_qty.clip(lower=0) * yearly_prices.loc[yearend]
    losses = off_qty.clip(upper=0) * yearly_prices.loc[yearend]
    loss_unit_prices = off_qty.clip(upper=0).where(off_qty.clip(upper=0)==0,1) * yearly_prices.loc[yearend]
    loss_unit_prices = loss_unit_prices.loc[loss_unit_prices!=0].sort_values()
    min_asset, min_unit_price = loss_unit_prices.index[0], loss_unit_prices[0]   
    if gains.sum() < min_unit_price:
        continue  
    rebalance_ratio = off_qty.clip(upper=0) / off_qty.clip(upper=0).sum()
    rebalance_qty = (gains.sum()*rebalance_ratio/yearly_prices.loc[yearend]).round(decimals=1).astype('int')
    rebalance_order = (rebalance_qty.abs()*yearly_prices.loc[yearend]).sort_values(ascending=False)
    rebalance_assets = rebalance_order.cumsum() < gains.sum() 
    holdings.loc[yearend] = holdings.loc[yearend] + rebalance_qty.loc[rebalance_assets] - off_qty.clip(lower=0)

port = holdings*yearly_prices
allocation_diff = (port.divide(port.sum(axis='columns'), axis='index') - weights/weights.sum()) * 100
allocation_diff.loc[allocation_diff.values>1][allocation_diff>1]

days = []
for year in years:
    days.append(len(holdings.loc[holdings.index.year==year]))
days = pd.Series(days, index=years)

holdings_ratio = pd.DataFrame()
for year in years:
    holdings_ratio = pd.concat([holdings_ratio,holdings.loc[holdings.index.year==year]/holdings.loc[holdings.index.year==year].sum(axis='columns')[0]])
holdings_sum = holdings_ratio.sum(axis='columns')
holdings_sum.loc[holdings_sum!=1]

daily_prices_FX_included = pd.DataFrame()
for year in years:
    daily_prices_FX_included = pd.concat([daily_prices_FX_included, (prices.loc[prices.index.year==year]).multiply(usd.loc[usd.index.year==year,'cumprod'], axis='index')])
daily_prices_FX_included = daily_prices_FX_included.dropna()

# daily prices * daily holdings (quantities of assets held)
daily_portfolio_values = pd.DataFrame()
daily_portfolio_values_FX_included = pd.DataFrame()
for year in years:
    daily_portfolio_values = pd.concat([daily_portfolio_values, prices.loc[prices.index.year==year]*holdings.loc[holdings.index.year==year].iloc[0,:]])
    daily_portfolio_values_FX_included = pd.concat([daily_portfolio_values_FX_included, daily_prices_FX_included.loc[daily_prices_FX_included.index.year==year]*holdings.loc[holdings.index.year==year].iloc[0,:]])


yearly_ret = pd.DataFrame()
for year in years:
    yearly = daily_portfolio_values.loc[daily_portfolio_values.index.year==year]
    yearly_ret = pd.concat([yearly_ret, np.power(yearly.pct_change().add(1).cumprod().iloc[-1,:], 1/days[year]) - 1], axis='columns')
yearly_ret = yearly_ret.T
yearly_ret = pd.concat([yearly_ret, pd.Series(yearly_ret.sum(axis='columns'),name='Total')], axis='columns')

daily_port_changes = daily_portfolio_values.pct_change()
all_year_cumprod = daily_port_changes.add(1).cumprod()
all_year_returns = np.power(all_year_cumprod.iloc[-1,:], 1/days.sum()) - 1
all_year_total_ret = all_year_returns.sum()


all_year_daily_cov = daily_port_changes.cov()
yearly_daily_cov = pd.DataFrame()
for year in years:
    yearly_daily_cov = pd.concat([yearly_daily_cov, daily_port_changes[daily_port_changes.index.year==year].cov()]) 

yearly_asset_stds = pd.DataFrame()
for year in years:
    yearly_asset_stds = pd.concat([yearly_asset_stds, daily_portfolio_values.loc[daily_portfolio_values.index.year==year].std()], axis=1)
yearly_asset_stds = yearly_asset_stds.T
yearly_asset_stds.index = years
yearly_max_stds = yearly_asset_stds.max()

yearly_total_stds = []
pricesums = daily_portfolio_values.sum(axis='columns')
for year in years:
    yearly_total_stds.append(pricesums.loc[pricesums.index.year==year].std())
yearly_total_stds = pd.DataFrame(yearly_total_stds, index = years)
yearly_total_stds.columns = ['']

all_year_class_stds = daily_portfolio_values.std()
all_year_total_stds = daily_portfolio_values.sum(axis='columns').std()

yearly_peaks = pd.DataFrame()
for year in years:
    yearly_peaks = pd.concat([yearly_peaks, daily_portfolio_values.loc[daily_portfolio_values.index.year==year].max()], axis=1)
yearly_peaks = yearly_peaks.T
yearly_peaks.index = years

all_year_peaks = daily_portfolio_values.max()

yearly_drawdowns = pd.DataFrame()
for year in years:
    yearly_drawdowns = pd.concat([yearly_drawdowns, daily_portfolio_values.loc[daily_portfolio_values.index.year==year]/yearly_peaks.loc[year] - 1])

yearly_mdds = pd.DataFrame()
for year in years:
    yearly_mdds = pd.concat([yearly_mdds, yearly_drawdowns.loc[yearly_drawdowns.index.year==year].min()], axis=1) #same as axis='column'
yearly_mdds.columns = years
yearly_mdds = yearly_mdds.T

all_year_drawdowns = daily_portfolio_values/all_year_peaks - 1
all_year_mdds = all_year_drawdowns.min()

risk_free = yearly_ret.sub(yearly_ret['TLT'], axis='index')
yearly_asset_stds.index = risk_free.index
yearly_total_stds.index = risk_free.index
yearly_sharpe = pd.concat([risk_free.loc[:,risk_free.columns!='Total'].div(yearly_asset_stds), \
    pd.Series(risk_free['Total']/yearly_total_stds[''], name='Total')], axis='columns')

all_year_class_sharpe = (all_year_returns-all_year_returns['TLT'])/all_year_class_stds
all_year_total_sharpe = (all_year_returns.sum()-all_year_returns['TLT'])/all_year_total_stds

# The following immediate block is just for initial plotting purposes.
import math
weighted_prices = weights*prices
daily_amounts = weighted_prices.sum(axis='columns')
ratio = ((invested/len(prices.columns))/prices.iloc[0,:]).round()
spy = math.floor(invested/prices['SPY'][0])
gld = math.floor(invested/prices['GLD'][0])

sns.set()
fig, ax = plt.subplots(1,2)
ax[0].plot((ratio*prices).sum(axis='columns'))
ax[0].plot(daily_portfolio_values.sum(axis='columns'))
ax[0].plot(prices['SPY']*spy)
ax[0].plot(prices['GLD']*gld)
ax[0].legend(['Non-Weighted', 'Weighted', 'SPY', 'GLD'])
ax[1].plot(ratio*prices)
ax[1].plot(daily_portfolio_values)
ax[1].legend(prices.columns)
plt.show()

# The following are actual portfolio plottings

fig, ax = plt.subplots(2,2, layout='constrained')
ax[0,0].plot(daily_portfolio_values.sum(axis='columns'))
ax[0,0].set_title('Total Assets FX Not Included')
ax[0,1].plot(daily_portfolio_values)
ax[0,1].set_title('Each Asset FX Not Included')
ax[1,0].plot(daily_portfolio_values_FX_included.sum(axis='columns'))
ax[1,0].set_title('Total Assets FX Included')
ax[1,1].plot(daily_portfolio_values_FX_included)
ax[1,1].set_title('Each Asset FX Included')
plt.ticklabel_format(style='plain')
ax[0,1].legend(daily_portfolio_values.columns)
ax[1,1].legend(daily_portfolio_values.columns)
fig.tight_layout()
plt.suptitle('All Weather Portfolio')
plt.show()

x = np.arange(len(yearly_ret.index))
width = 0.4
rects = {}
fig1, ax1 = plt.subplots(1, layout='constrained')
for n, asset in enumerate(yearly_ret.columns):
    rects[asset] = ax1.bar(x+width/len(x)*n, yearly_ret[asset]*100, width, label=asset)
ax1.set_ylabel('Annual Returns (%)')
ax1.set_xlabel('Years')
ax1.set_xticks(x, yearly_ret.index.year)    
plt.xticks(rotation=45)
ax1.legend(yearly_ret.columns)
# for asset in yearly_ret.columns:
#     ax1.bar_label(rects[asset])
fig.tight_layout()
plt.suptitle('All Weather Portfolio - Each Asset Annual Returns')
plt.show()

fig2, ax2 = plt.subplots(1, layout='constrained')
ax2.bar(yearly_ret.index.year, yearly_ret.sum(axis='columns')*100)
ax2.set_ylabel('Annual Returns (%)')
ax2.set_xlabel('Years')
plt.xticks(rotation=45)
fig.tight_layout()
plt.suptitle('All Weather Portfolio - Total Asset Annual Returns')
plt.show()
