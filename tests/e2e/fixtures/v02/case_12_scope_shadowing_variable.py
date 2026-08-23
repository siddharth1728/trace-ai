# Case 12: Scope Error - Local variable assignment before declaration
global_counter = 0

def increment_session_counter():
    # Bug: Local assignment without 'global' keyword raises UnboundLocalError
    global_counter = global_counter + 1
    return global_counter

print("Count:", increment_session_counter())
