import socket
import threading
import os

class Client:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        print(f"Connected to {host}:{port}")
        self.current_file = None  # State untuk file yang sedang diterima
        self.receive_thread = threading.Thread(target=self.receive)
        self.receive_thread.start()
        self.send_commands()

    def receive(self):
        buffer = b''
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            buffer += data

            while True:
                if self.current_file:
                    # Menerima data file yang sedang berlangsung
                    remaining = self.current_file['size'] - self.current_file['received']
                    chunk = buffer[:remaining]
                    self.current_file['received'] += len(chunk)
                    self.current_file['buffer'] += chunk
                    buffer = buffer[len(chunk):]

                    if self.current_file['received'] >= self.current_file['size']:
                        # Simpan file
                        os.makedirs('downloads', exist_ok=True)
                        filename = self.current_file['filename']
                        with open(f'downloads/{filename}', 'wb') as f:
                            f.write(self.current_file['buffer'])
                        print(f"File received successfully: downloads/{filename}")
                        self.current_file = None
                    else:
                        print(f"Receiving file: {self.current_file['filename']} ({self.current_file['received']}/{self.current_file['size']} bytes)")
                        break  # Menunggu data lebih lanjut
                else:
                    # Cek header FILE atau pesan teks
                    if buffer.startswith(b'FILE '):
                        newline = buffer.find(b'\n')
                        if newline == -1:
                            break  # Header belum lengkap
                        header = buffer[:newline].decode().strip().split()
                        if len(header) < 3:
                            buffer = buffer[newline+1:]
                            continue
                        _, filename, size_str = header[:3]
                        try:
                            size = int(size_str)
                        except ValueError:
                            buffer = buffer[newline+1:]
                            continue
                        buffer = buffer[newline+1:]
                        self.current_file = {
                            'filename': filename,
                            'size': size,
                            'received': 0,
                            'buffer': b''
                        }
                    else:
                        # Proses pesan teks
                        newline = buffer.find(b'\n')
                        if newline == -1:
                            break
                        line_bytes = buffer[:newline]
                        buffer = buffer[newline+1:]
                        try:
                            line = line_bytes.decode()
                            print(line)
                        except UnicodeDecodeError:
                            print("Received non-text data, skipping...")
                if not buffer:
                    break

    def send_commands(self):
        while True:
            cmd = input()
            if cmd.startswith('/upload '):
                filename = cmd.split()[1]
                filepath = os.path.join('files', filename)
                try:
                    with open(filepath, 'rb') as f:
                        data = f.read()
                    self.sock.sendall(f"/upload {filename}\n".encode())
                    self.sock.sendall(f"{len(data)}\n".encode())
                    self.sock.sendall(data)
                    print(f"File '{filename}' uploaded successfully from 'files/'")
                except FileNotFoundError:
                    print(f"File '{filename}' not found in 'files/'")
            elif cmd.startswith('/download '):
                self.sock.sendall(cmd.encode() + b'\n')
            else:
                self.sock.sendall(cmd.encode() + b'\n')

if __name__ == "__main__":
    Client('localhost', 9999)