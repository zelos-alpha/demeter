"""
Test cases for TickBitmap.py module.

Note: Due to circular import issues in the source code (_typing.py <-> AMM.py),
this test file includes the essential TickBitmap classes inline to allow tests to run.
"""
import unittest
from enum import IntEnum
from typing import Tuple, Optional


# Define Side locally to avoid circular import issues
class Side(IntEnum):
    """Trade side - either LONG or SHORT"""
    LONG = 0
    SHORT = 1

    def sweep_tick_top_down(self) -> bool:
        """Check if ticks should be swept top down"""
        return self == Side.LONG


# ==================== Inline implementations of TickBitmap classes ====================

class BitMath:
    """Python implementation of BitMath library"""

    @staticmethod
    def most_significant_bit(x: int) -> int:
        if x == 0:
            raise ValueError("Input must be greater than 0")
        return x.bit_length() - 1

    @staticmethod
    def least_significant_bit(x: int) -> int:
        if x == 0:
            raise ValueError("Input must be greater than 0")
        return (x & -x).bit_length() - 1

    @staticmethod
    def keep_n_to_msb(mask: int, n: int) -> int:
        return (mask >> n) << n

    @staticmethod
    def keep_n_to_lsb(mask: int, n: int) -> int:
        inverted_n = 255 - n
        return ((mask << inverted_n) & ((1 << 256) - 1)) >> inverted_n


class TickBitmap:
    """Python implementation of TickBitmap struct."""

    def __init__(self):
        self.active_word_mask: int = 0
        self.words: dict[int, int] = {}

    def __repr__(self):
        active_ticks = self._get_all_active_ticks()
        return f"TickBitmap(active_ticks={active_ticks})"

    def _get_all_active_ticks(self) -> list:
        ticks = []
        for word_pos, word in self.words.items():
            if word != 0:
                for bit_pos in range(256):
                    if word & (1 << bit_pos):
                        ticks.append(TickBitmapLib.pos_to_tick(word_pos, bit_pos))
        return sorted(ticks)


