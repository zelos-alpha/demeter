import random
class PRNG:

    def seed(self, state: int) -> None:
        random.seed(state)

    def next(self) -> int:
        return random.randint(0, 1000000)


if __name__ == '__main__':
    prng = PRNG()
    prng.seed(15)
    print(prng.next())  # 3423
    print(prng.next())  # 190
    print('-' * 20)
    prng = PRNG()
    prng.seed(15)
    print(prng.next())  # 3423
    print(prng.next())  # 190