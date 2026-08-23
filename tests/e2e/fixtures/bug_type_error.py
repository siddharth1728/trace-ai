# Benchmark Case 3: Type Error (NoneType operation when parsing profile)
def format_user_display_name(user_record):
    # Bug: user_record["name"] may be None, causing TypeError on .upper()
    raw_name = user_record.get("name")
    return raw_name.upper()

guest_user = {"id": 101, "name": None, "role": "guest"}
print("Display Name:", format_user_display_name(guest_user))
