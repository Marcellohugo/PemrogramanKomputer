[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/69YEJ65p)
# lecture-network-programming-E03-242502

Fill your NRP and Name in profile.txt file.  

Implement simple multi-client chat servers using the `select`, `socketserver`, and `threading` modules.

Create two server files and one client file:

-   **server-socketserver.py**: Must use the `socketserver` module.
-   **server-select.py**: Must use the `select` module.
-   **client.py**: Must use the `threading` module.

You don't need to run both servers simultaneously—only one at a time. However, each server should be able to handle multiple clients simultaneously and broadcast messages to all connected clients.

Additionally, clients should be able to send some commands:
- `/list`: to receive a list of currently connected clients.
- `/upload <filename>`: to upload a file to the server.
- `/download <filename>`: to download a file from the server.


## Output Example
- server
   ```
   Server started on localhost:9999
   New client connected: ('127.0.0.1', 57220)
   New client connected: ('127.0.0.1', 57236)
   Received hai dari client 1 from ('127.0.0.1', 57220)
   Received halo dari client 2 from ('127.0.0.1', 57236)
   Received /list from ('127.0.0.1', 57220)
   Received /upload cakwee.jpg from ('127.0.0.1', 57220)
   File cakwee.jpg received successfully
   Received /download cakwee.jpg from ('127.0.0.1', 57236)
   File cakwee.jpg sent successfully
   ```
- client 1
   ```
   Connected to localhost:9999
   hai dari client 1
   ('127.0.0.1', 57236): halo dari client 2
   /list
   ('127.0.0.1', 57220)
   ('127.0.0.1', 57236)
   /upload cakwee.jpg
   File 'cakwee.jpg' uploaded successfully
    ```
- client 2
   ```
   Connected to localhost:9999
   ('127.0.0.1', 57220): hai dari client 1
   halo dari client 2
   /download cakwee.jpg
   Receiving file: cakwee.jpg...
   File received successfully: downloads/cakwee.jpg
    ```