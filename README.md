# TCP Client-Server Chat Application

A concurrent TCP client-server chat application implemented in Python using low-level socket programming. The application supports multiple simultaneous clients, runtime username registration, connected-user discovery, broadcast messaging, private messaging, and separate **CONTROL** and **DATA** TCP connections.

---

## Project Overview

This project was developed as part of **CNT 4713 – Net-Centric Computing** at **Florida International University (FIU)** under Professor **Xavier Caddle**.

The project focuses on the design and implementation of a TCP-based chat system using Python's built-in socket programming capabilities without external messaging frameworks.

The application consists of two independent programs:

- **`server.py`** — manages TCP connections, active users, concurrent clients, message routing, and client lifecycle events.
- **`client.py`** — connects to the server, sends application commands through the CONTROL connection, and receives responses and messages through the DATA connection.

---

## Objective

The primary objective of this project was to apply core computer networking concepts by building an application directly on top of TCP sockets.

The project was designed to demonstrate:

- TCP client-server communication
- Multiple concurrent client connections
- Separation of command and response traffic
- Application-layer protocol design
- Runtime user registration
- Broadcast and private message delivery
- Thread-safe shared-state management
- Client connection and disconnection handling

---

## Technologies & Tools

- **Python 3**
- **Python `socket` library**
- **Python `threading` library**
- **TCP/IP**
- **PyCharm**

---

## Architecture

Each connected client uses two TCP connections with the server:

```text
                     TCP Chat Server
                 ┌─────────────────────┐
                 │                     │
Client ─────────►│  CONTROL Connection │
Commands         │                     │
                 │                     │
Client ◄─────────│    DATA Connection  │
Responses        │                     │
                 └─────────────────────┘
```

### CONTROL Connection

The **CONTROL connection** is established first and lets the client send commands to the server.

Supported commands include:

```text
login <username>
who
broadcast <message>
private <username> <message>
quit
```

### DATA Connection

After the CONTROL connection is established, the server creates a temporary DATA listening socket. The operating system dynamically selects an available TCP port, which the server communicates to the client through the CONTROL connection. The client then establishes a second TCP connection using that DATA port.

The **DATA connection** is used for:

- Server responses
- Broadcast messages
- Private messages
- User join notifications
- User logout notifications

---

## Key Concepts Implemented

### TCP Socket Programming

The project implements the TCP socket lifecycle using operations such as:

```text
socket()
bind()
listen()
accept()
connect()
sendall()
recv()
close()
```

The implementation distinguishes between:

- **Listening sockets**, which wait for incoming TCP connection requests.
- **Connected sockets**, which handle communication with individual clients.

---

### Dynamic DATA Port Allocation

The server creates a temporary DATA listening socket and binds it to port `0`.

```python
data_listening_socket.bind(("0.0.0.0", 0))
```

Using port `0` allows the operating system to dynamically select an available TCP port. The selected port is then retrieved using:

```python
data_port = data_listening_socket.getsockname()[1]
```

The server communicates this port to the client through the already-established CONTROL connection. Once the client establishes its DATA connection, the temporary DATA listening socket is closed.

---

### Concurrent Client Handling

The server supports multiple simultaneous clients using Python threads. Each accepted CONTROL connection is assigned to a separate worker thread:

```python
client_thread = threading.Thread(
    target=handle_client,
    args=(control_connection_socket, client_control_address)
)

client_thread.start()
```

This allows the main server process to continue accepting new clients while existing clients independently send commands and receive messages.

---

### Thread-Safe Shared State

Connected users are stored in a shared dictionary:

```python
active_clients = {}
```

Each username is associated with that client's CONTROL and DATA sockets. Because multiple client threads may access or modify this dictionary at the same time, the server protects critical operations using:

```python
active_clients_lock = threading.Lock()
```

This helps prevent race conditions when clients log in, disconnect, or request information about currently connected users.

---

### Application-Layer Protocol

The application implements a lightweight protocol using status codes. Successful operations return:

```text
200
```

Failed or invalid operations return:

```text
500
```

This creates a simple structured protocol on top of TCP.

---

### Unique Username Registration

Clients register a runtime username using:

```text
login <username>
```

The server validates username uniqueness while protecting the shared client registry with a lock. If the username is already in use, the server rejects the login attempt with:

```text
500
```

If the username is available, the client is registered and receives:

```text
200
```

The implementation distinguishes between a **requested username** and an **authenticated username**, ensuring that failed duplicate-login attempts cannot affect already connected users.

