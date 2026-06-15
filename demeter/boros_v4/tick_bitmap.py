from typing import Tuple, Optional
from ._typing import Side


class BitMath:
    """Python implementation of BitMath library"""

    @staticmethod
    def most_significant_bit(x: int) -> int:
        """
        Returns the index of the most significant bit (0-indexed from LSB).
        MSB is at index 255 for a 256-bit number.
        """
        if x == 0:
            raise ValueError("Input must be greater than 0")
        return x.bit_length() - 1

    @staticmethod
    def least_significant_bit(x: int) -> int:
        """
        Returns the index of the least significant bit (0-indexed from LSB).
        LSB is at index 0.
        """
        if x == 0:
            raise ValueError("Input must be greater than 0")
        return (x & -x).bit_length() - 1

    @staticmethod
    def keep_n_to_msb(mask: int, n: int) -> int:
        """
        Keep all bits from n (inclusive) to MSB and clear the rest.
        Equivalent to: (mask >> n) << n
        """
        return (mask >> n) << n

    @staticmethod
    def keep_n_to_lsb(mask: int, n: int) -> int:
        """
        Keep all bits from LSB to n (inclusive) and clear the rest.
        Equivalent to: (mask << (255 - n)) >> (255 - n) in 256-bit context
        """
        # In Python, we need to handle this differently since integers are arbitrary precision
        # We simulate 256-bit behavior
        inverted_n = 255 - n
        return ((mask << inverted_n) & ((1 << 256) - 1)) >> inverted_n


