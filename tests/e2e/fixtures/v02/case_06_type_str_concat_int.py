# Case 6: Type Error - String concatenation with integer
def calculate_invoice_total(subtotal, tax_str):
    # Bug: tax_str is a string like "10" instead of float, causing TypeError on +
    return subtotal + tax_str

print("Invoice:", calculate_invoice_total(100.0, "10"))
