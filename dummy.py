# populate_dummy_data.py

import bcrypt
from google.cloud import firestore
import datetime


# Initialize Firestore Client
def init_firestore():
    return firestore.Client.from_service_account_json("firestore_credentials.json")


db = init_firestore()


# Password Hashing
def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


# Create Users
def create_user(username, email, password):
    users_ref = db.collection("users")
    # Check if user already exists using keyword arguments
    query = (
        users_ref.where(field_path="username", op_string="==", value=username)
        .limit(1)
        .stream()
    )
    if any(True for _ in query):
        print(f"User '{username}' already exists. Skipping creation.")
        return None
    # Hash the password
    password_hashed = hash_password(password)
    # Create user document with last_recitation_time initialized to None
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": password_hashed,
        "created_at": datetime.datetime.utcnow(),
        "last_recitation_time": None,  # Initialize as None
    }
    user_ref = users_ref.add(user_doc)
    print(f"User '{username}' created with ID: {user_ref[1].id}")
    return user_ref[1].id


# Create Friendship
def create_friendship(user1_id, user2_id):
    friendships_ref = db.collection("friendships")
    # Check if friendship already exists using keyword arguments
    query = (
        friendships_ref.where(
            field_path="user1_id", op_string="==", value=min(user1_id, user2_id)
        )
        .where(field_path="user2_id", op_string="==", value=max(user1_id, user2_id))
        .limit(1)
        .stream()
    )
    if any(True for _ in query):
        print(
            f"Friendship between '{user1_id}' and '{user2_id}' already exists. Skipping."
        )
        return
    # Create friendship
    friendship_data = {
        "user1_id": min(user1_id, user2_id),
        "user2_id": max(user1_id, user2_id),
        "created_at": datetime.datetime.utcnow(),
    }
    friendships_ref.add(friendship_data)
    print(f"Friendship created between '{user1_id}' and '{user2_id}'.")

    # Initialize streak with current_streak=0 and last_mutual_recitation=None
    streaks_ref = db.collection("streaks")
    streak_data = {
        "user1_id": min(user1_id, user2_id),
        "user2_id": max(user1_id, user2_id),
        "current_streak": 0,
        "last_mutual_recitation": None,
        "created_at": datetime.datetime.utcnow(),
    }
    streaks_ref.add(streak_data)
    print(f"Streak initialized between '{user1_id}' and '{user2_id}'.")


# Create Recitation
def create_recitation(user_id, date=None):
    recitations_ref = db.collection("recitations")
    users_ref = db.collection("users").document(user_id)
    if not date:
        # Use a fixed past date for testing purposes
        # For example, set to 1 day ago
        date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    else:
        # Ensure date is datetime.datetime
        if isinstance(date, datetime.date) and not isinstance(date, datetime.datetime):
            date = datetime.datetime.combine(date, datetime.time())
    # Update user's last_recitation_time
    users_ref.update({"last_recitation_time": date})
    # Check if recitation already exists for the date using keyword arguments
    query = (
        recitations_ref.where(field_path="user_id", op_string="==", value=user_id)
        .where(field_path="date", op_string="==", value=date)
        .limit(1)
        .stream()
    )
    if any(True for _ in query):
        print(f"Recitation for user '{user_id}' on '{date}' already exists. Skipping.")
        return
    # Create recitation
    recitation_data = {
        "user_id": user_id,
        "date": date,  # Stored as datetime.datetime
        "recited_at": date,
    }
    recitations_ref.add(recitation_data)
    print(f"Recitation for user '{user_id}' on '{date}' created.")


# Update Streaks based on existing recitations
def update_streaks():
    streaks_ref = db.collection("streaks").stream()
    for streak_doc in streaks_ref:
        streak = streak_doc.to_dict()
        user1_id = streak["user1_id"]
        user2_id = streak["user2_id"]
        # Fetch users' last_recitation_time
        user1_doc = db.collection("users").document(user1_id).get()
        user2_doc = db.collection("users").document(user2_id).get()
        if not user1_doc.exists or not user2_doc.exists:
            continue
        user1_recitation = user1_doc.to_dict().get("last_recitation_time")
        user2_recitation = user2_doc.to_dict().get("last_recitation_time")
        if user1_recitation and user2_recitation:
            time_diff = abs(user1_recitation - user2_recitation).total_seconds()
            if time_diff <= 86400:  # 24 hours
                # Increment streak
                new_streak = streak["current_streak"] + 1
                streaks_ref.document(streak_doc.id).update(
                    {
                        "current_streak": new_streak,
                        "last_mutual_recitation": max(
                            user1_recitation, user2_recitation
                        ),
                    }
                )
                print(
                    f"Streak between '{user1_id}' and '{user2_id}' incremented to {new_streak}."
                )
            else:
                # Reset streak
                streaks_ref.document(streak_doc.id).update(
                    {"current_streak": 0, "last_mutual_recitation": None}
                )
                print(f"Streak between '{user1_id}' and '{user2_id}' reset to 0.")
        else:
            # Reset streak if any user hasn't recited
            streaks_ref.document(streak_doc.id).update(
                {"current_streak": 0, "last_mutual_recitation": None}
            )
            print(
                f"Streak between '{user1_id}' and '{user2_id}' reset to 0 due to missing recitation."
            )


# Main Function to Populate Dummy Data
def populate_dummy_data():
    print("Starting to populate dummy data...\n")

    # 1. Create Users
    users = [
        {"username": "alice", "email": "alice@example.com", "password": "password123"},
        {"username": "bob", "email": "bob@example.com", "password": "password456"},
        {
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "password789",
        },
    ]
    user_ids = {}
    for user in users:
        user_id = create_user(user["username"], user["email"], user["password"])
        if user_id:
            user_ids[user["username"]] = user_id

    print("\nUsers created:\n", user_ids, "\n")

    # 2. Create Friendships
    friendships = [
        ("alice", "bob"),
        ("alice", "charlie"),
        ("bob", "charlie"),
    ]
    for u1, u2 in friendships:
        user1_id = user_ids.get(u1)
        user2_id = user_ids.get(u2)
        if user1_id and user2_id:
            create_friendship(user1_id, user2_id)

    # 3. Create Recitations
    # Assume all users have recited today and yesterday for testing streak logic
    for username, user_id in user_ids.items():
        # Create recitation for yesterday
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        create_recitation(user_id, date=yesterday)
        # Create recitation for today
        create_recitation(user_id, date=datetime.datetime.utcnow())

    # 4. Update Streaks
    print("\nUpdating streaks based on recitations...\n")
    update_streaks()

    print("\nDummy data population completed.")


if __name__ == "__main__":
    populate_dummy_data()
