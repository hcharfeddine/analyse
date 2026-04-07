participants = 10  # active
pending_status = [True] * participants  # True=active

def pending_battles(active_count):
    """Number of battles in current round, with byes if odd."""
    return active_count // 2

def toggle_pending(index):
    pending_status[index] = not pending_status[index]

# Initial
active = sum(pending_status)
print(f"Active: {active}, Pending battles: {pending_battles(active)}")  # 10, 5

# Toggle one to pending
toggle_pending(0)
active = sum(pending_status)
print(f"Active: {active}, Pending battles: {pending_battles(active)}")  # 9, 4

# Toggle back
toggle_pending(0)
active = sum(pending_status)
print(f"Active: {active}, Pending battles: {pending_battles(active)}")  # 10, 5 - updates!

# Total battles to 1 winner: always active - 1
print(f"Total battles to winner: {active - 1}")