---

### User Join Notifications

When a client successfully logs in, the server notifies other connected users.

```text
200

join
alice
```

The newly logged-in client is excluded from its own JOIN notification because it has already received the successful login response.

---

### Connected User Discovery

The `who` command allows a client to request the list of currently connected users. The server retrieves a snapshot of the active usernames and returns them through the requesting client's DATA connection.

```text
200

bob, alice, mallory
```

---

### Broadcast Messaging

Clients can send a message to every currently connected user using:

```text
broadcast <message>
```

The server creates a snapshot of the current active clients and sends the broadcast through each client's DATA connection, including the sender.

```text
200

Broadcast
alice
Hello everyone!
```

---

### Private Messaging

Clients can send a message to one specific connected user using:

```text
private bob Meet after class.
```

If the recipient exists, only that client's DATA socket receives the message:

```text
200

Private
alice
Meet after class.
```

The sender receives a success response. If the requested recipient does not exist, the server returns a failed response.

---

### Client Lifecycle Management

The server performs centralized cleanup when a client quits or disconnects. This includes:

- Removing the authenticated username from the active-client registry
- Closing the client's CONTROL socket
- Closing the client's DATA socket
- Notifying remaining users that the client has disconnected

Example logout notification:

```text
200

logout
alice
```

The design also allows a username to become available again after the previous user disconnects.

---

### Command Validation

The server validates the structure of every supported command before processing it.

Examples of malformed requests include:

```text
broadcast
private bob
who extra
quit extra
```

Invalid commands return:

```text
500
```

without terminating the active client session. For this, the application uses limited string splitting to preserve messages containing spaces.

For example:

```python
command_parts = request.split(" ", 1)
```

This separates the command name from the remaining content without breaking multi-word messages.

---

## Supported Commands

| Command | Description |
|---|---|
| `login <username>` | Registers a unique username with the server |
| `who` | Returns the usernames of currently connected clients |
| `broadcast <message>` | Sends a message to all connected clients |
| `private <username> <message>` | Sends a message to one specified client |
| `quit` | Disconnects the client from the server |

---

## Running the Project

### 1. Start the Server

Run:

```bash
python server.py <control_port>
```

Example:

```bash
python server.py 8991
```

The CONTROL port is selected at runtime by the person running the server.

---

### 2. Start a Client

Open another terminal and run:

```bash
python client.py
```

---

### 3. Connect to the Server

```text
connect <server_ip_address> <control_port>
```

For local testing:

```text
connect 127.0.0.1 8991
```

For communication between different machines, replace the address with the appropriate server IP.

---

### 4. Log In

Register a username:

```text
login <username>
```

Each active client must use a unique username.

---

### 5. Use Chat Commands

Examples:

```text
who
```

```text
broadcast Hello everyone!
```

```text
private bob Meet after class.
```

```text
quit
```

---

### 6. Start Additional Clients

Open additional terminals and run:

```bash
python client.py
```

Each client connects using the IP address and CONTROL port of the running server and registers a unique username.

---

## Testing

The final implementation was tested using multiple concurrent clients.

Testing included:

- Multiple simultaneous TCP clients
- Successful user login
- Duplicate username rejection
- Connected-user listing with `who`
- Broadcast messaging
- Private messaging
- Invalid private-message recipients
- Malformed command handling
- Normal client logout
- Unexpected client disconnection
- JOIN and LOGOUT notifications
- Username reuse after disconnection
- Continued operation of remaining clients after another client disconnects

A final system test was performed using three simultaneous clients: Alice, Bob, and Mallory. The clients successfully remained connected while executing broadcast, private messaging, user discovery, login validation, and disconnection operations.

---

## Skills Demonstrated

- TCP/IP networking
- Socket programming
- Network programming
- Client-server architecture
- Concurrent programming
- Multithreading
- Thread synchronization
- Shared-state management
- Application-layer protocol design
- Dynamic TCP port allocation
- Message routing
- Input validation
- Client lifecycle management
- Network debugging
- Multi-client system testing
- Git-based version control

---

## Academic Context & Attribution

This project originated from a course assignment for **CNT 4713 – Net-Centric Computing** at **Florida International University (FIU)**, taught by Professor **Xavier Caddle**. This repository contains my implementation and technical documentation created for professional portfolio purposes. The repository is intended to demonstrate practical experience with TCP networking, socket programming, concurrent systems, and application-layer protocol design.
