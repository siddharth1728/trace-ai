# Case 4: Misleading Symptom - ZeroDivisionError despite non-empty list
# The list is NOT empty ([10.0, 10.0]), but the spread (max - min) is 0!
def normalize_score(score, all_scores):
    min_s = min(all_scores)
    max_s = max(all_scores)
    # Bug: When all scores are identical, max_s - min_s is 0, causing ZeroDivisionError
    return (score - min_s) / (max_s - min_s)

student_scores = [10.0, 10.0]
print("Normalized:", normalize_score(10.0, student_scores))
