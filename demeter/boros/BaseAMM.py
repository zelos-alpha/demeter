from abc import ABC, abstractmethod
from PositiveAMMMath import PositiveAMMMath


class BaseAMM(ABC):

    @classmethod
    def mintByBorosRouter(cls, totalCash: int, totalSize: int, maxCashIn: int, exactSizeIn: int):
        netCashIn, netLpOut = cls._mint({}, totalCash, totalSize, maxCashIn, exactSizeIn)

    @classmethod
    def burnByBorosRouter(cls, totalCash: int, totalSize: int, lpToBurn: int):
        pass

    @classmethod
    def swapByBorosRouter(cls):
        pass

    @staticmethod
    @abstractmethod
    def _mint(_state, totalCash: int, totalSize: int, maxCashIn: int, exactSizeIn: int):
        pass

    @staticmethod
    @abstractmethod
    def _burn(_state, totalCash: int, totalSize: int, lpToBurn: int):
        pass

    @staticmethod
    @abstractmethod
    def _swap(_state, sizeOut: int):
        pass

