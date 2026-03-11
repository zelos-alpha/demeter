from ._typing import Side


class SideLib:
    """Library for side operations"""

    @staticmethod
    def to_signed_size(size: int, side: Side) -> int:
        """Convert unsigned size to signed based on side"""
        return size if side == Side.LONG else -size