class TickBitmap:
    """
    Python implementation of TickBitmap struct.

    Uses a dictionary to simulate the storage behavior, where:
    - active_word_mask: tracks which words have active ticks
    - words: dictionary mapping word position to word value
    """

    def __init__(self):
        self.active_word_mask: int = 0
        self.words: dict[int, int] = {}  # Only store non-zero words

    def __repr__(self):
        active_ticks = self._get_all_active_ticks()
        return f"TickBitmap(active_ticks={active_ticks})"

    def _get_all_active_ticks(self) -> list:
        """Helper to get all active ticks for debugging"""
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
        """
        Convert signed tick index to word position and bit position.

        Args:
            i_tick: signed 16-bit tick index (-32768 to 32767)

        Returns:
            (word_pos, bit_pos): tuple of word position (0-255) and bit position (0-255)
        """
        # Convert signed int16 to unsigned uint16 representation
        # XOR with (1 << 15) maps:
        # -32768 -> 0, 0 -> 32768, 32767 -> 65535
        u_tick = (i_tick & 0xFFFF) ^ (1 << 15)
        word_pos = u_tick >> 8
        bit_pos = u_tick & 255
        return word_pos, bit_pos

    @staticmethod
    def pos_to_tick(word_pos: int, bit_pos: int) -> int:
        """
        Convert word position and bit position back to signed tick index.

        Args:
            word_pos: word position (0-255)
            bit_pos: bit position (0-255)

        Returns:
            signed 16-bit tick index
        """
        u_tick = (word_pos << 8) | bit_pos
        # XOR with (1 << 15) to convert back to signed representation
        i_tick = u_tick ^ (1 << 15)
        # Convert to signed int16
        if i_tick >= 32768:
            i_tick -= 65536
        return i_tick

    @staticmethod
    def get_word(bitmap: TickBitmap, word_pos: int) -> int:
        """Get the word value at the given position"""
        return bitmap.words.get(word_pos, 0)

    @staticmethod
    def set_word(bitmap: TickBitmap, word_pos: int, word: int) -> None:
        """Set the word value at the given position"""
        if word == 0:
            bitmap.words.pop(word_pos, None)
        else:
            bitmap.words[word_pos] = word

    @staticmethod
    def set(bitmap: TickBitmap, i_tick: int) -> None:
        """
        Set a tick as active (mark the corresponding bit as 1).

        Args:
            bitmap: TickBitmap instance
            i_tick: tick index to activate
        """
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        new_word = word | (1 << bit_pos)

        if word == new_word:
            return  # Already set

        TickBitmapLib.set_word(bitmap, word_pos, new_word)
        if word == 0:
            # Word was previously empty, update active_word_mask
            bitmap.active_word_mask |= (1 << word_pos)

    @staticmethod
    def reset(bitmap: TickBitmap, i_tick: int) -> None:
        """
        Reset a tick as inactive (mark the corresponding bit as 0).

        Args:
            bitmap: TickBitmap instance
            i_tick: tick index to deactivate
        """
        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        new_word = word & ~(1 << bit_pos)

        if word == new_word:
            return  # Already reset

        TickBitmapLib.set_word(bitmap, word_pos, new_word)
        if new_word == 0:
            # Word is now empty, update active_word_mask
            bitmap.active_word_mask &= ~(1 << word_pos)

    @staticmethod
    def find_greater_tick(bitmap: TickBitmap, i_tick: int) -> Tuple[Optional[int], bool]:
        """
        Find the smallest active tick that is greater than the given tick.

        Args:
            bitmap: TickBitmap instance
            i_tick: the tick to search from (exclusive)

        Returns:
            (next_tick, found): tuple of the found tick and whether it was found
        """
        if i_tick == 32767:  # type(int16).max
            return 0, False

        i_tick += 1  # Search from the next tick

        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        active_word_mask = bitmap.active_word_mask

        # Try to find in the same word
        if (active_word_mask & (1 << word_pos)) != 0:
            word = TickBitmapLib.get_word(bitmap, word_pos)
            masked_word = BitMath.keep_n_to_msb(word, bit_pos)
            if masked_word != 0:
                found_bit = BitMath.least_significant_bit(masked_word)
                return TickBitmapLib.pos_to_tick(word_pos, found_bit), True

        # Find next active word
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
        """
        Find the largest active tick that is less than the given tick.

        Args:
            bitmap: TickBitmap instance
            i_tick: the tick to search from (exclusive)

        Returns:
            (prev_tick, found): tuple of the found tick and whether it was found
        """
        if i_tick == -32768:  # type(int16).min
            return 0, False

        i_tick -= 1  # Search from the previous tick

        word_pos, bit_pos = TickBitmapLib.tick_to_pos(i_tick)
        active_word_mask = bitmap.active_word_mask

        # Try to find in the same word
        if (active_word_mask & (1 << word_pos)) != 0:
            word = TickBitmapLib.get_word(bitmap, word_pos)
            masked_word = BitMath.keep_n_to_lsb(word, bit_pos)
            if masked_word != 0:
                found_bit = BitMath.most_significant_bit(masked_word)
                return TickBitmapLib.pos_to_tick(word_pos, found_bit), True

        # Find previous active word
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
        """
        Find the lowest (smallest) active tick in the bitmap.

        Args:
            bitmap: TickBitmap instance

        Returns:
            (tick, found): tuple of the found tick and whether it was found
        """
        active = bitmap.active_word_mask
        if active == 0:
            return 0, False

        word_pos = BitMath.least_significant_bit(active)
        word = TickBitmapLib.get_word(bitmap, word_pos)
        bit_pos = BitMath.least_significant_bit(word)
        # 100000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

        return TickBitmapLib.pos_to_tick(word_pos, bit_pos), True

    @staticmethod
    def find_highest_tick(bitmap: TickBitmap) -> Tuple[Optional[int], bool]:
        """
        Find the highest (largest) active tick in the bitmap.

        Args:
            bitmap: TickBitmap instance

        Returns:
            (tick, found): tuple of the found tick and whether it was found
        """
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
        """
        Get the starting tick for iteration based on the side.

        Args:
            bitmap: TickBitmap instance
            side: LONG or SHORT

        Returns:
            (tick, found): tuple of the starting tick and whether it was found
        """
        if side.sweep_tick_top_down():
            # LONG: sweep from high to low, start from highest tick
            return TickBitmapLib.find_highest_tick(bitmap)
        else:
            # SHORT: sweep from low to high, start from lowest tick
            return TickBitmapLib.find_lowest_tick(bitmap)

    @staticmethod
    def next(bitmap: TickBitmap, i_tick: int, side: Side) -> Tuple[Optional[int], bool]:
        """
        Get the next tick for iteration based on the side.

        Args:
            bitmap: TickBitmap instance
            i_tick: current tick
            side: LONG or SHORT

        Returns:
            (tick, found): tuple of the next tick and whether it was found
        """
        if side.sweep_tick_top_down():
            # LONG: sweep from high to low, find lower tick
            return TickBitmapLib.find_less_tick(bitmap, i_tick)
        else:
            # SHORT: sweep from low to high, find higher tick
            return TickBitmapLib.find_greater_tick(bitmap, i_tick)
