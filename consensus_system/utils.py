"""
Utility functions for the consensus system.
"""

from typing import Any, List, Optional, Dict


def calculate_majority_vote(values: List[Any]) -> Optional[Any]:
    """
    Calculate the majority vote from a list of values.
    
    Handles both hashable and unhashable values (like dicts or lists) 
    efficiently while maintaining consistent tie-breaking (first occurrence wins).
    
    Args:
        values: List of values to count
        
    Returns:
        The value with the highest count, or None if the input list is empty or contains only None.
    """
    if not values:
        return None

    # Filter out None values
    valid_values = [v for v in values if v is not None]
    if not valid_values:
        return None

    # Use a two-pronged approach for efficiency:
    # 1. Dictionary for hashable values (O(N))
    # 2. List of [value, count] for unhashable values (O(N*M) where M is number of unique unhashable)
    
    hashable_counts: Dict[Any, int] = {}
    unhashable_counts: List[List[Any]] = [] # Each element is [value, count, first_index]
    
    # Track first appearance index for tie-breaking
    first_appearance: Dict[Any, int] = {} 
    
    for i, val in enumerate(valid_values):
        try:
            # Try to use it as a hash key
            if val not in hashable_counts:
                hashable_counts[val] = 1
                first_appearance[val] = i
            else:
                hashable_counts[val] += 1
        except TypeError:
            # Handle unhashable values (dicts, lists, etc.)
            found = False
            for item in unhashable_counts:
                if item[0] == val:
                    item[1] += 1
                    found = True
                    break
            if not found:
                unhashable_counts.append([val, 1, i])

    # Find the winner
    winner_val = None
    max_count = -1
    earliest_index = float('inf')

    # Check hashable counts
    for val, count in hashable_counts.items():
        index = first_appearance[val]
        if count > max_count:
            max_count = count
            winner_val = val
            earliest_index = index
        elif count == max_count and index < earliest_index:
            winner_val = val
            earliest_index = index

    # Check unhashable counts
    for item in unhashable_counts:
        val, count, index = item[0], item[1], item[2]
        if count > max_count:
            max_count = count
            winner_val = val
            earliest_index = index
        elif count == max_count and index < earliest_index:
            winner_val = val
            earliest_index = index

    return winner_val
