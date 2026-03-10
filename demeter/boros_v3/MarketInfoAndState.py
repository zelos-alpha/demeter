

class MarketInfoAndState:
    f_tag_to_index = {}  # FTag: FIndex
    _acc_state_map = {}

    def __init__(self):
        pass

    def _to_f_index(self, f_tag: FTag) -> FIndex:
        return self.f_tag_to_index[f_tag]

    def _acc_state(self, acc) -> AccountState:
        return self._acc_state_map[acc]
