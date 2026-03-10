
class TickMath:

    @staticmethod
    def get_rate_at_tick(tick, step):
        return TickMath._get_rate_at_tick(tick * step)

    @staticmethod
    def _get_rate_at_tick(tick):
        """
        rate = g(tick)
        g(tick) = 1.00005^tick - 1 for tick >= 0
        g(tick) = -g(-tick) for tick < 0
        This function only works for tick from -32768 * 15 to 32767 * 15
        :param tick:
        :return:
        """
        tick = int(tick)
        abs_tick = tick if tick >= 0 else -tick
        assert abs_tick <= 32768

        _rate = 0xfffcb92e5f40b9f2f86266c763702fb7 if abs_tick & 0x1 != 0 else 0x100000000000000000000000000000000
        if abs_tick & 0x2 != 0: _rate = (_rate * 0xfff972677b0287f20ca2232ae174ac61) >> 128
        if abs_tick & 0x4 != 0: _rate = (_rate * 0xfff2e4f9e77ca923223ffc276878b031) >> 128
        if abs_tick & 0x8 != 0: _rate = (_rate * 0xffe5ca9f907218edf3c20a9b87d8b905) >> 128
        if abs_tick & 0x10 != 0: _rate = (_rate * 0xffcb97ee039bed3373e5b571bf3e4989) >> 128
        if abs_tick & 0x20 != 0: _rate = (_rate * 0xff973a9678d50163584a32b3255afbbc) >> 128
        if abs_tick & 0x40 != 0: _rate = (_rate * 0xff2ea00defa36b3de45cff7e3bc651f2) >> 128
        if abs_tick & 0x80 != 0: _rate = (_rate * 0xfe5deb59ac7b1aae542822b60b658f66) >> 128
        if abs_tick & 0x100 != 0: _rate = (_rate * 0xfcbe817ac9c95c76b6730ccf91e6d8de) >> 128
        if abs_tick & 0x200 != 0: _rate = (_rate * 0xf9879cae3104ef30d992ea9a423d2979) >> 128
        if abs_tick & 0x400 != 0: _rate = (_rate * 0xf33916a17af80ec5fc60d88f617d0b95) >> 128
        if abs_tick & 0x800 != 0: _rate = (_rate * 0xe7156db1a55bd580fae8391a0ef5618b) >> 128
        if abs_tick & 0x1000 != 0: _rate = (_rate * 0xd097adc1c6919e761394d554da360e46) >> 128
        if abs_tick & 0x2000 != 0: _rate = (_rate * 0xa9f6d43953345a56a0df0cb1c591fb10) >> 128
        if abs_tick & 0x4000 != 0: _rate = (_rate * 0x70d7d2303df60688dcde5dbd2c3f8bb3) >> 128
        if abs_tick & 0x8000 != 0: _rate = (_rate * 0x31bd8ddcefd287b5a91fb8c4681a9810) >> 128

        _rate = 115792089237316195423570985008687907853269984665640564039457584007913129639935 // _rate
        _rate >>= 23
        if abs_tick & 0x40000 != 0: _rate = (_rate * 0xf06345295e343b7bc86046165c00aba) >> 105
        if abs_tick & 0x20000 != 0: _rate = (_rate * 0x57b4d53300bbb68ed922df63e3590) >> 105
        if abs_tick & 0x10000 != 0: _rate = (_rate * 0x34fa3662ba5cbd83623db239c427) >> 105
        _rate = (_rate * 10 ** 18 + (1 << 104)) >> 105
        _rate -= 10 ** 18
        if tick < 0:
            _rate = -_rate
        return _rate

if __name__ == '__main__':
    rate = TickMath.get_rate_at_tick(574, 2)
    print(rate)  # 59077837696286439
    rate = TickMath.get_rate_at_tick(-574, 2)
    print(rate)  # -59077837696286439
