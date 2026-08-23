# Benchmark Case 4: Logic Error (Off-by-one or indexing error)
def get_nth_element(items, n):
    # Bug: Using n instead of n-1 for 1-based nth element lookup on a list
    if n > len(items):
        return None
    return items[n]  # Raises IndexError when n == len(items)

numbers = [10, 20, 30, 40, 50]
# User asks for 5th element, expecting 50
print("5th element:", get_nth_element(numbers, 5))
