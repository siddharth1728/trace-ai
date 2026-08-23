# Benchmark Case 5: Input Validation Bug (Unhandled empty string or negative input)
def calculate_grade_percentage(score, max_score):
    # Bug: Unhandled zero / negative score or empty inputs
    if score is None or max_score is None:
        raise ValueError("Scores cannot be None")
    return (score / max_score) * 100

print(calculate_grade_percentage(0, 0))
