# Case 13: Edge Case - Whitespace string vs empty string
def parse_cleaned_username(raw_input):
    if raw_input == "":
        raise ValueError("Username cannot be empty")
    # Bug: Whitespace string "   " passes == "" check but is invalid after strip()
    first_char = raw_input.strip()[0]
    return first_char.upper()

print("Initial:", parse_cleaned_username("   "))
