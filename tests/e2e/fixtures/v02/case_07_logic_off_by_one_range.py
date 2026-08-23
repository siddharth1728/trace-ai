# Case 7: Logic Error - Off-by-one in loop range
def get_last_element(items):
    # Bug: range(len(items) + 1) iterates to index len(items), raising IndexError
    last = None
    for i in range(len(items) + 1):
        last = items[i]
    return last

items = ["alpha", "beta", "gamma"]
print("Last:", get_last_element(items))
