

class LibOrderIdSort:
    @staticmethod
    def make_temp_array(ids: list[OrderId]) -> list[OrderIdEntry]:
        pass  # todo


class OrderIdEntryLib:
    @staticmethod
    def random_partition(arr: list[OrderIdEntry], low: int, high: int, prng: PRNG) -> int:
        n = high - low
        if n == 1: return low
        pivot_pos = OrderIdEntryLib.random_pivot(arr, low, high, prng)
        return OrderIdEntryLib.partition(arr, low, high, pivot_pos)

    @staticmethod
    def partition(arr: list[OrderIdEntry], low: int, high: int, pivot_pos: int) -> int:
        n = high - low
        if n == 1: return low
        pivot = arr[pivot_pos]
        arr[pivot_pos] = arr[low]
        l = low
        r = high
        while True:
            l += 1
            while l < high and arr[l] < pivot:
                l += 1
            r -= 1
            while r > low and arr[r] > pivot:
                r -= 1
            if l >= r:
                break
            arr[l], arr[r] = arr[r], arr[l]
        arr[low] = arr[r]
        arr[r] = pivot
        return r

    @staticmethod
    def random_pivot(arr: list[OrderIdEntry], low: int, high: int, prng: PRNG) -> int:
        n = high - low
        if n == 1: return low
        if n == 2: return low + (prng.next() % 2)
        rand_pos = (prng.next() % (n - 2)) + low + 1
        a = arr[low]
        b = arr[rand_pos]
        c = arr[high - 1]
        a, b, c = OrderIdEntryLib._network_sort(a, b, c)
        arr[low] = a
        arr[rand_pos] = b
        arr[high - 1] = c
        return rand_pos

    @staticmethod
    def _network_sort(a: OrderIdEntry, b: OrderIdEntry, c: OrderIdEntry) -> (OrderIdEntry, OrderIdEntry, OrderIdEntry):
        if b < a: (a, b) = (b, a)
        if c < a: (a, c) = (c, a)
        if c < b: (b, c) = (c, b)
        return a, b, c