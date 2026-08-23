# Benchmark Case 1: Syntax Error (Missing colon on function definition)
def calculate_cart_total(items)
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]
    return total

cart = [
    {"price": 10.0, "quantity": 2},
    {"price": 5.5, "quantity": 1}
]
print(calculate_cart_total(cart))