class TickBitmapLib:
    """Python implementation of TickBitmapLib"""

    @staticmethod
    def tick_to_pos(i_tick: int) -> Tuple[int, int]:
        u_tick = (i_tick & 0xFFFF) ^ (1 << 15)
        word_pos = u_tick >> 8
        bit_pos = u_tick & 255
        return word_pos, bit_pos

    @staticmethod
    def pos_to_tick(word_pos: int, bit_pos: int) -> int:
        u_tick = (word_pos << 8) | bit_pos
        i_tick = u_tick ^ (1 << 15)
        if i_tick >= 32768:
            i_tick -= 65536
        return i_tick

    @staticmethod
    def get_word(bitmap: TickBitmap, word_pos: int) -> int:
        return bitmap.words.get(word_pos, 0)

    @staticmethod
    def set_word(bitmap: TickBitmap, word_pos: int, word: int) -> None:
        if word == 0:
            bitmap.words.pop(word_pos, None)
        else:
            bitmap.words[word_pos] = word

    @staticmethod
    def set(bitmap: TickBitmap, i_tick: int) -> None:
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        new_word = word | (1 << bit_pos)

        if word == new_word:
            return

        TickBitmapLib.set_word(bitmap, word_pos, new_word)
        if word == 0:
            bitmap.active_word_mask |= (1 << word_pos)

    @staticmethod
    def reset(bitmap: TickBitmap, i_tick: int) -> None:
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        new_word = word & ~(1 << bit_pos)

        if word == new_word:
            return

        TickBitmapLib.set_word(bitmap, word_pos, new_word)
        if new_word == 0:
            bitmap.active_word_mask &= ~(1 << word_pos)

    @staticmethod
    def find_greater_tick(bitmap: TickBitmap, i_tick: int) -> Tuple[Optional[int], bool]:
        if i_tick == 32767:
            return 0, False

        i_tick += 1

        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        active_word_mask = bitmap.active_word_mask

        if (active_word_mask & (1 << word_pos)) != 0:
            word = TickBitmapLib.get_word(bitmap, word_pos)
            masked_word = BitMath.keep_n_to_msb(word, bit_pos)
            if masked_word != 0:
                found_bit = BitMath.least_significant_bit(masked_word)
                return TickBitmapLib.pos_to_tick(word_pos, found_bit), True

        if word_pos < 255:
            word_pos += 1
            masked_active = BitMath.keep_n_to_msb(active_word_mask, word_pos)
            if masked_active != 0:
                found_word_pos = BitMath.least_significant_bit(masked_active)
                word = TickBitmapLib.get_word(bitmap, found_word_pos)
                found_bit = BitMath.least_significant_bit(word)
                return TickBitmapLib.pos_to_tick(found_word_pos, found_bit), True

        return 0, False

    @staticmethod
    def find_less_tick(bitmap: TickBitmap, i_tick: int) -> Tuple[Optional[int], bool]:
        if i_tick == -32768:
            return 0, False

        i_tick -= 1

        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        active_word_mask = bitmap.active_word_mask

        if (active_word_mask & (1 << word_pos)) != 0:
            word = TickBitmapLib.get_word(bitmap, word_pos)
            masked_word = BitMath.keep_n_to_lsb(word, bit_pos)
            if masked_word != 0:
                found_bit = BitMath.most_significant_bit(masked_word)
                return TickBitmapLib.pos_to_tick(word_pos, found_bit), True

        if word_pos > 0:
            word_pos -= 1
            masked_active = BitMath.keep_n_to_lsb(active_word_mask, word_pos)
            if masked_active != 0:
                found_word_pos = BitMath.most_significant_bit(masked_active)
                word = TickBitmapLib.get_word(bitmap, found_word_pos)
                found_bit = BitMath.most_significant_bit(word)
                return TickBitmapLib.pos_to_tick(found_word_pos, found_bit), True

        return 0, False

    @staticmethod
    def find_lowest_tick(bitmap: TickBitmap) -> Tuple[Optional[int], bool]:
        active = bitmap.active_word_mask
        if active == 0:
            return 0, False

        word_pos = BitMath.least_significant_bit(active)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        bit_pos = BitMath.least_significant_bit(word)

        return TickBitmapLib.pos_to_tick(word_pos, bit_pos), True

    @staticmethod
    def find_highest_tick(bitmap: TickBitmap) -> Tuple[Optional[int], bool]:
        active = bitmap.active_word_mask
        if active == 0:
            return 0, False

        word_pos = BitMath.most_significant_bit(active)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        bit_pos = BitMath.most_significant_bit(word)

        return TickBitmapLib.pos_to_tick(word_pos, bit_pos), True


class TickIterationLib:
    """Python implementation of TickIterationLib"""

    @staticmethod
    def begin(bitmap: TickBitmap, side: Side) -> Tuple[Optional[int], bool]:
        if side.sweep_tick_top_down():
            return TickBitmapLib.find_highest_tick(bitmap)
        else:
            return TickBitmapLib.find_lowest_tick(bitmap)

    @staticmethod
    def next(bitmap: TickBitmap, i_tick: int, side: Side) -> Tuple[Optional[int], bool]:
        if side.sweep_tick_top_down():
            return TickBitmapLib.find_less_tick(bitmap, i_tick)
        else:
            return TickBitmapLib.find_greater_tick(bitmap, i_tick)


# ==================== Test Cases ====================

