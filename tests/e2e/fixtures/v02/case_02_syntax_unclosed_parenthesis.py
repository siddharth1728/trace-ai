# Case 2: Syntax Error - Unclosed parenthesis in multi-line call
def generate_report(user_id, status, score):
    return f"User {user_id}: {status} with score {score}"

result = generate_report(
    101,
    "PASSED",
    95.5
print("Report Result:", result)
