
import json

def _parse_paginated_json(output: str):
    # Use a bracket-balancing approach to find each JSON array
    items = []
    depth = 0
    start = None
    parse_errors = 0
    for i, char in enumerate(output):
        if char == '[':
            if depth == 0:
                start = i
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    arr = json.loads(output[start:i+1])
                    if isinstance(arr, list):
                        items.extend(arr)
                except json.JSONDecodeError:
                    parse_errors += 1
                start = None
    
    return items, parse_errors

# Test case 1: Nested brackets in strings
test1 = '[{"message": "here is a bracket ["}]'
items1, errors1 = _parse_paginated_json(test1)
print(f"Test 1: {test1}")
print(f"Items: {items1}, Errors: {errors1}")

# Test case 2: Concatenated arrays
test2 = '[{"id": 1}][{"id": 2}]'
items2, errors2 = _parse_paginated_json(test2)
print(f"Test 2: {test2}")
print(f"Items: {items2}, Errors: {errors2}")

# Test case 3: Closing bracket in string
test3 = '[{"message": "closing ]"}]'
items3, errors3 = _parse_paginated_json(test3)
print(f"Test 3: {test3}")
print(f"Items: {items3}, Errors: {errors3}")
