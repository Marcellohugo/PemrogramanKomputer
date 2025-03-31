import socketserver
import threading
import os

class ChatHandler(socketserver.BaseRequestHandler):
    active_clients = []
    lock = threading.Lock()

    def handle(self):
        self.buffer = b''
        self.upload_state = 'normal'
        self.upload_filename = None
        self.upload_file_size = 0
        self.upload_received = 0
        self.upload_file_data = b''

        with self.lock:
            self.active_clients.append(self)
        print(f"New client connected: {self.client_address}")
        try:
            while True:
                data = self.request.recv(4096)
                if not data:
                    break
                self.buffer += data
                self.process_buffer()
        finally:
            with self.lock:
                self.active_clients.remove(self)
            print(f"Client disconnected: {self.client_address}")

    def process_buffer(self):
        while True:
            if self.upload_state == 'normal':
                newline_pos = self.buffer.find(b'\n')
                if newline_pos == -1:
                    break
                line = self.buffer[:newline_pos].decode().strip()
                self.buffer = self.buffer[newline_pos+1:]
                self.handle_line(line)
            elif self.upload_state == 'upload_size':
                newline_pos = self.buffer.find(b'\n')
                if newline_pos == -1:
                    break
                size_line = self.buffer[:newline_pos].decode().strip()
                self.buffer = self.buffer[newline_pos+1:]
                try:
                    self.upload_file_size = int(size_line)
                    self.upload_state = 'upload_data'
                    self.upload_received = 0
                    self.upload_file_data = b''
                except ValueError:
                    self.request.sendall(b"ERROR Invalid file size\n")
                    self.upload_state = 'normal'
            elif self.upload_state == 'upload_data':
                remaining = self.upload_file_size - self.upload_received
                chunk = self.buffer[:remaining]
                self.upload_file_data += chunk
                self.upload_received += len(chunk)
                self.buffer = self.buffer[remaining:]
                if self.upload_received >= self.upload_file_size:
                    os.makedirs('uploads', exist_ok=True)  # Pastikan folder 'uploads' ada
                    file_path = os.path.join('uploads', self.upload_filename)
                    with open(file_path, 'wb') as f:
                        f.write(self.upload_file_data)
                    print(f"File {file_path} received successfully")
                    self.broadcast(f"File {self.upload_filename} uploaded", exclude_self=True)
                    self.upload_state = 'normal'
                else:
                    break

    def handle_line(self, line):
        if line.startswith('/upload'):
            parts = line.split()
            if len(parts) < 2:
                self.request.sendall(b"ERROR Missing filename\n")
                return
            self.upload_filename = parts[1]
            self.upload_state = 'upload_size'
        elif line.startswith('/download'):
            parts = line.split()
            if len(parts) < 2:
                self.request.sendall(b"ERROR Missing filename\n")
                return
            filename = os.path.join('uploads', parts[1])  # Ambil dari folder 'uploads'
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                self.request.sendall(f"FILE {parts[1]} {file_size}\n".encode())
                try:
                    with open(filename, 'rb') as f:
                        while chunk := f.read(4096):  # Kirim file dalam potongan 4KB
                            self.request.sendall(chunk)
                    print(f"File {filename} sent successfully")
                except (ConnectionResetError, BrokenPipeError):
                    print(f"Client disconnected while downloading {filename}")
            else:
                self.request.sendall(b"ERROR File not found\n")
        elif line == '/list':
            client_list = [str(client.client_address) for client in ChatHandler.active_clients]
            self.request.sendall('\n'.join(client_list).encode() + b'\n')
        else:
            print(f"Received {line} from {self.client_address}")
            self.broadcast(f"{self.client_address}: {line}", exclude_self=True)

    def broadcast(self, message, exclude_self=False):
        with self.lock:
            for client in self.active_clients:
                if client == self and exclude_self:
                    continue
                try:
                    client.request.sendall(message.encode() + b'\n')
                except:
                    pass

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    HOST, PORT = "localhost", 9999
    server = ThreadingTCPServer((HOST, PORT), ChatHandler)
    print(f"Server started on {HOST}:{PORT}")
    server.serve_forever()