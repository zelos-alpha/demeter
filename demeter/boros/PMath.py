

class PMath:
    IONE_YEAR = 365 * 60 * 60 * 24

    @staticmethod
    def sign(x: int):
        if x > 0:
            return 1
        if x < 0:
            return -1
        return 0