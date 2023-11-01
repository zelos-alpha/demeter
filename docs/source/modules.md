# Modules

## Actuator

Actuator is the commander of backtesting. It controls the backtesting process. The most important function is run(), all 
backtesting process is managed by run(). 

The process of a backtesting is 

* Reset actuator
* Initialize strategy (set object to strategy, then run strategy.initialize())
* Process each row in data
    * Prepare data in this iteration
    * Run trigger
    * Run strategy.on_bar()
    * Update market, e.g. calculate fee earned of uniswap position
    * Run strategy.after_bar()
    * Get latest account status(balance)
    * Notify actions
* Run evaluator indicator
* Run strategy.finalize()
* Output result if required

Actuator also manage affairs after backtesting, such as output(to console or to files), strategy evaluating indicators. 

## broker和market

## 数据输入, 和指标

## 设置asset和price

## on_bar和触发器

## account status和market status

## 获取和保存结果

## 评价指标