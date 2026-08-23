# Case 15: Call Hierarchy - Helper function failure called from multiple paths
def _internal_divider(a, b):
    return a / b

def process_batch(items):
    results = []
    for item in items:
        # Bug: passes divisor 0 when item['divisor'] is missing or 0
        divisor = item.get("divisor", 0)
        results.append(_internal_divider(item["val"], divisor))
    return results

batch = [{"val": 100, "divisor": 0}]
print("Batch:", process_batch(batch))
