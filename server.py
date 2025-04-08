import sqlite3  # Import SQLite database module for data storage
import socket  # Import socket module for network communication
import json  # Import json module for data serialization/deserialization
import threading  # Import threading module to handle multiple client connections

# Database setup
conn = sqlite3.connect("ticket_system.db", check_same_thread=False)  # Connect to SQLite database, allow access from multiple threads
cursor = conn.cursor()  # Create a cursor object to execute SQL commands

# Enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON")

# Function to verify database integrity
def verify_database_integrity():
    """Verifies that all tables exist with the correct schema and repairs if needed."""
    print("Verifying database integrity...")
    
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("Creating users table...")
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                points INTEGER DEFAULT 100
            )
        """)
        
    # Check if events table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
    if not cursor.fetchone():
        print("Creating events table...")
        cursor.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                available_tickets INTEGER,
                vip_tickets INTEGER DEFAULT 10,
                regular_cost INTEGER,
                vip_cost INTEGER
            )
        """)
        
    # Check if purchases table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchases'")
    if not cursor.fetchone():
        print("Creating purchases table...")
        cursor.execute("""
            CREATE TABLE purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                ticket_type TEXT,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(event_id) REFERENCES events(id)
            )
        """)
    
    # Verify purchases table has the correct columns
    try:
        cursor.execute("PRAGMA table_info(purchases)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Check if all expected columns exist
        expected_columns = ["id", "user_id", "event_id", "ticket_type", "purchase_date"]
        missing_columns = [col for col in expected_columns if col not in column_names]
        
        if missing_columns:
            print(f"Warning: Missing columns in purchases table: {missing_columns}")
            # Add missing columns
            for column in missing_columns:
                if column == "purchase_date":
                    print(f"Adding missing column: {column}")
                    # SQLite has limitations on ALTER TABLE - can't add a column with DEFAULT CURRENT_TIMESTAMP
                    cursor.execute("ALTER TABLE purchases ADD COLUMN purchase_date TIMESTAMP")
                    # Update existing rows to have the current timestamp
                    cursor.execute("UPDATE purchases SET purchase_date = CURRENT_TIMESTAMP WHERE purchase_date IS NULL")
                    conn.commit()
            print("Database structure updated")
    except sqlite3.Error as e:
        print(f"Error verifying purchases table columns: {e}")
    
    conn.commit()
    print("Database verification complete")

# Run database verification at startup
verify_database_integrity()

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
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Date and time of purchase
        FOREIGN KEY(user_id) REFERENCES users(id),  -- Foreign key constraint to users table
        FOREIGN KEY(event_id) REFERENCES events(id)  -- Foreign key constraint to events table
    )
