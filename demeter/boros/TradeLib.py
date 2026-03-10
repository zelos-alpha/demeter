from _typing import Side, Fill, Trade

class TradeLib:
    MARK128 = 0xffffffffffffffffffffffffffffffff

    @staticmethod
    def _from(_signedSize: int, _signedCost: int) -> str:
        hexSize = hex(_signedSize & TradeLib.MARK128)
        hexSize = f"{hexSize[2:]:0>32}"
        hexCost = hex(_signedCost & TradeLib.MARK128)
        hexCost = f"{hexCost[2:]:0>32}"
        return f"0x{hexSize}{hexCost}"
    
    @staticmethod
    def _from3(_side: Side, _size: int, _rate: int) -> str:
        _signedSize = _size
        _signedCost = _signedSize * _rate
        if _side == Side.LONG:
            return TradeLib._from(_signedSize, _signedCost)
        else:
            return TradeLib._from(-_signedSize, -_signedCost)


    @staticmethod
    def unpack(trade: int) -> (int, int):
        pass

    @staticmethod
    def opposite(trade: int) -> str:
        _signedSize, _signedCost = TradeLib.unpack(trade)
        return TradeLib._from(-_signedSize, -_signedCost)

    @staticmethod
    def isZero(trade: Trade):
        return trade == 0

    @staticmethod
    def signedSize(trade: Trade) -> int:
        _signedSize, _signedCost = TradeLib.unpack(trade)
        return _signedSize

    @staticmethod
    def signedCost(trade: Trade) -> int:
        _signedSize, _signedCost = TradeLib.unpack(trade)
        return _signedCost


class FillLib:
    @staticmethod
    def from3(_side: Side, _size: int, _rate: int) -> Fill:
        pass  # todo
