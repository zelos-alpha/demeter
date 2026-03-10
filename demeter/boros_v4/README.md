# boros说明

* 入口为market.py 待TradeModule更新完place_single_order逻辑更新该部分
* AMM部分已经实现mint/burn相关流程，稍后更新测试以及AMMModule模块入口
* 目前正在更新Market部分的orderAndOtc部分逻辑
* 待处理逻辑：
  * OrderId从int值调整为object对象
  * 合并进来用户数据settle计算
  * 合并进来match order以及otc流程
  * 清算处理