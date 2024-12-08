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

# Set Streamlit Page Configuration
st.set_page_config(page_title="Quran Recitation Tracker", layout="wide")

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "navigate_to" not in st.session_state:
    st.session_state["navigate_to"] = None  # Initialize navigation flag


# Navigation
def main():
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
                st.experimental_rerun()
            else:
                st.error(message)
        else:
            st.error("Please fill out all fields.")


# Login Page
def login():
    st.title("Login")
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
                st.experimental_rerun()
            else:
                st.error(result)
        else:
            st.error("Please enter both username and password.")


# Logout Function
def logout():
    # Update session state
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

    # Create a placeholder for the success message
    placeholder = st.empty()
    placeholder.success("Logging out successfully! Redirecting...")

    # Pause for 2 seconds
    time.sleep(2)

    # Clear the placeholder
    placeholder.empty()

    # Refresh the app to navigate back to login/register
    st.experimental_rerun()


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
            st.write(
                f"**{streak['friend_username']}**: {streak['current_streak']} day(s) streak"
            )
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
                        st.experimental_rerun()
                    else:
                        st.error("Failed to accept friend request.")
            with col2:
                if st.button("Reject", key=f"reject_{req['id']}"):
                    success, message = respond_friend_request(req["id"], accept=False)
                    if success:
                        st.warning("Friend request rejected.")
                        # Optionally, you can refresh the page to update the list
                        st.experimental_rerun()
                    else:
                        st.error("Failed to reject friend request.")
    else:
        st.info("No pending friend requests.")


if __name__ == "__main__":
    main()