""")

conn.commit()  # Commit the table creation transactions to the database

# Insert Anime Concerts (Only run this once)
cursor.execute("SELECT COUNT(*) FROM events")  # Check if events already exist
if cursor.fetchone()[0] == 0:  # Only insert if no events exist
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

def send_response(client_socket, response_data):
    """
    Helper function to send JSON response to client with proper encoding and newline.
    
    Args:
        client_socket: Socket object for the client connection
        response_data: Dictionary containing the response data
    """
    try:
        json_response = json.dumps(response_data) + '\n'  # Add newline to mark end of message
        client_socket.send(json_response.encode())
    except Exception as e:
        print(f"Error sending response: {e}")
        raise

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
                    send_response(client_socket, {"status": "success", "message": "User registered successfully"})
                except sqlite3.IntegrityError:  # Handle case where username already exists
                    # Send error response to client
                    send_response(client_socket, {"status": "error", "message": "Username already exists"})

            elif action == "login":  # Handle user login
                username = request.get("username")  # Get username from request
                password = request.get("password")  # Get password from request
                
                # ############################################################
                # ################ SQL INJECTION VULNERABILITY ###############
                # ############################################################
                # Using string formatting to construct SQL queries is highly vulnerable
                # This allows attackers to bypass authentication or extract data
                
                # Vulnerable SQL query construction
                query = f"SELECT id, points FROM users WHERE username = '{username}' AND password = '{password}'"
                cursor.execute(query)
                user = cursor.fetchone()  # Get first matching row
                if user:  # Check if user was found
                    # Send success response with user ID and points
                    send_response(client_socket, {"status": "success", "user_id": user[0], "points": user[1]})
                else:
                    # Send error response if credentials are invalid
                    send_response(client_socket, {"status": "error", "message": "Invalid credentials"})

            elif action == "view_events":  # Handle request to view all events
                # ############################################################
                # ################ PATH TRAVERSAL VULNERABILITY ##############
                # ############################################################
                # This simulates a vulnerability where the system would read
                # event data from files based on user input without proper validation
                
                # For demonstration, we'll simulate the vulnerability with a comment
                # The actual vulnerability would be:
                # event_file = request.get("event_file", "events.txt")
                # with open(event_file, 'r') as f:  # Vulnerable to path traversal like "../../../etc/passwd"
                #     data = f.read()
                
                cursor.execute("SELECT * FROM events")  # Query all events from database
                events = cursor.fetchall()  # Get all rows from the query
                # Format events data for JSON serialization
                formatted_events = []
                for event in events:
                    formatted_events.append({
                        "id": event[0],
                        "name": event[1],
                        "available_tickets": event[2],
                        "vip_tickets": event[3],
                        "regular_cost": event[4],
                        "vip_cost": event[5]
                    })
                # Send success response with formatted events data
                send_response(client_socket, {"status": "success", "events": formatted_events})

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
                        send_response(client_socket, {"status": "error", "message": "Not enough points"})
                    elif ticket_type == "VIP" and vip_tickets <= 0:  # Check if VIP tickets are available
                        # Send error if VIP tickets sold out
                        send_response(client_socket, {"status": "error", "message": "VIP tickets sold out"})
                    elif ticket_type == "Regular" and available_tickets <= 0:  # Check if regular tickets are available
                        # Send error if regular tickets sold out
                        send_response(client_socket, {"status": "error", "message": "Regular tickets sold out"})
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
                        send_response(client_socket, {"status": "success", "message": f"{ticket_type} Ticket purchased for {ticket_cost} points"})
            elif action == "check_points":  # Handle request to check points balance
                user_id = request.get("user_id")  # Get user ID from request
                # Query user points
                cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()  # Get user data
                if user:  # Check if user exists
                    # Send success response with points balance
                    send_response(client_socket, {"status": "success", "points": user[0]})
            elif action == "add_funds":
                userid = request.get("userid")
                amount = request.get("amount")
                if amount <= 0:
                    send_response(client_socket, {"status": "error", "message": "Invalid amount"})
                else:
                    cursor.execute("UPDATE users SET points = points + ? WHERE id = ?", (amount, userid))
                    conn.commit()
                    send_response(client_socket, {"status": "success", "message": f"Added {amount} points to user {userid}"})
            elif action == "view_purchases":
                try:
                    user_id = request.get("user_id")
                    print(f"Processing view_purchases for user_id: {user_id}")  # Debug output
                    
                    if not user_id:
                        print("Error: Missing user_id in request")  # Debug output
                        send_response(client_socket, {"status": "error", "message": "User ID is required"})
                        return
                        
                    # First verify the user exists
                    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                    user_result = cursor.fetchone()
                    if not user_result:
                        print(f"Error: User {user_id} not found in database")  # Debug output
                        send_response(client_socket, {"status": "error", "message": "User not found"})
                        return

                    try:
                        # Check if purchases table exists
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchases'")
                        if not cursor.fetchone():
                            print("Error: Purchases table does not exist")  # Debug output
                            send_response(client_socket, {"status": "error", "message": "Purchases table does not exist"})
                            return
                            
                        # Check if events table exists
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
                        if not cursor.fetchone():
                            print("Error: Events table does not exist")  # Debug output
                            send_response(client_socket, {"status": "error", "message": "Events table does not exist"})
                            return
                    except sqlite3.Error as e:
                        print(f"Database error checking tables: {e}")  # Debug output
                        send_response(client_socket, {"status": "error", "message": f"Database error checking tables: {str(e)}"})
                        return

                    # Use LEFT JOIN to handle cases where event might have been deleted
                    try:
                        print("Executing purchases query...")  # Debug output
                        query = """
                            SELECT p.id, p.event_id, p.ticket_type, p.purchase_date, 
                                   COALESCE(e.name, 'Unknown Event') as event_name
                            FROM purchases p
                            LEFT JOIN events e ON p.event_id = e.id
                            WHERE p.user_id = ? 
                            ORDER BY p.id DESC
                        """
                        print(f"Query: {query}")  # Debug output
                        cursor.execute(query, (user_id,))
                        purchases = cursor.fetchall()
                        print(f"Found {len(purchases)} purchases")  # Debug output
                        
                        if not purchases:
                            send_response(client_socket, {"status": "success", "purchases": [], "message": "No purchases found"})
                        else:
                            send_response(client_socket, {"status": "success", "purchases": purchases})
                    except sqlite3.Error as e:
                        error_msg = f"Database error in purchases query: {str(e)}"
                        print(error_msg)  # Debug output
                        send_response(client_socket, {"status": "error", "message": error_msg})
                        return
                        
                except sqlite3.Error as e:
                    error_msg = f"Database error in view_purchases: {str(e)}"
                    print(error_msg)  # Debug output
                    send_response(client_socket, {"status": "error", "message": error_msg})
                except Exception as e:
                    error_msg = f"Error in view_purchases: {str(e)}"
                    print(error_msg)  # Debug output
                    send_response(client_socket, {"status": "error", "message": error_msg})
                
            # Add a diagnostic action
            elif action == "diagnose_db":
                try:
                    # Check all tables
                    tables_result = {}
                    for table in ["users", "events", "purchases"]:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]
                        tables_result[table] = {
                            "count": count,
                            "columns": columns
                        }
                    
                    # Test a sample query
                    test_query_result = {}
                    if tables_result["users"]["count"] > 0:
                        # Get a sample user
                        cursor.execute("SELECT id FROM users LIMIT 1")
                        test_user_id = cursor.fetchone()[0]
                        test_query_result["sample_user_id"] = test_user_id
                        
                        # Try the purchases query
                        try:
                            cursor.execute("""
                                SELECT p.id, p.event_id, p.ticket_type, p.purchase_date, 
                                       COALESCE(e.name, 'Unknown Event') as event_name
                                FROM purchases p
                                LEFT JOIN events e ON p.event_id = e.id
                                WHERE p.user_id = ? 
                                ORDER BY p.id DESC
                            """, (test_user_id,))
                            sample_purchases = cursor.fetchall()
                            test_query_result["sample_purchases_count"] = len(sample_purchases)
                            test_query_result["sample_purchase_data"] = sample_purchases[:1] if sample_purchases else []
                        except sqlite3.Error as e:
                            test_query_result["error"] = str(e)
                    
                    # Check foreign keys status
                    cursor.execute("PRAGMA foreign_keys")
                    foreign_keys_enabled = cursor.fetchone()[0]
                    
                    diagnosis = {
                        "tables": tables_result,
                        "test_query": test_query_result,
                        "foreign_keys_enabled": foreign_keys_enabled
                    }
                    
                    send_response(client_socket, {
                        "status": "success", 
                        "message": "Database diagnosis complete", 
                        "diagnosis": diagnosis
                    })
                except Exception as e:
                    send_response(client_socket, {
                        "status": "error", 
                        "message": f"Diagnosis error: {str(e)}"
                    })
                
        except Exception as e:  # Handle any exceptions that occur
            print("Error:", e)  # Print error to server console
            try:
                # Try to send error response to client
                send_response(client_socket, {"status": "error", "message": "An error occurred"})
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