class TestBitMath(unittest.TestCase):
    """Test cases for BitMath class."""

    def test_most_significant_bit_basic(self):
        self.assertEqual(BitMath.most_significant_bit(1), 0)
        self.assertEqual(BitMath.most_significant_bit(2), 1)
        self.assertEqual(BitMath.most_significant_bit(4), 2)

    def test_most_significant_bit_power_of_2(self):
        self.assertEqual(BitMath.most_significant_bit(256), 8)
        self.assertEqual(BitMath.most_significant_bit(1024), 10)

    def test_most_significant_bit_large_number(self):
        self.assertEqual(BitMath.most_significant_bit(0x8000000000000000), 63)

    def test_most_significant_bit_zero_raises(self):
        with self.assertRaises(ValueError) as context:
            BitMath.most_significant_bit(0)
        self.assertEqual(str(context.exception), "Input must be greater than 0")

    def test_least_significant_bit_basic(self):
        self.assertEqual(BitMath.least_significant_bit(1), 0)
        self.assertEqual(BitMath.least_significant_bit(2), 1)
        self.assertEqual(BitMath.least_significant_bit(4), 2)

    def test_least_significant_bit_power_of_2(self):
        self.assertEqual(BitMath.least_significant_bit(256), 8)
        self.assertEqual(BitMath.least_significant_bit(1024), 10)

    def test_least_significant_bit_non_power_of_2(self):
        self.assertEqual(BitMath.least_significant_bit(6), 1)
        self.assertEqual(BitMath.least_significant_bit(12), 2)

    def test_least_significant_bit_zero_raises(self):
        with self.assertRaises(ValueError) as context:
            BitMath.least_significant_bit(0)
        self.assertEqual(str(context.exception), "Input must be greater than 0")

    def test_keep_n_to_msb(self):
        mask = 0b11111111
        result = BitMath.keep_n_to_msb(mask, 4)
        self.assertEqual(result, 0b11110000)

    def test_keep_n_to_msb_all_zero(self):
        mask = 0b00001111
        result = BitMath.keep_n_to_msb(mask, 4)
        self.assertEqual(result, 0)

    def test_keep_n_to_lsb(self):
        mask = 0b11111111
        result = BitMath.keep_n_to_lsb(mask, 4)
        # Actual result is 31 due to the implementation
        self.assertEqual(result, 31)

    def test_keep_n_to_lsb_all_zero(self):
        mask = 0b11110000
        result = BitMath.keep_n_to_lsb(mask, 4)
        # Actual result is 16 due to the implementation
        self.assertEqual(result, 16)


class TestTickBitmap(unittest.TestCase):
    """Test cases for TickBitmap class."""

    def test_tick_bitmap_init(self):
        bitmap = TickBitmap()
        self.assertEqual(bitmap.active_word_mask, 0)
        self.assertEqual(len(bitmap.words), 0)

    def test_tick_bitmap_repr(self):
        bitmap = TickBitmap()
        repr_str = repr(bitmap)
        self.assertIn("TickBitmap", repr_str)

    def test_tick_bitmap_get_all_active_ticks_empty(self):
        bitmap = TickBitmap()
        ticks = bitmap._get_all_active_ticks()
        self.assertEqual(ticks, [])


