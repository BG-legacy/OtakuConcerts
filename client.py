import socket  # Import socket module for network communication
import json  # Import json module for data serialization/deserialization

# Server connection configuration
HOST = "127.0.0.1"  # Localhost IP address
PORT = 12345  # Port number for the connection

# Create a socket object for TCP communication
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))  # Connect to the server at the specified host and port

# Global variables to store user information
user_id = None  # User ID received from server after login
points = 0  # Points balance for the current user

def send_request(action, data={}):
    """
    Sends a request to the server and returns the response.
    
    Args:
        action (str): The action to perform (e.g. 'login', 'register')
        data (dict): Additional data for the request
        
    Returns:
        dict: The server's response parsed from JSON
    """
    request = {"action": action}  # Create request dictionary with action
    request.update(data)  # Add additional data to the request
    client.send(json.dumps(request).encode())  # Convert to JSON, encode to bytes, and send
    response_data = client.recv(4096).decode()  # Receive response (4096 bytes buffer), decode from bytes
    response = json.loads(response_data)  # Parse JSON response into a dictionary
    return response  # Return the parsed response

def login():
    """
    Handles the user login process.
    
    Returns:
        bool: True if login was successful, False otherwise
    """
    global user_id, points  # Use global variables so we can modify them
    username = input("Enter username: ")  # Prompt user for username
    password = input("Enter password: ")  # Prompt user for password
    # Send login request to server with credentials
    response = send_request("login", {"username": username, "password": password})
    if response["status"] == "success":  # Check if login was successful
        user_id = response["user_id"]  # Store the user ID from response
        points = response["points"]  # Store the points balance from response
        print(f"Login successful. You have {points} points.")  # Inform user of successful login
        return True  # Return success
    else:
        print("Login failed:", response["message"])  # Show error message from server
        return False  # Return failure

def register():
    """
    Handles new user registration.
    
    Returns:
        bool: True if registration was successful, False otherwise
    """
    username = input("Enter new username: ")  # Prompt for new username
    password = input("Enter new password: ")  # Prompt for new password
    # Send registration request to server
    response = send_request("register", {"username": username, "password": password})
    print(response["message"])  # Display response message from server
    if response["status"] == "success":  # Check if registration was successful
        return True  # Return success
    return False  # Return failure

def purchase_ticket():
    """
    Handles ticket purchasing for events.
    Updates points balance after successful purchase.
    """
    global points  # Use global points variable so we can modify it
    if user_id is None:  # Check if user is logged in
        print("Please login first.")  # Inform user login is required
        return
        
    event_id = input("Enter event ID to purchase: ")  # Prompt for event ID
    ticket_type = input("Choose ticket type (Regular/VIP): ").strip().capitalize()  # Prompt for ticket type
    if ticket_type not in ["Regular", "VIP"]:  # Validate ticket type input
        print("Invalid ticket type.")  # Inform user of invalid selection
        return
    # Send purchase request to server
    response = send_request("purchase_ticket", {"user_id": user_id, "event_id": event_id, "ticket_type": ticket_type})
    print(response["message"])  # Display response message from server
    
    if response["status"] == "success":  # Check if purchase was successful
        # Update points after purchase
        check_points()  # Refresh points balance from server

def check_points():
    """
    Retrieves and displays the user's current points balance.
    """
    global points  # Use global points variable so we can modify it
    if user_id is None:  # Check if user is logged in
        print("Please login first.")  # Inform user login is required
        return
        
    # Send request to check points balance
    response = send_request("check_points", {"user_id": user_id})
    if response["status"] == "success":  # Check if request was successful
        points = response["points"]  # Update points with value from server
        print(f"You have {points} points.")  # Display current points balance

def view_events():
    """
    Retrieves and displays all available events.
    """
    # Send request to get list of events
    response = send_request("view_events")
    if response["status"] == "success":  # Check if request was successful
        print("\nAvailable Events:")  # Print header
        print("ID | Event Name | Regular Cost | VIP Cost")  # Print column headers
        print("-" * 50)  # Print separator line
        for event in response["events"]:  # Iterate through each event in the response
            # Print event details: ID, name, regular price, VIP price
            print(f"{event[0]} | {event[1]} | Regular: {event[4]} points | VIP: {event[5]} points")
        print()  # Print blank line after events list

def main():
    """
    Main function that handles the user interface flow.
    """
    global user_id  # Use global user_id variable
    print("Welcome to Otaku Concerts!")  # Display welcome message
    
    # Login/Registration loop
    while True:
        if user_id is None:  # Check if user is not logged in
            print("\n1. Login | 2. Register | 3. Exit")  # Display pre-login menu
            choice = input("> ")  # Get user choice
            if choice == "1":  # User chose login
                if login():  # Attempt login
                    break  # Proceed to main menu after successful login
            elif choice == "2":  # User chose register
                register()  # Attempt registration
            elif choice == "3":  # User chose exit
                print("Goodbye!")  # Display exit message
                return  # Exit the program
            else:
                print("Invalid choice.")  # Inform user of invalid selection
        else:
            break  # User is already logged in, skip to main menu
    
    # Main menu loop (after login)
    while user_id is not None:  # Loop while user is logged in
        print("\n1. View Events | 2. Buy Ticket | 3. Check Points | 4. Logout | 5. Exit")  # Display main menu
        choice = input("> ")  # Get user choice
        if choice == "1":  # User chose view events
            view_events()  # Display events
        elif choice == "2":  # User chose buy ticket
            purchase_ticket()  # Process ticket purchase
        elif choice == "3":  # User chose check points
            check_points()  # Display points balance
        elif choice == "4":  # User chose logout
            user_id = None  # Clear user_id to indicate logout
            print("Logged out successfully.")  # Display logout confirmation
            main()  # Restart the login flow
            return  # Return from current main() call (prevents stacking)
        elif choice == "5":  # User chose exit
            print("Goodbye!")  # Display exit message
            break  # Exit the loop
        else:
            print("Invalid choice.")  # Inform user of invalid selection

if __name__ == "__main__":  # Check if this file is being run directly
    try:
        main()  # Execute the main function
    finally:
        client.close()  # Ensure socket is closed even if an error occurs
