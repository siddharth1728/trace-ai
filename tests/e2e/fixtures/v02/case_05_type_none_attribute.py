# Case 5: Type Error - NoneType attribute invocation
def format_user_display_name(user_record):
    raw_name = user_record.get("name")
    return raw_name.upper()

guest_user = {"id": 101, "name": None, "role": "guest"}
print("Display Name:", format_user_display_name(guest_user))
