# utils.py

import bcrypt
from google.cloud import firestore
import datetime
import streamlit as st
import json
from google.oauth2 import service_account

# Initialize Firestore Client
def init_firestore():
    try:
        # Load Firestore credentials from Streamlit secrets
        credentials_info = st.secrets["firestore_credentials"]
        credentials_dict = json.loads(credentials_info)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        return firestore.Client(credentials=credentials, project=credentials_dict['project_id'])
    except KeyError:
        st.error("Firestore credentials not found in secrets.")
        raise

db = init_firestore()



# Password Hashing
def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# User Registration
def register_user(username, email, password):
    users_ref = db.collection("users")
    # Check if username already exists using keyword arguments
    query = (
        users_ref.where(field_path="username", op_string="==", value=username)
        .limit(1)
        .stream()
    )
    if any(True for _ in query):
        return False, "Username already exists."
    # Check if email already exists using keyword arguments
    query = (
        users_ref.where(field_path="email", op_string="==", value=email)
        .limit(1)
        .stream()
    )
    if any(True for _ in query):
        return False, "Email already exists."
    # Hash the password
    password_hashed = hash_password(password)
    # Create user document with last_recitation_time initialized to None
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": password_hashed,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "last_recitation_time": None,  # Initialize as None
    }
    users_ref.add(user_doc)
    return True, "Registration successful."


# User Login
def login_user(username, password):
    users_ref = db.collection("users")
    query = (
        users_ref.where(field_path="username", op_string="==", value=username)
        .limit(1)
        .stream()
    )
    user = None
    for doc in query:
        user = doc.to_dict()
        user["id"] = doc.id
        break
    if user and verify_password(password, user["password_hash"]):
        return True, user
    else:
        return False, "Invalid username or password."


