from typing import List, Tuple, Literal
from dataclasses import dataclass, field
from decimal import Decimal
from .OrderBookUtils import OrderBookStorageStruct
from ._typing import Side, Stage
from .MarketEntry import MarketEntry
from .TickMath import TickMath


@dataclass
class TickSweepState:
    ob_struct: OrderBookStorageStruct
    stage: Stage = Stage.LOOP_BATCH
    ticks: List[int] = field(default_factory=list)
    tick_sizes: List[Decimal] = field(default_factory=list)
    single_index: int = 0
    bin_min: int = 0
    bin_max: int = 0
    market: MarketEntry = None
    side: Side = Side.SHORT
    n_ticks_to_try_at_once: int = 5

    @staticmethod
    def create(market: MarketEntry, ob_struct: OrderBookStorageStruct, tick_side: Side,
               n_ticks_to_try_at_once: int) -> 'TickSweepState':
        if tick_side == Side.SHORT:
            start_tick = -32768  # type(int16).min
        else:
            start_tick = 32767  # type(int16).max

        # 调用 getNextNTicks
        ticks, tick_sizes = market.get_next_n_ticks(ob_struct, tick_side, start_tick, n_ticks_to_try_at_once)

        if len(ticks) == 0:
            # 如果没有tick，返回 SWEPT_ALL 状态
            return TickSweepState(
                ob_struct=ob_struct,
                stage=Stage.SWEPT_ALL,
                market=market,
                side=tick_side,
                n_ticks_to_try_at_once=n_ticks_to_try_at_once
            )

        return TickSweepState(
            ob_struct=ob_struct,
            stage=Stage.LOOP_BATCH,
            ticks=ticks,
            tick_sizes=tick_sizes,
            single_index=0,
            bin_min=0,
            bin_max=0,
            market=market,
            side=tick_side,
            n_ticks_to_try_at_once=n_ticks_to_try_at_once
        )

    def has_more(self) -> bool:
        """
        检查是否还有更多tick需要扫描

        对应 Solidity:
        function hasMore(TickSweepState memory $) internal pure returns (bool) {
            return $.stage != Stage.FOUND_STOP && $.stage != Stage.SWEPT_ALL;
        }

        返回:
            True: 继续扫描
            False: 扫描结束
        """
        return self.stage != Stage.FOUND_STOP and self.stage != Stage.SWEPT_ALL

    def get_last_tick(self) -> int:
        """
        获取当前最后一个tick

        对应 Solidity:
        function getLastTick(TickSweepState memory $) internal pure returns (int16 lastTick)

        返回:
            当前最后一个tick值
        """
        if self.stage == Stage.LOOP_BATCH:
            return self._last_tick_array()
        elif self.stage in (Stage.LOOP_SINGLE, Stage.BINARY_SEARCH, Stage.FOUND_STOP):
            return self.ticks[self.single_index]
        else:
            raise ValueError(f"Invalid stage for getLastTick: {self.stage}")

    def get_last_tick_and_sum_size(self) -> Tuple[int, Decimal]:
        """
        获取最后一个tick和累计订单数量

        对应 Solidity:
        function getLastTickAndSumSize(TickSweepState memory $)
            internal pure returns (int16 lastTick, uint256 sumSize)

        返回:
            (lastTick, sumSize): 最后一个tick和累计数量
        """
        if self.stage == Stage.LOOP_BATCH:
            return self._last_tick_array(), sum(self.tick_sizes)
        elif self.stage in (Stage.LOOP_SINGLE, Stage.FOUND_STOP):
            return self.ticks[self.single_index], self.tick_sizes[self.single_index]
        elif self.stage == Stage.BINARY_SEARCH:
            last_tick = self.ticks[self.single_index]
            # sum from bin_min to single_index (inclusive)
            sum_size = sum(self.tick_sizes[self.bin_min:self.single_index + 1])
            return last_tick, sum_size
        else:
            raise ValueError(f"Invalid stage for getLastTickAndSumSize: {self.stage}")

    def get_sum_cost(self, tick_step: int) -> Decimal:
        """
        计算累计成本 (费率 * 数量)

        对应 Solidity:
        function getSumCost(TickSweepState memory $, uint8 tickStep) internal pure returns (int256 cost)

        参数:
            tick_step: tick步长

        返回:
            累计成本
        """
        cost = Decimal('0')

        if self.stage == Stage.LOOP_BATCH:
            for i in range(len(self.tick_sizes)):
                cost += self._calculate_tick_cost(self.ticks[i], self.tick_sizes[i], tick_step)
        elif self.stage == Stage.LOOP_SINGLE:
            cost = self._calculate_tick_cost(
                self.ticks[self.single_index],
                self.tick_sizes[self.single_index],
                tick_step
            )
        elif self.stage == Stage.BINARY_SEARCH:
            for i in range(self.bin_min, self.single_index + 1):
                cost += self._calculate_tick_cost(self.ticks[i], self.tick_sizes[i], tick_step)
        else:
            raise ValueError(f"Invalid stage for getSumCost: {self.stage}")

        return cost

    def _last_tick_array(self) -> int:
        """获取tick列表的最后一个值"""
        if not self.ticks:
            raise ValueError("Empty ticks array")
        return self.ticks[-1]

    def _calculate_tick_cost(self, tick: int, size: Decimal, tick_step: int) -> Decimal:
        """
        计算单个tick的成本

        成本 = size * rate
        对于LONG: size为正
        对于SHORT: size为负

        对应 Solidity:
        function _calculateTickCost(int16 tick, uint256 size, Side side, uint8 tickStep)
            private pure returns (int256)

            size.toSignedSize(side).mulDown(TickMath.getRateAtTick(tick, tickStep));
        """
        # 简化: 假设rate = tick * tick_step (实际需要更复杂的计算)
        rate = TickMath.get_rate_at_tick(tick, tick_step)

        # 转换为有符号数
        if self.side == Side.LONG:
            signed_size = size
        else:
            signed_size = -size

        return signed_size * Decimal(rate)

    def _end_tick(self) -> int:
        """
        获取扫描方向的边界tick

        对应 Solidity:
        function endTick(Side side) internal pure returns (int16) {
            return side == Side.LONG ? type(int16).min : type(int16).max;
        }

        - LONG: 从小到大扫描，边界是 -32768
        - SHORT: 从大到小扫描，边界是 32767
        """
        if self.side == Side.LONG:
            return -32768  # type(int16).min
        else:
            return 32767  # type(int16).max

    @staticmethod
    def _should_use_binary_search(length: int) -> bool:
        """
        判断是否应该使用二分查找

        对应 Solidity:
        function _shouldUseBinarySearch(uint256 length) internal pure returns (bool) {
            return length > 4;
        }

        参数:
            length: tick列表长度

        返回:
            True: 使用二分查找 (>4个tick)
            False: 使用单点扫描 (<=4个tick)
        """
        return length > 4

    def transition_up(self):
        """
        向上转换，扩大搜索范围

        在calcSwapAmountBookAMM中，当订单簿数量不足时调用此函数。

        对应 Solidity:
        function transitionUp(TickSweepState memory $) internal view {
            if ($.stage == Stage.LOOP_BATCH) {
                _transitionUpBatch($);
            } else if ($.stage == Stage.LOOP_SINGLE) {
                _transitionUpSingle($);
            } else if ($.stage == Stage.BINARY_SEARCH) {
                _transitionUpBinary($);
            } else {
                assert(false);
            }
        }

        转换规则:
        - LOOP_BATCH -> 加载下一批tick，或转为SWEPT_ALL
        - LOOP_SINGLE -> 移动到下一个tick
        - BINARY_SEARCH -> 向上二分查找
        """
        if self.stage == Stage.LOOP_BATCH:
            self._transition_up_batch()
        elif self.stage == Stage.LOOP_SINGLE:
            self._transition_up_single()
        elif self.stage == Stage.BINARY_SEARCH:
            self._transition_up_binary()
        else:
            raise ValueError(f"Cannot transitionUp from stage: {self.stage}")

    def _transition_up_batch(self):
        """
        LOOP_BATCH 阶段的向上转换

        对应 Solidity:
        function _transitionUpBatch(TickSweepState memory $) private view {
            if ($.ticks.length != $.nTicksToTryAtOnce || _lastTickArray($) == $.side.endTick()) {
                $.stage = Stage.SWEPT_ALL;
                return;
            }

            ($.ticks, $.tickSizes) = IMarket($.market).getNextNTicks(
                $.side, _lastTickArray($), $.nTicksToTryAtOnce
            );

            if ($.ticks.length == 0) {
                $.stage = Stage.SWEPT_ALL;
                return;
            }
        }
        """
        # 检查是否已到达边界
        last_tick = self._last_tick_array()
        end_tick = self._end_tick()

        if len(self.ticks) != self.n_ticks_to_try_at_once or last_tick == end_tick:
            self.stage = Stage.SWEPT_ALL

        # 加载下一批tick
        new_ticks, new_sizes = self.market.get_next_n_ticks(
            self.ob_struct, self.side, last_tick, self.n_ticks_to_try_at_once
        )

        if len(new_ticks) == 0:
            self.stage = Stage.SWEPT_ALL

        # 更新tick列表
        self.ticks = new_ticks
        self.tick_sizes = new_sizes
        self.single_index = 0

    def _transition_up_single(self):
        """
        LOOP_SINGLE 阶段的向上转换

        对应 Solidity:
        function _transitionUpSingle(TickSweepState memory $) private pure {
            if (++$.singleIndex == $.ticks.length) assert(false);
        }
        """
        self.single_index += 1
        if self.single_index >= len(self.ticks):
            raise ValueError("singleIndex overflow in transitionUpSingle")

    def _transition_up_binary(self):
        """
        BINARY_SEARCH 阶段的向上转换

        对应 Solidity:
        function _transitionUpBinary(TickSweepState memory $) private pure {
            $.bin_min = $.singleIndex + 1;
            if ($.bin_min == $.bin_max) {
                if ($.bin_min == $.ticks.length) assert(false);
                $.singleIndex = $.bin_min;
                $.stage = Stage.FOUND_STOP;
            } else {
                $.singleIndex = avg($.bin_min, $.bin_max);
            }
        }
        """
        self.bin_min = self.single_index + 1

        if self.bin_min == self.bin_max:
            if self.bin_min >= len(self.ticks):
                raise ValueError("bin_min overflow in transitionUpBinary")
            self.single_index = self.bin_min
            self.stage = Stage.FOUND_STOP
        else:
            self.single_index = (self.bin_min + self.bin_max) // 2

    def transition_down(self):
        """
        向下转换，缩小搜索范围

        在calcSwapAmountBookAMM中，当订单簿数量过多时调用此函数。

        对应 Solidity:
        function transitionDown(TickSweepState memory $) internal pure {
            if ($.stage == Stage.LOOP_BATCH) {
                _transitionDownBatch($);
            } else if ($.stage == Stage.LOOP_SINGLE) {
                $.stage = Stage.FOUND_STOP;
            } else if ($.stage == Stage.BINARY_SEARCH) {
                _transitionDownBinary($);
            } else {
                assert(false);
            }
        }

        转换规则:
        - LOOP_BATCH -> 转为LOOP_SINGLE或BINARY_SEARCH
        - LOOP_SINGLE -> 转为FOUND_STOP
        - BINARY_SEARCH -> 向下二分查找
        """
        if self.stage == Stage.LOOP_BATCH:
            self._transition_down_batch()
        elif self.stage == Stage.LOOP_SINGLE:
            self.stage = Stage.FOUND_STOP
        elif self.stage == Stage.BINARY_SEARCH:
            self._transition_down_binary()
        else:
            raise ValueError(f"Cannot transitionDown from stage: {self.stage}")

    def _transition_down_batch(self):
        """
        LOOP_BATCH 阶段的向下转换

        对应 Solidity:
        function _transitionDownBatch(TickSweepState memory $) private pure {
            if (!_shouldUseBinarySearch($.ticks.length)) {
                $.stage = Stage.LOOP_SINGLE;
                $.singleIndex = 0;
            } else {
                $.stage = Stage.BINARY_SEARCH;
                $.bin_min = 0;
                $.bin_max = $.ticks.length;
                $.singleIndex = avg($.bin_min, $.bin_max);
            }
        }

        规则:
        - tick数量 <= 4: 进入LOOP_SINGLE
        - tick数量 > 4: 进入BINARY_SEARCH
        """
        if not self._should_use_binary_search(len(self.ticks)):
            self.stage = Stage.LOOP_SINGLE
            self.single_index = 0
        else:
            self.stage = Stage.BINARY_SEARCH
            self.bin_min = 0
            self.bin_max = len(self.ticks)
            self.single_index = (self.bin_min + self.bin_max) // 2

    def _transition_down_binary(self):
        """
        BINARY_SEARCH 阶段的向下转换

        对应 Solidity:
        function _transitionDownBinary(TickSweepState memory $) private pure {
            $.bin_max = $.singleIndex;
            if ($.bin_min == $.bin_max) {
                $.stage = Stage.FOUND_STOP;
            } else {
                $.singleIndex = avg($.bin_min, $.bin_max);
            }
        }
        """
        self.bin_max = self.single_index

        if self.bin_min == self.bin_max:
            self.stage = Stage.FOUND_STOP
        else:
            self.single_index = (self.bin_min + self.bin_max) // 2
