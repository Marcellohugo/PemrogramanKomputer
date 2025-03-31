import socket
import os

def recv_chunked(sock: socket.socket, output_file: str = None):
    """
    Receive all data using chunked transfer encoding.

    Args:
        sock: The socket object
        output_file: Optional file path to save the received data

    Returns:
        Total bytes received
    """
    total_bytes = 0
    received_data = b""

    try:
        while True:
            chunk_size_hex = sock.recv(2)
            if not chunk_size_hex:
                break

            chunk_size = int(chunk_size_hex.decode(), 16)
            if chunk_size == 0:
                print("End of transmission (chunk size 00)")
                break

            chunk = b""
            while len(chunk) < chunk_size:
                part = sock.recv(chunk_size - len(chunk))
                if not part:
                    raise ConnectionError("Connection lost during transmission")
                chunk += part

            received_data += chunk
            total_bytes += len(chunk)

            print(f"Received chunk size: {chunk_size}, Data: {chunk.decode(errors='ignore')}")

        # Simpan ke file jika diperlukan
        if output_file:
            with open(output_file, "wb") as f:
                f.write(received_data)

    except Exception as e:
        print(f"Error receiving file: {e}")

    return total_bytes

def start_client(host='localhost', port=12345, output_file="received_file.txt"):
    """Connect to the server and receive the file in chunks."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"Connecting to {host}:{port}...")
        sock.connect((host, port))
        print("Connected. Receiving file...")

        total_bytes = recv_chunked(sock, output_file)

        print(f"Transfer complete. Received {total_bytes} bytes total.")
        if output_file:
            print(f"File saved to: {os.path.abspath(output_file)}")

    except ConnectionRefusedError:
        print(f"Connection refused. Make sure the server is running at {host}:{port}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    # Set default values
    host = 'localhost'
    port = 12345
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(current_dir, "received_file.txt")

    print(f"Client configured to connect to {host}:{port} and save to {output_file}")
    start_client(host, port, output_file)