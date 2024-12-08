# app.py

import streamlit as st
from utils import (
    register_user,
    login_user,
    send_friend_request,
    get_friend_requests,
    respond_friend_request,
    get_friends,
    mark_recitation,
    get_streaks,
)
import datetime
import time  # Import time module for sleep functionality
import os  # Import os for file path handling
import uuid  # Import uuid for generating unique tokens
from streamlit_cookies_manager import EncryptedCookieManager  # Import Cookies Manager

# Initialize Cookies Manager
cookies = EncryptedCookieManager(
    prefix="quran_tracker/",
    password="your_secure_password_here",  # Replace with a secure password
)

# Wait for the cookies to load
if not cookies.ready():
    st.stop()

# Set Streamlit Page Configuration
st.set_page_config(page_title="Quran Recitation Tracker", layout="wide")

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "navigate_to" not in st.session_state:
    st.session_state["navigate_to"] = None  # Initialize navigation flag


# Helper function to load images
def load_image(image_name):
    image_path = os.path.join("images", image_name)
    return image_path


# Helper function to center images
def center_image(image_path, width=300):
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center;">
            <img src="{image_path}" width="{width}">
        </div>
        """,
        unsafe_allow_html=True,
    )


# Navigation
def main():
    # Check for auth token in cookies
    auth_token = cookies.get("auth_token")

    if auth_token and not st.session_state["logged_in"]:
        # Query Firestore to find the user with this auth_token
        users_ref = db.collection("users")
        query = users_ref.where("auth_token", "==", auth_token).stream()
        user = None
        for doc in query:
            user = doc.to_dict()
            user["id"] = doc.id
            break
        if user:
            # Set session state
            st.session_state["logged_in"] = True
            st.session_state["user"] = user
        else:
            # Invalid token; clear the cookie
            del cookies["auth_token"]
            cookies.save()

    # Handle navigation before rendering widgets
    if st.session_state["navigate_to"] == "Login":
        st.session_state["page_choice"] = "Login"
        st.session_state["navigate_to"] = None
    elif st.session_state["navigate_to"] == "Register":
        st.session_state["page_choice"] = "Register"
        st.session_state["navigate_to"] = None

    if not st.session_state["logged_in"]:
        st.sidebar.title("Welcome")
        # Assign selectbox value from session_state or default
        choice = st.sidebar.selectbox(
            "Choose an option", ["Login", "Register"], key="page_choice"
        )
        if choice == "Login":
            login()
        elif choice == "Register":
            register()
    else:
        st.sidebar.title(f"Hello, {st.session_state['user']['username']}!")
        nav = st.sidebar.radio(
            "Navigation", ["Dashboard", "Friends", "Friend Requests", "Logout"]
        )
        if nav == "Dashboard":
            dashboard()
        elif nav == "Friends":
            manage_friends()
        elif nav == "Friend Requests":
            manage_friend_requests()
        elif nav == "Logout":
            logout()


# Registration Page
def register():
    st.title("Register")

    # Display the image at the top, centered
    center_image(load_image("1.png"), width=600)  # Adjust width as needed

    with st.form("registration_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Register")
    if submit:
        if username and email and password:
            success, message = register_user(username, email, password)
            if success:
                st.success(message)
                # Create a placeholder for the success message
                placeholder = st.empty()
                placeholder.success("Registration successful. Redirecting to Login...")
                # Pause for 1 second
                time.sleep(1)
                # Set the navigation flag to "Login"
                st.session_state["navigate_to"] = "Login"
                # Refresh the app to navigate to the login page
                st.rerun()
            else:
                st.error(message)
        else:
            st.error("Please fill out all fields.")


# Login Page
def login():
    st.title("Login")

    # Display the image at the top, centered
    center_image(load_image("1.png"), width=600)  # Adjust width as needed

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
    if submit:
        if username and password:
            success, result = login_user(username, password)
            if success:
                # Update session state
                st.session_state["logged_in"] = True
                st.session_state["user"] = result

                # Generate a unique token
                auth_token = str(uuid.uuid4())

                # Store the token in the user's Firestore document
                user_doc = db.collection("users").document(result["id"])
                user_doc.update({"auth_token": auth_token})

                # Set the auth token in a cookie
                cookies["auth_token"] = auth_token
                cookies.save()

                # Create a placeholder for the success message
                placeholder = st.empty()
                placeholder.success(
                    "Logged in successfully! Redirecting to Dashboard..."
                )

                # Pause for 1 second
                time.sleep(1)

                # Clear the placeholder
                placeholder.empty()

                # Refresh the app to navigate to the dashboard
                st.rerun()
            else:
                st.error(result)
        else:
            st.error("Please enter both username and password.")


# Logout Function
def logout():
    # Update session state
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

    # Remove auth token from Firestore
    if "user" in st.session_state and st.session_state["user"]:
        user_doc = db.collection("users").document(st.session_state["user"]["id"])
        user_doc.update({"auth_token": ""})  # Clear the auth token

    # Delete the auth token cookie
    if "auth_token" in cookies:
        del cookies["auth_token"]
        cookies.save()

    # Create a placeholder for the success message
    placeholder = st.empty()
    placeholder.success("Logging out successfully! Redirecting...")

    # Pause for 2 seconds
    time.sleep(2)

    # Clear the placeholder
    placeholder.empty()

    # Refresh the app to navigate back to login/register
    st.rerun()


# Dashboard Page
def dashboard():
    st.title("Dashboard")
    user_id = st.session_state["user"]["id"]
    # Recitation Button
    if st.button("Mark Recitation for Today"):
        success, message = mark_recitation(user_id)
        if success:
            st.success(message)
        else:
            st.warning(message)
    # Display Streaks
    st.subheader("Your Streaks with Friends")
    streaks = get_streaks(user_id)
    active_streaks = [s for s in streaks if s["current_streak"] > 0]
    if active_streaks:
        for streak in active_streaks:
            st.write(f"**{streak['friend_username']}**: {streak['current_streak']} 🔥")
    else:
        st.info("No active streaks. Start reciting to build streaks!")


# Friends Management Page
def manage_friends():
    st.title("Your Friends")
    friends = get_friends(st.session_state["user"]["id"])
    if friends:
        for friend in friends:
            st.write(f"- {friend['username']}")
    else:
        st.info("You have no friends yet. Send a friend request to get started!")

    st.subheader("Add a Friend")
    with st.form("add_friend_form"):
        friend_username = st.text_input("Friend's Username")
        send_request = st.form_submit_button("Send Friend Request")
    if send_request:
        if friend_username:
            success, message = send_friend_request(
                st.session_state["user"]["id"], friend_username
            )
            if success:
                st.success(message)
            else:
                st.error(message)
        else:
            st.error("Please enter a username.")


# Friend Requests Management Page
def manage_friend_requests():
    st.title("Friend Requests")
    user_id = st.session_state["user"]["id"]
    requests = get_friend_requests(user_id)
    if requests:
        for req in requests:
            st.write(f"**From:** {req['from_username']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Accept", key=f"accept_{req['id']}"):
                    success, message = respond_friend_request(req["id"], accept=True)
                    if success:
                        st.success("Friend request accepted.")
                        # Optionally, you can refresh the page to update the list
                        st.rerun()
                    else:
                        st.error("Failed to accept friend request.")
            with col2:
                if st.button("Reject", key=f"reject_{req['id']}"):
                    success, message = respond_friend_request(req["id"], accept=False)
                    if success:
                        st.warning("Friend request rejected.")
                        # Optionally, you can refresh the page to update the list
                        st.rerun()
                    else:
                        st.error("Failed to reject friend request.")
    else:
        st.info("No pending friend requests.")


if __name__ == "__main__":
    main()
