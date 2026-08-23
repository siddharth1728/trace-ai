# Benchmark Case 2: Runtime Error (ZeroDivisionError on empty score list)
def calculate_class_average(scores):
    # Bug: Directly dividing sum by len without handling empty list
    return sum(scores) / len(scores)

empty_scores = []
print("Average score:", calculate_class_average(empty_scores))
