import socket # Python's built-in library for socket/network programming.
import threading # Python's library that lets multiple sections of program
# execute concurrently.

# ------------------------------------------------------------
# RECEIVE SERVER MESSAGES
# ------------------------------------------------------------
def receive_server_messages(data_connection_socket):
    try:
        while True:
            # Wait for a response/message from the server.
            response_bytes = data_connection_socket.recv(1024)

            # recv() returning b"" means the server closed the data connection.
            if not response_bytes:
                break

            # Convert the received bytes into a string.
            response = response_bytes.decode()
            print(response)

    # The data connection may be closed while this thread
    # is waiting inside recv().
    except OSError:
        pass

print("Starting client...")

# Variables initialized as None so they can safely
# be checked and closed later if something unexpected happens.
control_connection_socket = None
data_connection_socket = None
receiver_thread = None

try:
    # ------------------------------------------------------------
    # CREATE THE CLIENT'S CONTROL SOCKET
    # ------------------------------------------------------------
    # Ask the OS to create a TCP socket (networking endpoint).
    # The client will eventually use this control connection to send commands
    # such as:login, who, broadcast, private, and quit
    control_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # At this point, the control socket does not yet have the
    # client's IP address and a TCP port assigned by the OS.

    # ------------------------------------------------------------
    # RECEIVE AND PARSE THE CONNECT COMMAND
    # ------------------------------------------------------------
    while True:
        # The user enters a command typed (strings).
        user_input = input()
        command_parts = user_input.split()

        # Expected format: connect (ip address) (control_port)
        if len(command_parts) != 3:
            print("Invalid connect command.")
            continue

        # Separate the command into individual arguments.
        command = command_parts[0]

        if command != "connect":
            print("Invalid connect command.")
            continue

        server_ip_address = command_parts[1]

        try:
            # Command-line/user input is received as strings,
            # so the TCP port must be converted into an integer.
            server_control_port = int(command_parts[2])
        except ValueError:
            print("Invalid port.")
            continue

        # Valid connect command
        break

    # ------------------------------------------------------------
    # ESTABLISH THE CONTROL CONNECTION
    # ------------------------------------------------------------
    # Connect the client's control socket to server's control  socket
    control_connection_socket.connect((server_ip_address, server_control_port))
    # The client's OS automatically selects the available
    # ephemeral (random) source TCP port for the connection.

    # ------------------------------------------------------------
    # RECEIVE THE CONNECT RESPONSE
    # ------------------------------------------------------------
    # The server responds through the already-established
    # control TCP connection.
    connect_response_bytes = control_connection_socket.recv(1024)
    # Convert the received bytes into a Python string.

    connect_response = connect_response_bytes.decode()
    print(connect_response)

    # ------------------------------------------------------------
    # EXTRACT THE SERVER'S DATA PORT
    # ------------------------------------------------------------
    # The response format is:
    # Status Code
    #
    # Data
    # Split the string using "\n\n" as the separator but only once.
    status_code, server_data_port = connect_response.split("\n\n",1)
    server_data_port = int(server_data_port)

    # ------------------------------------------------------------
    # CREATE THE CLIENT'S DATA SOCKET
    # ------------------------------------------------------------
    # Ask the OS to create a new IPv4 TCP socket for data connection.
    # It will be used to receives server responses, broadcasts, private messages, etc.
    data_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # ------------------------------------------------------------
    # ESTABLISH THE DATA CONNECTION
    # ------------------------------------------------------------
    # Connect the client's data socket to the data port
    # that the server provided in the connect response.
    data_connection_socket.connect((server_ip_address, server_data_port))

    # ------------------------------------------------------------
    # START THE DATA RECEIVER THREAD
    # ------------------------------------------------------------
    receiver_thread = threading.Thread(
        target=receive_server_messages,
        args=(data_connection_socket,),
        daemon=True
    )

    receiver_thread.start()

    # ------------------------------------------------------------
    # SEND USER COMMANDS
    # ------------------------------------------------------------
    while True:
        # Wait for the user to enter a command.
        user_input = input()
        # Send entire command line through the control connection.
        control_connection_socket.sendall(user_input.encode())

        # command "quit" ends the client's command loop.
        if user_input.strip() == "quit":
            break

    # ------------------------------------------------------------
    # WAIT FOR THE FINAL SERVER RESPONSE BEFORE ACTUALLY QUITTING
    # ------------------------------------------------------------
    # Wait until the data receiver thread finishes.
    # The server will send the quit response and then close the data connection.
    receiver_thread.join()

except KeyboardInterrupt:
    pass
except OSError:
    pass

# ------------------------------------------------------------
# CLIENT CLEANUP
# ------------------------------------------------------------
finally:
    # Close the client's control socket if it was created.
    if control_connection_socket is not None:
        try:
            control_connection_socket.close()
        except OSError:
            pass

    # Close the client's data socket if it was created.
    if data_connection_socket is not None:
        try:
            data_connection_socket.close()
        except OSError:
            pass