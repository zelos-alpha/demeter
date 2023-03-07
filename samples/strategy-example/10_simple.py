from datetime import timedelta, date

import pandas as pd

from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, RowData, simple_moving_average, ChainType, \
    MarketInfo, UniLpMarket, MarketDict

pd.options.display.max_columns = None
pd.set_option('display.width', 5000)


class MyFirstStrategy(Strategy):
    def on_bar(self, row_data: MarketDict[RowData]):
        # show how to access data
        if row_data.default.row_id == 1000:
            market: UniLpMarket = self.broker.markets.default
            # access current row
            print(row_data.default.closeTick)
            print(self.data.default.loc[row_data.default.timestamp].closeTick)

            # access the row by data index
            print(self.data.default.closeTick[0])  # first row
            print(self.data.default["closeTick"].iloc[0])  # first row
            print(self.data.default.closeTick[row_data.default.row_id])  # current row

            # access previous or after row
            print(
                self.data.default.loc[row_data.default.timestamp - timedelta(hours=1)].closeTick)  # data of an hour ago
            print(self.data.default.loc[
                      row_data.default.timestamp + timedelta(hours=1)].closeTick)  # data of an hour later

            print(broker.assets[market.token0].balance,
                  broker.assets[market.token1].balance)  # show balance in asset 0,1
            print(broker.assets[market.base_token].balance,
                  broker.assets[market.quote_token].balance)  # show balance in base quote
            print(self.broker.get_account_status(
                actuator.token_prices.loc[row_data.default.timestamp]))  # get current capital status,
            for position_info, position in market.positions.items():
                print(position_info, position)  # show all position


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # declare  token0
    eth = TokenInfo(name="eth", decimal=18)  # declare token1
    pool = UniV3Pool(usdc, eth, 0.05, usdc)  # declare pool
    test_market = MarketInfo("uni_market")

    actuator = Actuator()  # declare actuator
    broker = actuator.broker
    market = UniLpMarket(test_market, pool)

    broker.add_market(market)
    broker.set_balance(usdc, 10000)
    broker.set_balance(eth, 10)

    actuator.strategy = MyFirstStrategy()  # set strategy to actuator

    market.data_path = "../data"  # set data path
    market.load_data(ChainType.Polygon.name,  # load data
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 20),
                     date(2022, 8, 20))
    market.data["ma5"] = simple_moving_average(market.data.price)  # add indicator
    actuator.set_price(market.get_price_from_data())
    actuator.run()  # run test
