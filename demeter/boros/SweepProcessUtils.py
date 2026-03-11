from _typing import UserMem, SweptF, PartialData
from typing import List
from ProcessMergeUtils import ProcessMergeUtils

class SweepProcessUtils:
    @staticmethod
    def _sweepProcess(user: UserMem, part: PartialData):
        longSweptF = SweepProcessUtils.__sweepFOneSide(user.longIds)
        shortSweptF = SweepProcessUtils.__sweepFOneSide(user.shortIds)
        return ProcessMergeUtils._processF(part, longSweptF, shortSweptF)  # todo

    @staticmethod
    def __sweepFOneSide(ids: list) -> List[SweptF]:
        pass  # todo
