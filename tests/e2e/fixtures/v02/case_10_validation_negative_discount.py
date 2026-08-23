# Case 10: Input Validation - Unhandled negative discount
def calculate_discounted_price(price, discount_percent):
    if discount_percent > 100:
        raise ValueError("Discount cannot exceed 100%")
    # Bug: Negative discount_percent increases the price instead of throwing validation error
    return price * (1 - discount_percent / 100)

print("Discounted Price:", calculate_discounted_price(100.0, -25.0))
