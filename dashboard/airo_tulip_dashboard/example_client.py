"""An example client that takes input from stdin and sends it to the server."""

import socket

def client_loop(host: str = 'localhost', port: int = 49790):
    # Open a TCP socket and connect to the server.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))

        # Read input from stdin and send it to the server.
        while True:
            message = input("Enter a message: ")
            if message == 'exit':
                break
            if len(message) >= 1024:
                print("Message too long. Please enter a message with less than 1024 characters.")
                continue
            s.sendall(message.encode())
            response = s.recv(1024)
            print("Sent message to server.")
            print(f"Response: {response}")


if __name__ == '__main__':
    client_loop()