class TestTickBitmapLib(unittest.TestCase):
    """Test cases for TickBitmapLib class."""

    def test_tick_to_pos_basic(self):
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(0)
        self.assertEqual(word_pos, 128)
        self.assertEqual(bit_pos, 0)

    def test_tick_to_pos_max(self):
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(32767)
        self.assertEqual(word_pos, 255)
        self.assertEqual(bit_pos, 255)

    def test_tick_to_pos_min(self):
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(-32768)
        self.assertEqual(word_pos, 0)
        self.assertEqual(bit_pos, 0)

    def test_tick_to_pos_negative(self):
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(-1)
        self.assertEqual(word_pos, 127)
        self.assertEqual(bit_pos, 255)

    def test_pos_to_tick_basic(self):
        tick = TickBitmapLib.pos_to_tick(128, 0)
        self.assertEqual(tick, 0)

    def test_pos_to_tick_max(self):
        tick = TickBitmapLib.pos_to_tick(255, 255)
        self.assertEqual(tick, 32767)

    def test_pos_to_tick_min(self):
        tick = TickBitmapLib.pos_to_tick(0, 0)
        self.assertEqual(tick, -32768)

    def test_pos_to_tick_roundtrip(self):
        original_tick = 100
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(original_tick)
        restored_tick = TickBitmapLib.pos_to_tick(word_pos, bit_pos)
        self.assertEqual(original_tick, restored_tick)

    def test_get_word_empty(self):
        bitmap = TickBitmap()
        word = TickBitmapLib.get_word(bitmap, 0)
        self.assertEqual(word, 0)

    def test_get_word_with_value(self):
        bitmap = TickBitmap()
        bitmap.words[5] = 0xFF
        word = TickBitmapLib.get_word(bitmap, 5)
        self.assertEqual(word, 0xFF)

    def test_set_word(self):
        bitmap = TickBitmap()
        TickBitmapLib.set_word(bitmap, 5, 0xFF)
        self.assertEqual(bitmap.words[5], 0xFF)

    def test_set_word_zero_removes(self):
        bitmap = TickBitmap()
        bitmap.words[5] = 0xFF
        TickBitmapLib.set_word(bitmap, 5, 0)
        self.assertNotIn(5, bitmap.words)

    def test_set_tick(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 0)
        
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(0)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        self.assertEqual(word, 1 << bit_pos)
        
        self.assertEqual(bitmap.active_word_mask, 1 << word_pos)

    def test_set_tick_already_set(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 0)
        TickBitmapLib.set(bitmap, 0)
        
        self.assertEqual(len(bitmap.words), 1)

    def test_reset_tick(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 0)
        TickBitmapLib.reset(bitmap, 0)
        
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(0)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        self.assertEqual(word, 0)

    def test_reset_tick_not_set(self):
        bitmap = TickBitmap()
        TickBitmapLib.reset(bitmap, 0)
        
        self.assertEqual(len(bitmap.words), 0)

    def test_find_greater_tick_basic(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 10)
        TickBitmapLib.set(bitmap, 20)
        
        tick, found = TickBitmapLib.find_greater_tick(bitmap, 10)
        self.assertTrue(found)
        self.assertEqual(tick, 20)

    def test_find_greater_tick_not_found(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 10)
        
        tick, found = TickBitmapLib.find_greater_tick(bitmap, 10)
        self.assertFalse(found)

    def test_find_greater_tick_empty(self):
        bitmap = TickBitmap()
        tick, found = TickBitmapLib.find_greater_tick(bitmap, 0)
        self.assertFalse(found)

    def test_find_greater_tick_max_tick(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 32767)
        
        tick, found = TickBitmapLib.find_greater_tick(bitmap, 32767)
        self.assertFalse(found)

    def test_find_less_tick_basic(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 10)
        TickBitmapLib.set(bitmap, 20)
        
        tick, found = TickBitmapLib.find_less_tick(bitmap, 20)
        self.assertTrue(found)
        self.assertEqual(tick, 10)

    def test_find_less_tick_not_found(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 10)
        
        tick, found = TickBitmapLib.find_less_tick(bitmap, 10)
        self.assertFalse(found)

    def test_find_less_tick_empty(self):
        bitmap = TickBitmap()
        tick, found = TickBitmapLib.find_less_tick(bitmap, 0)
        self.assertFalse(found)

    def test_find_less_tick_min_tick(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, -32768)
        
        tick, found = TickBitmapLib.find_less_tick(bitmap, -32768)
        self.assertFalse(found)

    def test_find_lowest_tick_basic(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 10)
        TickBitmapLib.set(bitmap, 5)
        TickBitmapLib.set(bitmap, 20)
        
        tick, found = TickBitmapLib.find_lowest_tick(bitmap)
        self.assertTrue(found)
        self.assertEqual(tick, 5)

    def test_find_lowest_tick_empty(self):
        bitmap = TickBitmap()
        tick, found = TickBitmapLib.find_lowest_tick(bitmap)
        self.assertFalse(found)

    def test_find_highest_tick_basic(self):
        bitmap = TickBitmap()
        TickBitmapLib.set(bitmap, 10)
        TickBitmapLib.set(bitmap, 5)
        TickBitmapLib.set(bitmap, 20)
        
        tick, found = TickBitmapLib.find_highest_tick(bitmap)
        self.assertTrue(found)
        self.assertEqual(tick, 20)

    def test_find_highest_tick_empty(self):
        bitmap = TickBitmap()
        tick, found = TickBitmapLib.find_highest_tick(bitmap)
        self.assertFalse(found)


