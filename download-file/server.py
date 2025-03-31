import socket
import os

def send_file_chunked(client_socket: socket.socket, addr, file_path: str):
    """
    Send a file over a socket connection in chunks.
    Uses manual chunked encoding similar to HTTP chunked transfer.

    Format:
    [chunk size in hex (2 bytes)][chunk data]
    ...
    00 (to indicate end of transmission)
    """
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(16)
                if not chunk:
                    break

                chunk_size_hex = f"{len(chunk):02X}".zfill(2).encode()
                client_socket.send(chunk_size_hex)
                client_socket.send(chunk)
                
                print(f"Sending chunk size: {chunk_size_hex.decode()}, Data: {chunk}")

        client_socket.send(b"00")
        print(f"File {file_path} sent to {addr}")

    except Exception as e:
        print(f"Error sending file: {e}")

def start_server(host='0.0.0.0', port=12345, file_path=None):
    """Start a socket server that sends a file in chunks when clients connect."""
    if not file_path or not os.path.exists(file_path):
        print("Error: Please provide a valid file path")
        return

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server started on {host}:{port}")
        print(f"Serving file: {file_path}")

        while True:
            print("Waiting for connection...")
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")

            send_file_chunked(conn, addr, file_path)

            conn.close()
            print(f"Connection from {addr} closed")

    except KeyboardInterrupt:
        print("\nServer shutdown requested")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()
        print("Server stopped")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "file.txt")
    start_server(port=12345, file_path=file_path)