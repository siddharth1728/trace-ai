# Case 3: Runtime Error - ZeroDivision on empty list
def calculate_class_average(scores):
    return sum(scores) / len(scores)

empty_scores = []
print("Average:", calculate_class_average(empty_scores))
