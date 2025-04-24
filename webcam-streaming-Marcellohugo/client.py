import socket
import cv2

def send_video():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ("127.0.0.1", 12345)  # Ganti IP jika server berada di jaringan berbeda

    cap = cv2.VideoCapture(0)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Kompres frame menggunakan JPEG
            encoded, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not encoded:
                continue

            # Kirim buffer JPEG ke server
            client_socket.sendto(buffer.tobytes(), server_address)

            # Tambahkan delay kecil untuk mencegah flooding
            cv2.waitKey(1)

    finally:
        cap.release()
        client_socket.close()

if __name__ == "__main__":
    send_video()
