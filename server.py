import sqlite3  # Import SQLite database module for data storage
import socket  # Import socket module for network communication
import json  # Import json module for data serialization/deserialization
import threading  # Import threading module to handle multiple client connections

# Database setup
conn = sqlite3.connect("ticket_system.db", check_same_thread=False)  # Connect to SQLite database, allow access from multiple threads
cursor = conn.cursor()  # Create a cursor object to execute SQL commands

# Create tables if they don't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique user ID, auto-incremented
        username TEXT UNIQUE,  -- Username (must be unique)
        password TEXT,  -- User password (stored as plain text - not secure for production)
        points INTEGER DEFAULT 100  -- User's point balance, starts with 100 points
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique event ID, auto-incremented
        name TEXT,  -- Name of the event/concert
        available_tickets INTEGER,  -- Number of regular tickets available
        vip_tickets INTEGER DEFAULT 10,  -- Number of VIP tickets available, defaults to 10
        regular_cost INTEGER,  -- Cost in points for regular tickets
        vip_cost INTEGER  -- Cost in points for VIP tickets
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique purchase ID, auto-incremented
        user_id INTEGER,  -- ID of user who made the purchase
        event_id INTEGER,  -- ID of event for which ticket was purchased
        ticket_type TEXT,  -- Type of ticket (Regular or VIP)
        FOREIGN KEY(user_id) REFERENCES users(id),  -- Foreign key constraint to users table
        FOREIGN KEY(event_id) REFERENCES events(id)  -- Foreign key constraint to events table
    )
""")

conn.commit()  # Commit the table creation transactions to the database

# Insert Anime Concerts (Only run this once)
cursor.executemany("""
    INSERT INTO events (name, available_tickets, vip_tickets, regular_cost, vip_cost) VALUES (?, ?, ?, ?, ?)