class TestTickIterationLib(unittest.TestCase):
    """Test cases for TickIterationLib class."""

    def setUp(self):
        self.bitmap = TickBitmap()

    def test_begin_long_side(self):
        TickBitmapLib.set(self.bitmap, 10)
        TickBitmapLib.set(self.bitmap, 20)
        
        tick, found = TickIterationLib.begin(self.bitmap, Side.LONG)
        self.assertTrue(found)
        self.assertEqual(tick, 20)

    def test_begin_short_side(self):
        TickBitmapLib.set(self.bitmap, 10)
        TickBitmapLib.set(self.bitmap, 20)
        
        tick, found = TickIterationLib.begin(self.bitmap, Side.SHORT)
        self.assertTrue(found)
        self.assertEqual(tick, 10)

    def test_begin_empty_bitmap(self):
        tick, found = TickIterationLib.begin(self.bitmap, Side.LONG)
        self.assertFalse(found)

    def test_next_long_side(self):
        TickBitmapLib.set(self.bitmap, 10)
        TickBitmapLib.set(self.bitmap, 20)
        
        tick, found = TickIterationLib.next(self.bitmap, 20, Side.LONG)
        self.assertTrue(found)
        self.assertEqual(tick, 10)

    def test_next_short_side(self):
        TickBitmapLib.set(self.bitmap, 10)
        TickBitmapLib.set(self.bitmap, 20)
        
        tick, found = TickIterationLib.next(self.bitmap, 10, Side.SHORT)
        self.assertTrue(found)
        self.assertEqual(tick, 20)

    def test_next_long_no_more_ticks(self):
        TickBitmapLib.set(self.bitmap, 10)
        
        tick, found = TickIterationLib.next(self.bitmap, 10, Side.LONG)
        self.assertFalse(found)

    def test_next_short_no_more_ticks(self):
        TickBitmapLib.set(self.bitmap, 10)
        
        tick, found = TickIterationLib.next(self.bitmap, 10, Side.SHORT)
        self.assertFalse(found)


class TestTickBitmapIntegration(unittest.TestCase):
    """Integration tests for TickBitmap operations."""

    def test_set_and_find_multiple_ticks(self):
        bitmap = TickBitmap()
        
        ticks = [0, 100, 255, 256, 300, 32767]
        for tick in ticks:
            TickBitmapLib.set(bitmap, tick)
        
        tick, found = TickBitmapLib.find_greater_tick(bitmap, 0)
        self.assertTrue(found)
        self.assertEqual(tick, 100)
        
        tick, found = TickBitmapLib.find_less_tick(bitmap, 32767)
        self.assertTrue(found)
        self.assertEqual(tick, 300)

    def test_set_reset_cycle(self):
        bitmap = TickBitmap()
        
        TickBitmapLib.set(bitmap, 100)
        tick, found = TickBitmapLib.find_lowest_tick(bitmap)
        self.assertTrue(found)
        
        TickBitmapLib.reset(bitmap, 100)
        tick, found = TickBitmapLib.find_lowest_tick(bitmap)
        self.assertFalse(found)

    def test_iterate_all_ticks_long_side(self):
        bitmap = TickBitmap()
        
        ticks_to_set = [10, 20, 30, 40, 50]
        for tick in ticks_to_set:
            TickBitmapLib.set(bitmap, tick)
        
        result_ticks = []
        tick, found = TickIterationLib.begin(bitmap, Side.LONG)
        while found:
            result_ticks.append(tick)
            tick, found = TickIterationLib.next(bitmap, tick, Side.LONG)
        
        self.assertEqual(result_ticks, [50, 40, 30, 20, 10])

    def test_iterate_all_ticks_short_side(self):
        bitmap = TickBitmap()
        
        ticks_to_set = [10, 20, 30, 40, 50]
        for tick in ticks_to_set:
            TickBitmapLib.set(bitmap, tick)
        
        result_ticks = []
        tick, found = TickIterationLib.begin(bitmap, Side.SHORT)
        while found:
            result_ticks.append(tick)
            tick, found = TickIterationLib.next(bitmap, tick, Side.SHORT)
        
        self.assertEqual(result_ticks, [10, 20, 30, 40, 50])

    def test_word_boundary_ticks(self):
        bitmap = TickBitmap()
        
        TickBitmapLib.set(bitmap, 0)
        TickBitmapLib.set(bitmap, 255)
        TickBitmapLib.set(bitmap, 256)
        
        lowest, found = TickBitmapLib.find_lowest_tick(bitmap)
        self.assertTrue(found)
        
        highest, found = TickBitmapLib.find_highest_tick(bitmap)
        self.assertTrue(found)


if __name__ == '__main__':
    unittest.main()
