# Case 8: Logic Error - Accumulator reset inside loop
def sum_positive_numbers(numbers):
    for n in numbers:
        # Bug: total = 0 inside loop resets accumulator on every iteration
        total = 0
        if n > 0:
            total += n
    return total

print("Sum:", sum_positive_numbers([10, 20, 30]))
