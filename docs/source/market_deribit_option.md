# Deribit option market

To hedge against Greek values, we introduced the Deribit options market.

The Deribit options market can be utilized for options investment or backtesting of Greek hedging strategies. 
In this market, you can buy or sell options based on the current order book. 
Currently, this market only supports taker orders and does not support maker orders.

The backtesting process requires the order book dataset from Deribit. 
Currently, access to the order book is available through services like Tardis, but these services are usually expensive (costing a few hundred dollars per month). 
Therefore, we set up a service to record orderbooks via [Deribit api](https://docs.deribit.com/#public-get_order_book_by_instrument_id).

To save resources, we collect data once per hour. The data collection is limited to ETH.

The collected data has been uploaded to [Dropbox](https://www.dropbox.com/scl/fo/kwk5kgiseu5rvccjscd0f/ANswtRLzpCxOc6cMTH0oRlE?rlkey=ai071f9695uz287lt8k0bci5e&dl=0). If you need to conduct options backtesting, you'll need to download historical order books first.

During backtesting, you can select the desired orders from the current order book and then purchase them directly or buy them at specific prices. Transaction fees for buying and selling options will also be calculated.

Upon options expiration, they will be automatically exercised based on whether they are in-the-money or out-of-the-money.

Data in deribit option market is hourly, so when you backtesting with option market only, backtesting will run hourly. 
But when you work with the other market which has minutely data, the whole backtesting will be minutely. So we introduced the concept of 'open'.
Option market data is hourly, so it will open at the hour. When it is open, it's writable, you can buy and sell. 
But at the rest 59 minutes, the market is not open, which means it is readonly, you can read status only.    