import select
import socket
import os

class SelectServer:
    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        self.inputs = [self.server]
        self.clients = {}
        print(f"Server started on {host}:{port}")

    def broadcast(self, message, exclude=None):
        for sock in self.inputs:
            if sock != self.server and sock != exclude:
                try:
                    sock.sendall(message.encode() + b'\n')
                except:
                    pass

    def handle_client(self, sock):
        try:
            data = sock.recv(4096)
            if not data:
                raise ConnectionResetError  # Tangani klien yang terputus
            client_state = self.clients.get(sock, {'buffer': b'', 'state': 'normal'})
            client_state['buffer'] += data

            if client_state['state'] == 'normal':
                if b'\n' in client_state['buffer']:
                    line, rest = client_state['buffer'].split(b'\n', 1)
                    line = line.decode().strip()
                    client_state['buffer'] = rest
                    if line.startswith('/upload'):
                        parts = line.split()
                        if len(parts) < 2:
                            sock.sendall(b"ERROR Missing filename\n")
                            return
                        filename = parts[1]
                        client_state['state'] = 'upload_size'
                        client_state['filename'] = os.path.join('uploads', filename)  # Simpan di folder 'uploads'
                    elif line.startswith('/download'):
                        parts = line.split()
                        if len(parts) < 2:
                            sock.sendall(b"ERROR Missing filename\n")
                            return
                        filename = os.path.join('uploads', parts[1])  # Ambil dari folder 'uploads'
                        if os.path.exists(filename):
                            file_size = os.path.getsize(filename)
                            sock.sendall(f"FILE {parts[1]} {file_size}\n".encode())
                            with open(filename, 'rb') as f:
                                sock.sendall(f.read())
                            print(f"File {filename} sent successfully")
                        else:
                            sock.sendall(b"ERROR File not found\n")
                    elif line == '/list':
                        clients = [str(s.getpeername()) for s in self.inputs if s != self.server]
                        sock.sendall('\n'.join(clients).encode() + b'\n')
                    else:
                        self.broadcast(f"{sock.getpeername()}: {line}", exclude=sock)
            elif client_state['state'] == 'upload_size':
                if b'\n' in client_state['buffer']:
                    size_line, rest = client_state['buffer'].split(b'\n', 1)
                    try:
                        file_size = int(size_line.decode().strip())
                    except ValueError:
                        sock.sendall(b"ERROR Invalid file size\n")
                        client_state['state'] = 'normal'
                        return
                    client_state['file_size'] = file_size
                    client_state['buffer'] = rest
                    client_state['state'] = 'upload_data'
                    client_state['received'] = 0
            elif client_state['state'] == 'upload_data':
                remaining = client_state['file_size'] - client_state['received']
                chunk = client_state['buffer'][:remaining]
                client_state['received'] += len(chunk)
                client_state['buffer'] = client_state['buffer'][remaining:]
                if 'file_data' not in client_state:
                    client_state['file_data'] = chunk
                else:
                    client_state['file_data'] += chunk
                if client_state['received'] >= client_state['file_size']:
                    os.makedirs('uploads', exist_ok=True)  # Pastikan folder 'uploads' ada
                    with open(client_state['filename'], 'wb') as f:
                        f.write(client_state['file_data'])
                    print(f"File {client_state['filename']} received successfully")
                    self.broadcast(f"File {os.path.basename(client_state['filename'])} uploaded", exclude=sock)
                    client_state['state'] = 'normal'
                    del client_state['file_size'], client_state['received'], client_state['file_data'], client_state['filename']
            self.clients[sock] = client_state
        except (ConnectionResetError, BrokenPipeError):
            print(f"Client disconnected: {sock.getpeername()}")
            self.inputs.remove(sock)
            if sock in self.clients:
                del self.clients[sock]
            sock.close()

    def run(self):
        while True:
            readable, _, exceptional = select.select(self.inputs, [], self.inputs)
            for sock in readable:
                if sock == self.server:
                    client, addr = sock.accept()
                    self.inputs.append(client)
                    self.clients[client] = {'buffer': b'', 'state': 'normal'}
                    print(f"New client connected: {addr}")
                else:
                    self.handle_client(sock)
            for sock in exceptional:
                self.inputs.remove(sock)
                if sock in self.clients:
                    del self.clients[sock]
                sock.close()

if __name__ == "__main__":
    server = SelectServer('localhost', 9999)
    server.run()