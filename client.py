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
    try:
        request = {"action": action}  # Create request dictionary with action
        request.update(data)  # Add additional data to the request
        client.send(json.dumps(request).encode())  # Convert to JSON, encode to bytes, and send
        
        # Receive response in chunks until complete
        chunks = []
        while True:
            chunk = client.recv(4096).decode()  # Receive chunk (4096 bytes buffer), decode from bytes
            if not chunk:
                break
            chunks.append(chunk)
            if chunk.endswith('\n'):  # If we received a complete message
                break
        
        response_data = ''.join(chunks)  # Combine all chunks
        if not response_data:
            raise Exception("No response received from server")
            
        response = json.loads(response_data)  # Parse JSON response into a dictionary
        return response  # Return the parsed response
    except json.JSONDecodeError as e:
        print(f"Error decoding server response: {e}")
        print(f"Raw response: {response_data}")
        raise
    except Exception as e:
        print(f"Error in send_request: {e}")
        raise

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
    ticket_type = input("Choose ticket type (Regular/VIP): ").strip().title()  # Prompt for ticket type and normalize input
    if ticket_type not in ["Regular", "VIP"]:  # Validate ticket type input
        print("Invalid ticket type. Please choose either 'Regular' or 'VIP'.")  # Inform user of invalid selection
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
    try:
        # Send request to get list of events
        response = send_request("view_events")
        if response["status"] == "success":  # Check if request was successful
            print("\nAvailable Events:")  # Print header
            print("ID | Event Name | Regular Tickets | VIP Tickets | Regular Cost | VIP Cost")  # Print column headers
            print("-" * 80)  # Print separator line
            for event in response["events"]:  # Iterate through each event in the response
                # Print event details in a formatted way
                print(f"{event['id']} | {event['name']} | {event['available_tickets']} | {event['vip_tickets']} | {event['regular_cost']} points | {event['vip_cost']} points")
            print()  # Print blank line after events list
        else:
            print("Error viewing events:", response.get("message", "Unknown error"))
    except json.JSONDecodeError:
        print("Error: Received invalid response from server")
    except Exception as e:
        print(f"Error viewing events: {str(e)}")

def add_funds():
    """
    Handles adding funds to the user's balance.
    """
    global points  # Use global points variable so we can modify it
    if user_id is None:  # Check if user is logged in
        print("Please login first.")  # Inform user login is required
        return
        
    try:
        amount = int(input("Enter amount to add: "))  # Prompt for amount to add
        if amount <= 0:
            print("Amount must be greater than 0.")
            return
            
        # Send request to add funds
        response = send_request("add_funds", {"userid": user_id, "amount": amount})
        print(response["message"])  # Display response message from server
        
        if response["status"] == "success":  # Check if request was successful
            check_points()  # Refresh points balance from server
    except ValueError:
        print("Please enter a valid number.")

def view_purchases():
    """
    Handles viewing the user's purchase history.
    """
    global points
    if user_id is None:
        print("Please login first")
        return
    response = send_request("view_purchases", {"user_id": user_id})
    if response["status"] == "success":
        print("\nPurchase History:")
        for purchase in response["purchases"]:
            print(f"Purchase ID: {purchase[0]}")
            print(f"Event ID: {purchase[1]}")
            print(f"Ticket Type: {purchase[2]}")
            print(f"Purchase Date: {purchase[3]}")
            print("-" * 50)
    else:
        print("Error viewing purchases:", response.get("message", "Unknown error"))

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
        print("\n1. View Events | 2. Buy Ticket | 3. Check Points | 4. Logout | 5. Add Funds | 6. View Purchases | 7. Exit")  # Display main menu
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
        elif choice == "5":  # User chose add funds
            add_funds()  # Process add funds
        elif choice == "6":  # User chose view purchases
            view_purchases()  # Display purchase history
        elif choice == "7":  # User chose exit
            print("Goodbye!")  # Display exit message
            break  # Exit the loop
        else:
            print("Invalid choice.")  # Inform user of invalid selection

if __name__ == "__main__":  # Check if this file is being run directly
    try:
        main()  # Execute the main function
    finally:
        client.close()  # Ensure socket is closed even if an error occurs
