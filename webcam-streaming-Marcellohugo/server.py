import socket
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import cv2

def receive_video():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('0.0.0.0', 12345))

    root = tk.Tk()
    root.title("UDP Video Stream")

    canvas = tk.Canvas(root, width=320, height=240)
    canvas.pack()
    img_tk = None  # To prevent garbage collection

    def update_frame():
        nonlocal img_tk
        try:
            data, _ = server_socket.recvfrom(65536)
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img_tk = ImageTk.PhotoImage(image=img)
                canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        except Exception as e:
            print("Error:", e)
        root.after(1, update_frame)

    update_frame()
    root.mainloop()
    server_socket.close()

if __name__ == "__main__":
    receive_video()
