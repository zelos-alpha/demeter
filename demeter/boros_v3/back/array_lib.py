"""
ArrayLib Python Implementation
Array utility library based on contracts/lib/ArrayLib.sol
"""

from typing import List, Tuple, Any


class ArrayLib:
    """Array utility functions."""
    
    @staticmethod
    def find(arr: List[Any], item: Any) -> int:
        """
        Find the index of the first element equal to item.
        Returns len(arr) if no element is equal to item.
        """
        for i in range(len(arr)):
            if arr[i] == item:
                return i
        return len(arr)
    
    @staticmethod
    def include(arr: List[Any], item: Any) -> bool:
        """
        Check if item exists in the array.
        """
        for i in range(len(arr)):
            if arr[i] == item:
                return True
        return False
    
    @staticmethod
    def remove(arr: List[Any], item: Any) -> bool:
        """
        Remove item from array (assumes no duplicates).
        Returns True if item was found and removed.
        """
        for i in range(len(arr)):
            if arr[i] == item:
                # Swap with last element
                arr[i] = arr[-1]
                # Remove last element (pop)
                arr.pop()
                return True
        return False
    
    @staticmethod
    def reverse(arr: List[Any], l: int, r: int) -> None:
        """
        Reverse elements in array from index l to r (inclusive).
        """
        while l < r:
            arr[l], arr[r] = arr[r], arr[l]
            l += 1
            r -= 1
    
    @staticmethod
    def sum_uint(arr: List[int]) -> int:
        """
        Sum all elements in uint256 array.
        """
        total = 0
        for i in range(len(arr)):
            total += arr[i]
        return total
    
    @staticmethod
    def sum_uint_range(arr: List[int], start: int, end: int) -> int:
        """
        Sum elements in uint256 array from start (inclusive) to end (exclusive).
        """
        total = 0
        for i in range(start, end):
            total += arr[i]
        return total
    
    @staticmethod
    def extend(arr: List[Any], n: int) -> List[Any]:
        """
        Extend array by n elements (uninitialized).
        Returns new array with original elements plus n new slots.
        """
        # Create new array with additional slots (filled with None/uninitialized)
        new_arr = arr.copy()
        for _ in range(n):
            new_arr.append(None)
        return new_arr
    
    @staticmethod
    def concat(arr1: List[Any], arr2: List[Any]) -> List[Any]:
        """
        Concatenate two arrays.
        Returns new array with elements from both arrays.
        """
        return arr1 + arr2


class LowLevelArrayLib:
    """Low-level array manipulation functions."""
    
    @staticmethod
    def slice_from_temp(orig: List[Any], from_idx: int) -> Tuple[List[Any], Any]:
        """
        Create a slice of array from index 'from' to end.
        Returns (slice, borrow) where borrow is the original first element of slice.
        """
        slice_len = len(orig) - from_idx
        
        # Create slice starting from from_idx
        new_slice = orig[from_idx:]
        
        # Store borrow (original first element of slice)
        borrow = orig[from_idx] if from_idx < len(orig) else None
        
        return (new_slice, borrow)
    
    @staticmethod
    def restore_slice(slice_arr: List[Any], borrow: Any) -> None:
        """
        Restore the original first element of a slice.
        """
        if slice_arr and borrow is not None:
            slice_arr[0] = borrow
    
    @staticmethod
    def set_shorter_length(arr: List[Any], new_length: int) -> None:
        """
        Set array length to new_length (truncates or extends).
        """
        current_len = len(arr)
        if new_length < current_len:
            # Truncate
            del arr[new_length:]
        elif new_length > current_len:
            # Extend with None
            for _ in range(new_length - current_len):
                arr.append(None)
    
    @staticmethod
    def alloc_array_no_init(length: int) -> List[Any]:
        """
        Allocate an uninitialized array of specified length.
        Returns array filled with None values.
        """
        return [None] * length
