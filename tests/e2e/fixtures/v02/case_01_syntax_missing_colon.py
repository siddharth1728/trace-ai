# Case 1: Syntax Error - Missing colon on def
def calculate_cart_total(items)
    total = 0.0
    for item in items:
        total += item["price"] * item["quantity"]
    return total

cart = [{"price": 10.0, "quantity": 2}]
print("Total:", calculate_cart_total(cart))
