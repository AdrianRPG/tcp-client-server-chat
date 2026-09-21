import socket # Python's built-in library for socket/network programming.
import sys # Python's library that provides access to command-line arguments.
import threading # Python's library that lets multiple sections of program
# execute concurrently.

# ------------------------------------------------------------
# READ THE CONTROL PORT FROM THE COMMAND LINE
# ------------------------------------------------------------
# Check command formatting is good
if len(sys.argv) != 2:
    print("Usage: python server.py <control_port>")
    sys.exit(1)

# Command-line arguments are received as strings.
control_port = int(sys.argv[1]) # Therefore, convert the string argument into an integer.

print("Starting server...")

# ------------------------------------------------------------
# CREATE THE CONTROL LISTENING SOCKET
# ------------------------------------------------------------
# This socket will only be used to LISTEN for new connections.

# Ask the OS to create an IPv4 TCP socket (networking endpoint).
control_listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Arguments: AF_INET --→ IPv4; SOCK_STREAM --→ TCP
# Socket does not yet have the server's IP address and TCP control_port.
print("Creating server socket")

# ------------------------------------------------------------
# BIND THE CONTROL LISTENING SOCKET
# ------------------------------------------------------------
# Associate the control listening socket with the server's IP address and TCP control_port.
control_listening_socket.bind(("0.0.0.0", control_port))
# 0.0.0.0 --> Listen for connections on all available IPv4 network interfaces.

# ------------------------------------------------------------
# START LISTENING FOR CONTROL CONNECTIONS
# ------------------------------------------------------------
# Put the control socket into listening mode.
# The socket is now waiting for incoming TCP control connection requests from clients.
control_listening_socket.listen()
print("Awaiting connections...")

# Stores all currently logged-in clients in a Python dictionary.
# USERNAME -> CLIENT INFORMATION (Control Socket , Data Socket)
active_clients = {} # No users logged in yet.

# Dictionary's protection for race condition when multiple threads
# try to modify it at the same time.
active_clients_lock = threading.Lock()

# ------------------------------------------------------------
# CLEAN UP A CLIENT
# ------------------------------------------------------------

def cleanup_client(client_username,control_connection_socket,data_connection_socket):
    # Indicates whether this client had actually completed LOGIN.
    was_active = False
    # Snapshot of clients that remain logged in.
    clients_snapshot = []

    # --------------------------------------------------------
    # REMOVE CLIENT FROM ACTIVE CLIENTS
    # --------------------------------------------------------
    if client_username is not None:
        with active_clients_lock:
            # Only remove the user if they are still registered.
            if client_username in active_clients:
                active_clients.pop(client_username)
                was_active = True
                # Take a snapshot AFTER removing the disconnected user.
                clients_snapshot = list(active_clients.values())

    # --------------------------------------------------------
    # BROADCAST LOGOUT NOTIFICATION
    # --------------------------------------------------------
    # Only broadcast logout if the client had successfully
    # logged in and was registered in active_clients.
    if was_active:
        logout_notification = f"200\n\nlogout\n{client_username}"

        # Send the logout notification to every remaining client.
        for client_info in clients_snapshot:
            try:
                client_info["data_socket"].sendall(logout_notification.encode())

            except OSError:
                pass

    # --------------------------------------------------------
    # CLOSE THIS CLIENT'S CONTROL SOCKET
    # --------------------------------------------------------
    try:
        control_connection_socket.close()
    except OSError:
        pass

    # --------------------------------------------------------
    # CLOSE THIS CLIENT'S DATA SOCKET
    # --------------------------------------------------------
    if data_connection_socket is not None:
        try:
            data_connection_socket.close()
        except OSError:
            pass

# ------------------------------------------------------------
# HANDLE PROCESS FOR EACH CLIENT (CONCURRENTLY)
# ------------------------------------------------------------