""", [
    # Event data: (name, regular_tickets, vip_tickets, regular_cost, vip_cost)
    ("LiSA Live Concert", 50, 10, 40, 80),
    ("Eir Aoi Anime Night", 60, 10, 30, 70),
    ("Aimer: The Nightingale Tour", 70, 10, 35, 75),
    ("Yuki Kajiura: Fate Soundtracks Live", 40, 5, 50, 100),
    ("Hiroyuki Sawano: Attack on Titan OST Concert", 80, 8, 45, 90),
    ("Kenshi Yonezu: Chainsaw Man Opening Live", 100, 12, 50, 100),
    ("ClariS Special Anime Live", 55, 10, 25, 60),
    ("FLOW Naruto & Code Geass Concert", 90, 15, 30, 70),
    ("ReoNa SAO Alicization Tour", 65, 10, 35, 75),
    ("fripSide: Railgun Electro Night", 75, 10, 40, 85)
])
conn.commit()  # Commit the event insertions to the database

# Server setup
HOST = "127.0.0.1"  # Localhost IP address
PORT = 12345  # Port number for the connection

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create TCP socket object
server.bind((HOST, PORT))  # Bind socket to the specified host and port
server.listen(5)  # Listen for connections, queue up to 5 connection requests
print("Server is running...")  # Display server startup message

def handle_client(client_socket):
    """
    Handle communication with a connected client.
    
    Args:
        client_socket: Socket object for the client connection
    """
    while True:  # Continuous loop to handle client requests
        try:
            data = client_socket.recv(1024).decode()  # Receive data from client (1024 bytes buffer), decode from bytes
            if not data:  # Check if client disconnected
                break  # Exit the loop if no data received
            
            request = json.loads(data)  # Parse JSON data into Python dictionary
            action = request.get("action")  # Extract the requested action from the data

            if action == "register":  # Handle user registration
                username = request.get("username")  # Get username from request
                password = request.get("password")  # Get password from request
                try:
                    # Insert new user into database
                    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                    conn.commit()  # Commit the transaction
                    # Send success response to client
                    client_socket.send(json.dumps({"status": "success", "message": "User registered successfully"}).encode())
                except sqlite3.IntegrityError:  # Handle case where username already exists
                    # Send error response to client
                    client_socket.send(json.dumps({"status": "error", "message": "Username already exists"}).encode())

            elif action == "login":  # Handle user login
                username = request.get("username")  # Get username from request
                password = request.get("password")  # Get password from request
                # Query database for matching username and password
                cursor.execute("SELECT id, points FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()  # Get first matching row
                if user:  # Check if user was found
                    # Send success response with user ID and points
                    client_socket.send(json.dumps({"status": "success", "user_id": user[0], "points": user[1]}).encode())
                else:
                    # Send error response if credentials are invalid
                    client_socket.send(json.dumps({"status": "error", "message": "Invalid credentials"}).encode())

            elif action == "view_events":  # Handle request to view all events
                cursor.execute("SELECT * FROM events")  # Query all events from database
                events = cursor.fetchall()  # Get all rows from the query
                # Send success response with events data
                client_socket.send(json.dumps({"status": "success", "events": events}).encode())

            elif action == "purchase_ticket":  # Handle ticket purchase request
                user_id = request.get("user_id")  # Get user ID from request
                event_id = request.get("event_id")  # Get event ID from request
                ticket_type = request.get("ticket_type")  # Get ticket type from request

                # Query user points
                cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()  # Get user data

                # Query event details
                cursor.execute("SELECT available_tickets, vip_tickets, regular_cost, vip_cost FROM events WHERE id = ?", (event_id,))
                event = cursor.fetchone()  # Get event data

                # Count how many tickets the user has already purchased (for discount calculation)
                cursor.execute("SELECT COUNT(*) FROM purchases WHERE user_id = ?", (user_id,))
                purchase_count = cursor.fetchone()[0]  # Get count of previous purchases

                if user and event:  # Check if both user and event exist
                    user_points = user[0]  # Extract user points
                    available_tickets, vip_tickets, regular_cost, vip_cost = event  # Extract event data
                    ticket_cost = vip_cost if ticket_type == "VIP" else regular_cost  # Determine ticket cost based on type

                    if purchase_count >= 3:  # Apply 10% discount if user has purchased 3 or more tickets
                        ticket_cost = int(ticket_cost * 0.9)  # Calculate discounted price

                    if ticket_cost > user_points:  # Check if user has enough points
                        # Send error if not enough points
                        client_socket.send(json.dumps({"status": "error", "message": "Not enough points"}).encode())
                    elif ticket_type == "VIP" and vip_tickets <= 0:  # Check if VIP tickets are available
                        # Send error if VIP tickets sold out
                        client_socket.send(json.dumps({"status": "error", "message": "VIP tickets sold out"}).encode())
                    elif ticket_type == "Regular" and available_tickets <= 0:  # Check if regular tickets are available
                        # Send error if regular tickets sold out
                        client_socket.send(json.dumps({"status": "error", "message": "Regular tickets sold out"}).encode())
                    else:
                        # Deduct points from user
                        cursor.execute("UPDATE users SET points = points - ? WHERE id = ?", (ticket_cost, user_id))
                        if ticket_type == "VIP":  # If VIP ticket
                            # Decrease VIP ticket count
                            cursor.execute("UPDATE events SET vip_tickets = vip_tickets - 1 WHERE id = ?", (event_id,))
                        else:  # If regular ticket
                            # Decrease regular ticket count
                            cursor.execute("UPDATE events SET available_tickets = available_tickets - 1 WHERE id = ?", (event_id,))
                        # Record the purchase
                        cursor.execute("INSERT INTO purchases (user_id, event_id, ticket_type) VALUES (?, ?, ?)", (user_id, event_id, ticket_type))
                        conn.commit()  # Commit all transaction changes
                        # Send success response with purchase details
                        client_socket.send(json.dumps({"status": "success", "message": f"{ticket_type} Ticket purchased for {ticket_cost} points"}).encode())
            elif action == "check_points":  # Handle request to check points balance
                user_id = request.get("user_id")  # Get user ID from request
                # Query user points
                cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()  # Get user data
                if user:  # Check if user exists
                    # Send success response with points balance
                    client_socket.send(json.dumps({"status": "success", "points": user[0]}).encode())

        except Exception as e:  # Handle any exceptions that occur
            print("Error:", e)  # Print error to server console
            try:
                # Try to send error response to client
                client_socket.send(json.dumps({"status": "error", "message": "An error occurred"}).encode())
            except:
                pass  # Ignore if sending fails (connection may be closed)
            break  # Exit the loop on error
    
    print(f"Client disconnected")  # Log client disconnection
    client_socket.close()  # Close the client socket

# Main server loop
while True:  # Infinite loop to accept new connections
    try:
        client_socket, addr = server.accept()  # Accept incoming connection
        print(f"Connected to {addr}")  # Log the connection
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))  # Create a new thread for the client
        client_thread.daemon = True  # Set thread as daemon so it exits when main thread exits
        client_thread.start()  # Start the client thread
    except KeyboardInterrupt:  # Handle manual server shutdown (Ctrl+C)
        print("Server shutting down...")  # Log shutdown
        break  # Exit the loop
    except Exception as e:  # Handle other exceptions
        print(f"Error accepting connection: {e}")  # Log the error

# Close server
server.close()  # Close the server socket
conn.close()  # Close the database connection
print("Server closed")  # Log server closure
