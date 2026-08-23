# Case 11: Scope Error - Variable declared inside conditional branch
def determine_membership_tier(points):
    if points > 1000:
        tier_label = "PLATINUM"
    elif points > 500:
        tier_label = "GOLD"
    # Bug: When points <= 500, tier_label is never assigned, causing UnboundLocalError / NameError
    return tier_label

print("Tier:", determine_membership_tier(200))
