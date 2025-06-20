class Position:

    @staticmethod
    def getPositionKey(_market: str, _collateralToken: str, _isLong: bool):
        return f'{_market}-{_collateralToken}-{_isLong}'