# Send Friend Request
def send_friend_request(from_user_id, to_username):
    users_ref = db.collection("users")
    # Get the to_user_id
    query = (
        users_ref.where(field_path="username", op_string="==", value=to_username)
        .limit(1)
        .stream()
    )
    to_user = None
    for doc in query:
        to_user = doc.to_dict()
        to_user["id"] = doc.id
        break
    if not to_user:
        return False, "User not found."
    if to_user["id"] == from_user_id:
        return False, "You cannot send a friend request to yourself."
    # Check if a friendship already exists using keyword arguments
    friendships_ref = db.collection("friendships")
    friendship_query = (
        friendships_ref.where(
            field_path="user1_id",
            op_string="==",
            value=min(from_user_id, to_user["id"]),
        )
        .where(
            field_path="user2_id",
            op_string="==",
            value=max(from_user_id, to_user["id"]),
        )
        .limit(1)
        .stream()
    )
    if any(True for _ in friendship_query):
        return False, "You are already friends."
    # Check if a friend request is already pending using keyword arguments
    friend_requests_ref = db.collection("friend_requests")
    request_query = (
        friend_requests_ref.where(
            field_path="from_user_id", op_string="==", value=from_user_id
        )
        .where(field_path="to_user_id", op_string="==", value=to_user["id"])
        .where(field_path="status", op_string="==", value="pending")
        .limit(1)
        .stream()
    )
    if any(True for _ in request_query):
        return False, "Friend request already sent."
    # Create friend request
    friend_request_doc = {
        "from_user_id": from_user_id,
        "to_user_id": to_user["id"],
        "status": "pending",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    friend_requests_ref.add(friend_request_doc)
    return True, "Friend request sent."


# Get Friend Requests for a User
def get_friend_requests(user_id):
    friend_requests_ref = db.collection("friend_requests")
    query = (
        friend_requests_ref.where(
            field_path="to_user_id", op_string="==", value=user_id
        )
        .where(field_path="status", op_string="==", value="pending")
        .stream()
    )
    requests = []
    for doc in query:
        req = doc.to_dict()
        req["id"] = doc.id
        # Get sender's username
        sender = db.collection("users").document(req["from_user_id"]).get()
        if sender.exists:
            req["from_username"] = sender.to_dict().get("username", "Unknown")
        requests.append(req)
    return requests


# Accept or Reject Friend Request
def respond_friend_request(request_id, accept=True):
    friend_requests_ref = db.collection("friend_requests").document(request_id)
    try:
        request_doc = friend_requests_ref.get()
        if not request_doc.exists:
            return False, "Friend request not found."
        request_data = request_doc.to_dict()
        if request_data["status"] != "pending":
            return False, "Friend request already responded to."
        # Update the status
        new_status = "accepted" if accept else "rejected"
        friend_requests_ref.update({"status": new_status})
        if accept:
            # Create friendship
            friendships_ref = db.collection("friendships")
            user1_id = request_data["from_user_id"]
            user2_id = request_data["to_user_id"]
            # Ensure consistent ordering
            if user1_id < user2_id:
                friendship_data = {
                    "user1_id": user1_id,
                    "user2_id": user2_id,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                }
            else:
                friendship_data = {
                    "user1_id": user2_id,
                    "user2_id": user1_id,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                }
            friendships_ref.add(friendship_data)
            # Initialize streak with current_streak=0 and last_mutual_recitation=None
            streaks_ref = db.collection("streaks")
            streak_data = {
                "user1_id": friendship_data["user1_id"],
                "user2_id": friendship_data["user2_id"],
                "current_streak": 0,
                "last_mutual_recitation": None,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
            }
            streaks_ref.add(streak_data)
        return True, f"Friend request {'accepted' if accept else 'rejected'}."
    except Exception as e:
        return False, str(e)


# Get Friends List
def get_friends(user_id):
    friendships_ref = db.collection("friendships")
    # Fetch friendships where user is user1
    query1 = friendships_ref.where(
        field_path="user1_id", op_string="==", value=user_id
    ).stream()
    friends = []
    for doc in query1:
        friendship = doc.to_dict()
        friend_id = friendship["user2_id"]
        friend_doc = db.collection("users").document(friend_id).get()
        if friend_doc.exists:
            friend = friend_doc.to_dict()
            friend["id"] = friend_doc.id
            friends.append(friend)
    # Fetch friendships where user is user2
    query2 = friendships_ref.where(
        field_path="user2_id", op_string="==", value=user_id
    ).stream()
    for doc in query2:
        friendship = doc.to_dict()
        friend_id = friendship["user1_id"]
        friend_doc = db.collection("users").document(friend_id).get()
        if friend_doc.exists:
            friend = friend_doc.to_dict()
            friend["id"] = friend_doc.id
            friends.append(friend)
    return friends


# Mark Recitation
def mark_recitation(user_id):
    recitations_ref = db.collection("recitations")
    users_ref = db.collection("users").document(user_id)
    # Get current timestamp as timezone-aware UTC datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    # Update user's last_recitation_time
    users_ref.update({"last_recitation_time": now})
    # Fetch user's friends
    friends = get_friends(user_id)
    # Initialize list to track mutual friends
    mutual_friends = []
    # Loop through each friend to check their last_recitation_time
    for friend in friends:
        friend_id = friend["id"]
        friend_doc = db.collection("users").document(friend_id).get()
        if friend_doc.exists:
            friend_data = friend_doc.to_dict()
            friend_last_recitation = friend_data.get("last_recitation_time")
            if friend_last_recitation:
                # Ensure friend_last_recitation is timezone-aware
                if friend_last_recitation.tzinfo is None:
                    friend_last_recitation = friend_last_recitation.replace(
                        tzinfo=datetime.timezone.utc
                    )
                time_diff = now - friend_last_recitation
                if time_diff.total_seconds() <= 86400:  # 24 hours = 86400 seconds
                    mutual_friends.append(friend_id)
    # Create or update recitation record for today
    # Firestore automatically handles datetime comparisons correctly
    today_recitation_query = (
        recitations_ref.where(field_path="user_id", op_string="==", value=user_id)
        .where(field_path="date", op_string="==", value=now)
        .limit(1)
        .stream()
    )
    if not any(True for _ in today_recitation_query):
        # Add recitation record
        recitation_data = {
            "user_id": user_id,
            "date": now,  # Stored as datetime.datetime (timezone-aware)
            "recited_at": now,
        }
        recitations_ref.add(recitation_data)
    # Update streaks with mutual friends
    streaks_ref = db.collection("streaks")
    for friend_id in mutual_friends:
        # Determine ordered user IDs
        ordered_ids = sorted([user_id, friend_id])
        # Query the streak document
        streak_query = (
            streaks_ref.where(
                field_path="user1_id", op_string="==", value=ordered_ids[0]
            )
            .where(field_path="user2_id", op_string="==", value=ordered_ids[1])
            .limit(1)
            .stream()
        )
        streak_doc = None
        for doc in streak_query:
            streak_doc = doc
            break
        if streak_doc:
            streak_data = streak_doc.to_dict()
            streak_id = streak_doc.id
            last_mutual = streak_data.get("last_mutual_recitation")
            if last_mutual:
                # Ensure last_mutual is timezone-aware
                if last_mutual.tzinfo is None:
                    last_mutual = last_mutual.replace(tzinfo=datetime.timezone.utc)
                time_since_last = now - last_mutual
                if time_since_last.total_seconds() <= 86400:
                    # Increment streak
                    new_streak = streak_data["current_streak"] + 1
                else:
                    # Reset streak
                    new_streak = 1
            else:
                # Initialize streak
                new_streak = 1
            # Update streak document
            streaks_ref.document(streak_id).update(
                {"current_streak": new_streak, "last_mutual_recitation": now}
            )
        else:
            # If no streak document exists, create one
            streak_data = {
                "user1_id": ordered_ids[0],
                "user2_id": ordered_ids[1],
                "current_streak": 1,
                "last_mutual_recitation": now,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
            }
            streaks_ref.add(streak_data)
    # Reset streaks with friends who haven't recited within 24 hours
    for friend in friends:
        friend_id = friend["id"]
        if friend_id not in mutual_friends:
            # Determine ordered user IDs
            ordered_ids = sorted([user_id, friend_id])
            # Query the streak document
            streak_query = (
                streaks_ref.where(
                    field_path="user1_id", op_string="==", value=ordered_ids[0]
                )
                .where(field_path="user2_id", op_string="==", value=ordered_ids[1])
                .limit(1)
                .stream()
            )
            streak_doc = None
            for doc in streak_query:
                streak_doc = doc
                break
            if streak_doc:
                streak_id = streak_doc.id
                # Reset streak
                streaks_ref.document(streak_id).update(
                    {"current_streak": 0, "last_mutual_recitation": None}
                )
    return True, "Recitation marked for today."


# Get Streaks
def get_streaks(user_id):
    streaks_ref = db.collection("streaks")
    # Fetch where user is user1
    query1 = streaks_ref.where(
        field_path="user1_id", op_string="==", value=user_id
    ).stream()
    # Fetch where user is user2
    query2 = streaks_ref.where(
        field_path="user2_id", op_string="==", value=user_id
    ).stream()
    streaks = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for doc in query1:
        streak = doc.to_dict()
        streak["id"] = doc.id
        # Get friend's info
        friend_id = streak["user2_id"]
        friend_doc = db.collection("users").document(friend_id).get()
        if friend_doc.exists:
            streak["friend_username"] = friend_doc.to_dict().get("username", "Unknown")
        # Check if streak is still active
        last_mutual = streak.get("last_mutual_recitation")
        if last_mutual:
            if last_mutual.tzinfo is None:
                last_mutual = last_mutual.replace(tzinfo=datetime.timezone.utc)
            time_diff = now - last_mutual
            if time_diff.total_seconds() > 86400:
                # Streak expired
                streak["current_streak"] = 0
        streaks.append(streak)
    for doc in query2:
        streak = doc.to_dict()
        streak["id"] = doc.id
        # Get friend's info
        friend_id = streak["user1_id"]
        friend_doc = db.collection("users").document(friend_id).get()
        if friend_doc.exists:
            streak["friend_username"] = friend_doc.to_dict().get("username", "Unknown")
        # Check if streak is still active
        last_mutual = streak.get("last_mutual_recitation")
        if last_mutual:
            if last_mutual.tzinfo is None:
                last_mutual = last_mutual.replace(tzinfo=datetime.timezone.utc)
            time_diff = now - last_mutual
            if time_diff.total_seconds() > 86400:
                # Streak expired
                streak["current_streak"] = 0
        streaks.append(streak)
    return streaks