def handle_client(control_connection_socket, client_control_address):

    client_username = None
    data_connection_socket = None
    data_listening_socket = None

    try:

        # ------------------------------------------------------------
        # CREATE THE DATA LISTENING SOCKET
        # ------------------------------------------------------------
        # Ask the OS to create a new TCP socket (networking endpoint) for the server.
        # This will listen for incoming TCP data connection requests from clients.
        data_listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print("Connection requested. Creating data socket")

        # ------------------------------------------------------------
        # BIND THE DATA LISTENING SOCKET
        # ------------------------------------------------------------
        # Associates the data socket with the server's IP address.
        # The server asks the OS for any available TCP port.
        data_listening_socket.bind(("0.0.0.0", 0))

        # ------------------------------------------------------------
        # START LISTENING FOR THE DATA CONNECTION
        # ------------------------------------------------------------
        data_listening_socket.listen()

        # ------------------------------------------------------------
        # FIND THE DATA PORT SELECTED BY THE OS
        # ------------------------------------------------------------
        # Use getsockname() to get the information address (IP[0] & port[1]) of the socket.
        data_port = data_listening_socket.getsockname()[1]

        # ------------------------------------------------------------
        # SEND THE DATA PORT TO THE CLIENT
        # ------------------------------------------------------------
        # The server needs to sends the data port through the already
        # established control connection sockets.
        response = f"200\n\n{data_port}"
        control_connection_socket.sendall(response.encode())

        # ------------------------------------------------------------
        # ACCEPT THE CLIENT'S DATA CONNECTION
        # ------------------------------------------------------------
        # The client will create a second TCP data socket and connect it to
        # the data port that the server just sent.
        # accept() then returns a NEW connected data socket for the server dedicated to
        # the data connection.
        data_connection_socket, client_data_address = data_listening_socket.accept()
        # The listening socket is no longer needed after this client's
        # data connection is established.
        data_listening_socket.close() # Close temporary socket.
        data_listening_socket = None

        # ------------------------------------------------------------
        # RECEIVE LOGIN COMMAND
        # ------------------------------------------------------------
        while True:
            # The server receives the login command through the control TCP connection.
            login_request_bytes = control_connection_socket.recv(1024)

            if not login_request_bytes:
                return

            # Convert the received bytes into a Python string.
            login_request = login_request_bytes.decode().strip()

            # ------------------------------------------------------------
            # EXTRACT THE CLIENT'S USERNAME
            # ------------------------------------------------------------
            # The login command format is:
            # login username
            # Split the string using " " as the separator but only once.
            login_parts = login_request.split(" ", 1)

            # A valid login command must contain: login <username>
            if len(login_parts) != 2:
                data_connection_socket.sendall("500\n\n".encode())
                continue

            command = login_parts[0]
            requested_username = login_parts[1].strip()

            # The command must be "login", and username cannot be empty.
            if command != "login" or requested_username == "":
                data_connection_socket.sendall("500\n\n".encode())
                continue

            # ------------------------------------------------------------------
            # VALIDATE USERNAME UNIQUENESS
            # ------------------------------------------------------------------
            with active_clients_lock:
                if requested_username in active_clients:
                # Username is already being used.
                    username_available = False
                else:
                    # Register the newly logged-in client.
                    active_clients[requested_username] = {"control_socket": control_connection_socket,
                        "data_socket": data_connection_socket}
                    username_available = True

            # Username already exists.
            if not username_available:
                login_response = "500\n\n"
                # Send the login response through the data TCP connection.
                data_connection_socket.sendall(login_response.encode())
                # Stop processing THIS login request.
                # Go back to the beginning of the login loop.
                continue

            # Username is unique and login was successful.
            client_username = requested_username
            login_response = "200\n\n"
            data_connection_socket.sendall(login_response.encode())
            print(f"Login requested by: {client_username}")

            # --------------------------------------------------------
            # BROADCAST JOIN NOTIFICATION
            # --------------------------------------------------------
            join_notification = f"200\n\njoin\n{client_username}"

            with active_clients_lock:
                # values() provides the items for each key (a special dictionary view).
                # Therefore, we have to list them.
                clients_snapshot = [client_info for username,
                client_info in active_clients.items()
                    if username != client_username]

            # Application-level broadcasting
            for client_info in clients_snapshot:
                client_info["data_socket"].sendall(join_notification.encode())

            # Exit the login loop and proceed to normal commands.
            break

        # --------------------------------------------------------
        # RECEIVE AND PARSE COMMAND LOOP
        # --------------------------------------------------------
        while True:
            # Wait for the next command through the CONTROL connection.
            request_bytes = (control_connection_socket.recv(1024))
            if not request_bytes:
                break
            # Convert the received bytes into a string.
            request = request_bytes.decode().strip()

            if request == "":
                data_connection_socket.sendall("500\n\n".encode())
                continue

            # Split the string using " " as the separator but only once.
            command_parts = request.split(" ", 1)
            command = command_parts[0]

            # ----------------------------------------------------
            # WHO COMMAND
            # ----------------------------------------------------
            if command == "who":

                if len(command_parts) != 1:
                    data_connection_socket.sendall("500\n\n".encode())
                    continue

                # Take a snapshot of the currently logged-in usernames.
                with active_clients_lock:
                    current_users = list(active_clients.keys())

                # Convert:["alice", "bob", "charlie"]
                # into: "alice,bob,charlie"
                users_list = ", ".join(current_users)

                print("Who requested. Sending users.")

                # Construct the WHO response.
                who_response = f"200\n\n{users_list}"

                # Send the response only to the client who requested the command WHO.
                data_connection_socket.sendall(who_response.encode())

            # ----------------------------------------------------
            # BROADCAST COMMAND
            # ----------------------------------------------------
            elif command == "broadcast":
                if len(command_parts) != 2:
                    data_connection_socket.sendall("500\n\n".encode())
                    continue
                # Extract the message after the word "broadcast".
                message = command_parts[1].strip()

                if message == "":
                    data_connection_socket.sendall("500\n\n".encode())
                    continue

                print(f"Broadcast requested by {client_username}")
                print(f"Message: {message}")

                # Already know who sent the command because this thread is for a particular client:
                # Construct the message that every active client receives.
                broadcast_response = f"200\n\nBroadcast\n{client_username}\n{message}"
                with active_clients_lock:
                    # information of all clients (data sockets)
                    clients_snapshot = list(active_clients.values())
                # broadcast: send the message to every client's data socket.
                for client_info in clients_snapshot:
                    client_info["data_socket"].sendall(broadcast_response.encode())

            # ----------------------------------------------------
            # PRIVATE COMMAND
            # ----------------------------------------------------
            elif command == "private":
                if len(command_parts) != 2:
                    data_connection_socket.sendall("500\n\n".encode())
                    continue

                # command_parts[1] contains private information: specified recipient and message
                private_parts = command_parts[1].split(" ", 1)

                if len(private_parts) != 2:
                    data_connection_socket.sendall("500\n\n".encode())
                    continue

                # Extract the recipient's username and the message.
                target_recipient = private_parts[0].strip()
                message = private_parts[1].strip()

                print(f"Private message from {client_username} to {target_recipient}")

                if target_recipient == "" or message == "":
                    data_connection_socket.sendall("500\n\n".encode())
                    continue

                # Safely look for the recipient in active_clients.
                with active_clients_lock:
                    target_client = active_clients.get(target_recipient)

                # ------------------------------------------------
                # IF RECIPIENT DOES NOT EXIST
                # ------------------------------------------------
                if target_client is None:
                    # Notify the sender that the private command failed.
                    private_response = "500\n\n"
                    data_connection_socket.sendall(private_response.encode())

                # ------------------------------------------------
                # RECIPIENT EXISTS
                # ------------------------------------------------
                else:
                    # Get the data socket of the recipient.
                    target_data_socket = target_client["data_socket"]

                    # Construct the private message for the recipient.
                    private_message = f"200\n\nPrivate\n{client_username}\n{message}"

                    # Send the private message only to the recipient.
                    target_data_socket.sendall(private_message.encode())

                    # Confirm success to the sender.
                    sender_response = "200\n\n"
                    data_connection_socket.sendall(sender_response.encode())

            # ----------------------------------------------------
            # QUIT COMMAND
            # ----------------------------------------------------
            elif command == "quit":
                if len(command_parts) != 1:
                    data_connection_socket.sendall("500\n\n".encode())
                    continue
                # Send success response to client
                print(f"Quit requested by {client_username}")
                quit_response = "200\n\n"
                data_connection_socket.sendall(quit_response.encode())
                return

            # For completely unknown commands.
            else:
                data_connection_socket.sendall("500\n\n".encode())

    # ------------------------------------------------------------
    # UNEXPECTED CLIENT DISCONNECTION
    # ------------------------------------------------------------
    except OSError:
        print("Client disconnected unexpectedly:", client_control_address)

    # ------------------------------------------------------------
    # ALWAYS CLEAN UP THIS CLIENT
    # ------------------------------------------------------------
    finally:
    # If something failed before the data connection was accepted,
    # close the temporary data listening socket too.
        if data_listening_socket is not None:
            try:
                data_listening_socket.close()
            except OSError:
                pass

        # Remove client from active_clients if necessary,
        # broadcast logout, and close CONTROL/DATA sockets.
        cleanup_client(
            client_username,
            control_connection_socket,
            data_connection_socket
        )

# ------------------------------------------------------------
# ACCEPT CLIENTS CONTROL CONNECTION
# ------------------------------------------------------------

# MAIN THREAD: Keep accepting new CONTROL connections and give each
# one to a separate worker thread.
while True:
    # When the client successfully connects, accept() returns
    # a new connected TCP socket to communicate with this client.
    control_connection_socket, client_control_address = control_listening_socket.accept()
    # client_control_address contains information about the client (IP address
    # and random TCP Port assigned by OS)

    client_thread = threading.Thread( #Creates a Thread object
        # When threat started, run function with specified args.
        target=handle_client,
        args=(control_connection_socket, client_control_address)
    )

    client_thread.start()