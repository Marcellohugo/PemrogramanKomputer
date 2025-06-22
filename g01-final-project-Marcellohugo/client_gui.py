# client_gui.py
import socket
import threading
import tkinter as tk
from tkinter import messagebox
import queue
import protocol
import re
from PIL import Image, ImageTk

HOST = '127.0.0.1'
PORT = 65432
PLAYER_SPEED = 5
TILE_SIZE = 40
GAME_MAP = [ # 20x15 grid
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,0,1,0,1,1,1,1,0,1,0,1,1,1,0,1],
    [1,0,1,0,0,0,1,0,0,0,0,1,0,1,0,0,0,1,0,1],
    [1,0,1,0,1,1,1,0,1,1,0,1,0,1,1,1,0,1,0,1],
    [1,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0,1],
    [1,0,1,1,0,1,0,1,0,1,0,1,1,1,0,1,0,1,1,1],
    [1,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,1,0,1],
    [1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,0,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,1,0,1,1,0,1,1,1,0,1,1,0,1,1,1],
    [1,0,0,0,0,1,0,0,1,0,0,0,1,0,1,0,0,0,0,1],
    [1,0,1,1,0,1,1,0,1,1,1,0,1,0,1,0,1,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]
WINDOW_WIDTH = (len(GAME_MAP[0]) * TILE_SIZE) + 200
WINDOW_HEIGHT = len(GAME_MAP) * TILE_SIZE

class GameClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Demam Emas")
        self.resizable(False, False)

        self.login_frame = tk.Frame(self)
        self.game_frame = tk.Frame(self)
        self.login_frame.pack(fill="both", expand=True)

        self.message_queue = queue.Queue()
        self.local_game_state = {'players': {}, 'monsters': {}, 'treasures': {}}
        self.my_player_id = None
        self.game_over = False
        self.sock = None

        self.setup_login_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def is_valid_email(self, email):
        return re.match(r"[^@]+@[^@]+\.[^@]+", email)

    def setup_login_ui(self):
        self.geometry("400x300")
        self.login_frame.config(bg="#2C3E50")
        
        tk.Label(self.login_frame, text="DEMAM EMAS", font=("Arial", 24, "bold"), fg="white", bg="#2C3E50").pack(pady=(20, 10))
        tk.Label(self.login_frame, text="Masukkan data untuk bermain", font=("Arial", 12), fg="white", bg="#2C3E50").pack(pady=(0, 20))
        
        # [BARU] Input untuk Nama Player
        tk.Label(self.login_frame, text="Nama Player:", font=("Arial", 11), fg="white", bg="#2C3E50").pack()
        self.name_entry = tk.Entry(self.login_frame, width=30, font=("Arial", 11))
        self.name_entry.pack(pady=5)
        
        tk.Label(self.login_frame, text="Email:", font=("Arial", 11), fg="white", bg="#2C3E50").pack()
        self.email_entry = tk.Entry(self.login_frame, width=30, font=("Arial", 11))
        self.email_entry.pack(pady=5)
        
        self.start_button = tk.Button(self.login_frame, text="START", font=("Arial", 12, "bold"), bg="#16A085", fg="white", command=self.start_game)
        self.start_button.pack(pady=20)
    
    def start_game(self):
        # [DIUBAH] Ambil nama dan email dari input
        player_name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        
        if not player_name:
            messagebox.showerror("Nama Kosong", "Nama player tidak boleh kosong.")
            return
        if not self.is_valid_email(email):
            messagebox.showerror("Email Tidak Valid", "Silakan masukkan alamat email yang valid.")
            return

        self.start_button.config(state="disabled", text="Menghubungkan...")
        
        if not self.connect_to_server():
            self.start_button.config(state="normal", text="START")
            return

        # [DIUBAH] Kirim nama dan email ke server
        self.sock.sendall(protocol.create_message(protocol.C_START_GAME, player_name, email).encode('utf-8'))
        
        self.login_frame.pack_forget()
        self.game_frame.pack(fill="both", expand=True)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.setup_game_ui()
    
    def setup_game_ui(self):
        self.canvas = tk.Canvas(self.game_frame, bg="black", width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.bg_img = None
        try:
            self.bg_img_raw = Image.open("dungeon_floor.png").resize((len(GAME_MAP[0]) * TILE_SIZE, WINDOW_HEIGHT))
            self.bg_img = ImageTk.PhotoImage(self.bg_img_raw)
        except FileNotFoundError:
            print("Peringatan: File 'dungeon_floor.png' tidak ditemukan.")
        self.keys_pressed = set()
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        self.after(100, self.process_queue)
        self.after(100, self.render_loop)

    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            threading.Thread(target=self.listen_for_messages, daemon=True).start()
            return True
        except ConnectionRefusedError:
            messagebox.showerror("Koneksi Gagal", "Server tidak ditemukan.")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan: {e}")
            return False

    def listen_for_messages(self):
        buffer = ""
        while not self.game_over:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data: break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.message_queue.put(line)
            except: break
        if self.sock: self.sock.close()

    def process_queue(self):
        if self.game_over: return
        try:
            message = self.message_queue.get(block=False)
            if not message: return
            command, args = protocol.parse_message(message)
            if command == protocol.S_GAME_UPDATE:
                player_data_str, monster_data_str, treasure_data_str = args
                self.local_game_state['players'].clear()
                if player_data_str:
                    for p in player_data_str.split(protocol.DATA_SEP):
                        pid, x, y, score = p.split(protocol.FIELD_SEP)
                        self.local_game_state['players'][pid] = {'x': int(x), 'y': int(y), 'score': int(score)}
                        # [DIUBAH] Set my_player_id saat pertama kali data diterima
                        if self.my_player_id is None:
                           # Asumsi server akan mengirim data kita duluan, atau kita cari dari nama
                           # Untuk sekarang, kita tunggu sampai ada di state
                           if any(pid for pid in self.local_game_state['players'].keys()):
                               # Logika ini perlu disempurnakan jika ID tidak langsung dikenali
                               # Namun, untuk saat ini, kita akan menunggu ID kita muncul
                               pass
                self.local_game_state['monsters'].clear()
                if monster_data_str:
                    for m in monster_data_str.split(protocol.DATA_SEP):
                        mid, x, y, mtype = m.split(protocol.FIELD_SEP)
                        self.local_game_state['monsters'][mid] = {'x': int(x), 'y': int(y), 'type': mtype}
                self.local_game_state['treasures'].clear()
                if treasure_data_str:
                    for t in treasure_data_str.split(protocol.DATA_SEP):
                        tid, x, y = t.split(protocol.FIELD_SEP)
                        self.local_game_state['treasures'][tid] = {'x': int(x), 'y': int(y)}
            elif command == protocol.S_GAME_FINISHED:
                self.game_over = True
                winner_id = args[0]
                # [DIUBAH] Mencari tahu ID kita dari server
                # Cara sederhana: server bisa mengirimkan ID kita saat konek
                # Atau kita bisa menebak dari nama, tapi untuk saat ini, kita asumsikan tahu ID kita
                if not self.my_player_id and self.local_game_state['players']:
                     # Jika ID belum ter-set, coba set dari nama yang kita input
                     my_name = self.name_entry.get().strip()
                     for pid in self.local_game_state['players']:
                         if pid.startswith(my_name):
                             self.my_player_id = pid
                             break
                self.canvas.delete("all"); self.canvas.config(bg="black")
                text = f"KAMU MENANG!" if winner_id == self.my_player_id else f"KAMU KALAH!\nPemenangnya adalah {winner_id}"
                self.canvas.create_text(WINDOW_WIDTH/2, WINDOW_HEIGHT/2, text=text, fill="white", font=("Arial", 40), justify=tk.CENTER)
                return
        except queue.Empty: pass
        finally:
            if not self.game_over: self.after(10, self.process_queue)

    def render_loop(self):
        if self.game_over: return
        self.canvas.delete("all")
        if self.bg_img: self.canvas.create_image(0, 0, image=self.bg_img, anchor="nw")
        else: self.canvas.create_rectangle(0, 0, len(GAME_MAP[0])*TILE_SIZE, WINDOW_HEIGHT, fill="#222")
        for y, row in enumerate(GAME_MAP):
            for x, tile in enumerate(row):
                if tile == 1: self.canvas.create_rectangle(x*TILE_SIZE, y*TILE_SIZE, (x+1)*TILE_SIZE, (y+1)*TILE_SIZE, fill="gray", outline="dark gray")
        for tdata in self.local_game_state['treasures'].values(): self.canvas.create_oval(tdata['x']-8, tdata['y']-8, tdata['x']+8, tdata['y']+8, fill="yellow", outline="gold")
        for mdata in self.local_game_state['monsters'].values(): self.canvas.create_rectangle(mdata['x']-12, mdata['y']-12, mdata['x']+12, mdata['y']+12, fill="red", outline="darkred")
        
        # [DIUBAH] Set my_player_id jika belum diset
        if not self.my_player_id:
            my_name = self.name_entry.get().strip()
            for pid in self.local_game_state['players']:
                if pid.startswith(my_name):
                    self.my_player_id = pid
                    break

        for pid, pdata in self.local_game_state['players'].items():
            color = "cyan" if pid == self.my_player_id else "orange"
            self.canvas.create_oval(pdata['x']-10, pdata['y']-10, pdata['x']+10, pdata['y']+10, fill=color)
            self.canvas.create_text(pdata['x'], pdata['y']-15, text=f"{pid}", fill="white")
        scoreboard_x = len(GAME_MAP[0]) * TILE_SIZE
        self.canvas.create_rectangle(scoreboard_x, 0, WINDOW_WIDTH, WINDOW_HEIGHT, fill="#1C1C1C", outline="")
        self.canvas.create_text(scoreboard_x + 100, 40, text="PAPAN SKOR", fill="white", font=("Arial", 18, "bold"))
        y_pos = 80
        sorted_players = sorted(self.local_game_state['players'].items(), key=lambda item: item[1]['score'], reverse=True)
        for pid, pdata in sorted_players:
            display_text = f"{pid} (Anda)" if pid == self.my_player_id else pid
            self.canvas.create_text(scoreboard_x + 20, y_pos, text=f"{display_text}: {pdata['score']}", fill="white", font=("Arial", 14), anchor="w")
            y_pos += 30
        self.after(16, self.render_loop)

    def update_velocity(self):
        if self.game_over or not self.sock: return
        try:
            vx, vy = 0, 0
            if 'w' in self.keys_pressed: vy -= PLAYER_SPEED
            if 's' in self.keys_pressed: vy += PLAYER_SPEED
            if 'a' in self.keys_pressed: vx -= PLAYER_SPEED
            if 'd' in self.keys_pressed: vx += PLAYER_SPEED
            self.sock.sendall(protocol.create_message(protocol.C_SET_VELOCITY, vx, vy).encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError): pass

    def on_key_press(self, event):
        if self.game_over: return
        key = event.keysym.lower()
        if key not in self.keys_pressed:
            self.keys_pressed.add(key)
            if key in ['w', 'a', 's', 'd']: self.update_velocity()
        if key == 'space':
            try:
                if self.sock: self.sock.sendall(protocol.create_message(protocol.C_ATTACK).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError): pass

    def on_key_release(self, event):
        if self.game_over: return
        key = event.keysym.lower()
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
            if key in ['w', 'a', 's', 'd']: self.update_velocity()

    def on_closing(self):
        self.game_over = True
        if self.sock: self.sock.close()
        self.destroy()

if __name__ == "__main__":
    app = GameClient()
    app.mainloop()