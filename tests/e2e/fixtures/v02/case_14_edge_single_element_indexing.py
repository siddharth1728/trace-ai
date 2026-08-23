# Case 14: Edge Case - Single element list indexing
def get_second_highest_score(scores):
    sorted_scores = sorted(scores, reverse=True)
    # Bug: When len(scores) == 1, accessing index 1 raises IndexError
    return sorted_scores[1]

print("Second Highest:", get_second_highest_score([98.5]))
