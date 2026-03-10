from abc import ABC

from BaseAMM import BaseAMM


class NegativeAMM(BaseAMM):
    @staticmethod
    def _mint(_state, totalCash: int, totalSize: int, maxCashIn: int, exactSizeIn: int):
        print('NegativeAMM _mint')

    @staticmethod
    def _burn(_state, totalCash: int, totalSize: int, lpToBurn: int):
        print('NegativeAMM _burn')

    @staticmethod
    def _swap(_state, sizeOut: int):
        print('PositiveAMM _swap')
