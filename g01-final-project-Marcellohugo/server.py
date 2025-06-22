# server.py
import socket
import threading
import time
import random
import protocol
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# --- Konfigurasi Game & Konstanta ---
HOST, PORT = '127.0.0.1', 65432
TICK_RATE, PLAYER_SPEED, TARGET_SCORE, TILE_SIZE = 20, 5, 100, 40
GAME_MAP = [ [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],[1,0,1,1,1,0,1,0,1,1,1,1,0,1,0,1,1,1,0,1],[1,0,1,0,0,0,1,0,0,0,0,1,0,1,0,0,0,1,0,1],[1,0,1,0,1,1,1,0,1,1,0,1,0,1,1,1,0,1,0,1],[1,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0,1],[1,0,1,1,0,1,0,1,0,1,0,1,1,1,0,1,0,1,1,1],[1,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,1,0,1],[1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,1,0,1,0,1],[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],[1,0,1,1,1,1,0,1,1,0,1,1,1,0,1,1,0,1,1,1],[1,0,0,0,0,1,0,0,1,0,0,0,1,0,1,0,0,0,0,1],[1,0,1,1,0,1,1,0,1,1,1,0,1,0,1,0,1,1,0,1],[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1] ]
ATTACK_RANGE, ATTACK_COOLDOWN, ATTACK_DAMAGE = 50, 1.0, 25
MONSTER_SPAWN_INTERVAL, TREASURE_SPAWN_INTERVAL = 10.0, 5.0

# --- Game State ---
clients, state_lock = {}, threading.Lock()
game_status, winner_id = "playing", None
game_state = {'players': {}, 'monsters': {}, 'treasures': {}}
walkable_tiles = []
monster_counter, treasure_counter = 0, 0
last_monster_spawn_time, last_treasure_spawn_time = time.time(), time.time()

# --- Fungsi Email ---
def send_game_notification(recipient_email, subject, body_html):
    sender_email = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASSWORD')
    if not sender_email or not password:
        print("Peringatan: Email tidak dikonfigurasi.")
        return
    message = MIMEMultipart("alternative")
    message["Subject"], message["From"], message["To"] = subject, f"Server Demam Emas <{sender_email}>", recipient_email
    message.attach(MIMEText(body_html, "html"))
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Email notifikasi dikirim ke {recipient_email}")
    except Exception as e:
        print(f"Gagal mengirim email ke {recipient_email}: {e}")

# --- Fungsi Game ---
def is_colliding(x, y):
    map_x, map_y = int(x / TILE_SIZE), int(y / TILE_SIZE)
    if not (0 <= map_y < len(GAME_MAP) and 0 <= map_x < len(GAME_MAP[0])): return True
    return GAME_MAP[map_y][map_x] == 1

def find_walkable_tiles():
    for y, row in enumerate(GAME_MAP):
        for x, tile in enumerate(row):
            if tile == 0: walkable_tiles.append((x, y))

def client_handler(sock):
    player_id = None
    try:
        buffer = ""
        while True:
            data = sock.recv(1024).decode('utf-8')
            if not data: break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line: continue
                command, args = protocol.parse_message(line)
                with state_lock:
                    if player_id is None: # Hanya proses C_START_GAME jika pemain belum diinisialisasi
                        if command == protocol.C_START_GAME and len(args) == 2:
                            player_name, player_email = args[0], args[1]
                            # [BARU] Pastikan nama pemain unik
                            unique_name = player_name
                            count = 1
                            while unique_name in game_state['players']:
                                unique_name = f"{player_name}_{count}"
                                count += 1
                            player_id = unique_name # ID pemain sekarang adalah nama uniknya
                            clients[player_id] = sock
                            game_state['players'][player_id] = {'x':60,'y':60,'vx':0,'vy':0,'hp':100,'score':0,'last_attack':0,'email':player_email,'name':player_name}
                            print(f"Pemain '{player_id}' ({player_email}) bergabung.")
                        continue
                    
                    if game_status != "playing": continue
                    player = game_state['players'].get(player_id)
                    if not player: continue
                    if command == protocol.C_SET_VELOCITY:
                        player['vx'], player['vy'] = int(args[0]), int(args[1])
                    elif command == protocol.C_ATTACK:
                        current_time = time.time()
                        if current_time - player['last_attack'] > ATTACK_COOLDOWN:
                            player['last_attack'] = current_time
                            monsters_defeated = []
                            for mid, mdata in list(game_state['monsters'].items()):
                                if (player['x'] - mdata['x'])**2 + (player['y'] - mdata['y'])**2 < ATTACK_RANGE**2:
                                    mdata['hp'] -= ATTACK_DAMAGE
                                    if mdata['hp'] <= 0:
                                        player['score'] += mdata['score_value']
                                        monsters_defeated.append(mid)
                            for mid in monsters_defeated:
                                if mid in game_state['monsters']: del game_state['monsters'][mid]
    finally:
        with state_lock:
            if player_id:
                print(f"Pemain '{player_id}' terputus.")
                if player_id in clients: del clients[player_id]
                if player_id in game_state['players']: del game_state['players'][player_id]
        sock.close()

def game_loop():
    global game_status, winner_id, last_monster_spawn_time, last_treasure_spawn_time, monster_counter, treasure_counter
    while True:
        loop_start_time = time.time()
        with state_lock:
            if game_status == "playing":
                current_time = time.time()
                if current_time - last_monster_spawn_time > MONSTER_SPAWN_INTERVAL:
                    last_monster_spawn_time, monster_counter = current_time, monster_counter+1
                    tile_x, tile_y = random.choice(walkable_tiles)
                    px, py = tile_x*TILE_SIZE+TILE_SIZE//2, tile_y*TILE_SIZE+TILE_SIZE//2
                    game_state['monsters'][f"M{monster_counter}"] = {'type':'Goblin','x':px,'y':py,'hp':50,'score_value':10}
                if current_time - last_treasure_spawn_time > TREASURE_SPAWN_INTERVAL:
                    last_treasure_spawn_time, treasure_counter = current_time, treasure_counter+1
                    tile_x, tile_y = random.choice(walkable_tiles)
                    px, py = tile_x*TILE_SIZE+TILE_SIZE//2, tile_y*TILE_SIZE+TILE_SIZE//2
                    game_state['treasures'][f"T{treasure_counter}"] = {'x':px,'y':py,'score_value':25}
                for pdata in game_state['players'].values():
                    pdata['x'], pdata['y'] = (pdata['x']+pdata['vx'], pdata['y']+pdata['vy']) if not is_colliding(pdata['x']+pdata['vx'], pdata['y']+pdata['vy']) else (pdata['x'], pdata['y'])
                for tid, tdata in list(game_state['treasures'].items()):
                    for pid, pdata in game_state['players'].items():
                        if (pdata['x']-tdata['x'])**2 + (pdata['y']-tdata['y'])**2 < 20**2:
                           pdata['score'] += tdata['score_value']
                           if tid in game_state['treasures']: del game_state['treasures'][tid]
                           break
                for pid, pdata in game_state['players'].items():
                    if pdata['score'] >= TARGET_SCORE:
                        game_status, winner_id = "finished", pid
                        break
            player_parts = [f"{pid},{p['x']},{p['y']},{p['score']}" for pid, p in game_state['players'].items()]
            monster_parts = [f"{mid},{m['x']},{m['y']},{m['type']}" for mid, m in game_state['monsters'].items()]
            treasure_parts = [f"{tid},{t['x']},{t['y']}" for tid, t in game_state['treasures'].items()]
            message = protocol.create_message(protocol.S_GAME_UPDATE if game_status=="playing" else protocol.S_GAME_FINISHED, ";".join(player_parts), ";".join(monster_parts), ";".join(treasure_parts)) if game_status=="playing" else protocol.create_message(protocol.S_GAME_FINISHED, winner_id)
        for sock in list(clients.values()):
            try: sock.sendall(message.encode('utf-8'))
            except socket.error: pass
        if game_status == "finished":
            print(f"Permainan Selesai! Pemenangnya adalah {winner_id}")
            with state_lock:
                for pid, pdata in game_state['players'].items():
                    if pid == winner_id:
                        subject = f"Selamat, {pdata['name']}! Anda Menang di Demam Emas!"
                        body = f"<html><body><h2>Kerja Bagus, {pdata['name']}!</h2><p>Anda telah memenangkan permainan <strong>Demam Emas</strong> dengan skor akhir {pdata['score']}! Anda adalah juara sejati.</p></body></html>"
                    else:
                        subject = f"Permainan Berakhir, {pdata['name']}"
                        body = f"<html><body><h2>Permainan Telah Usai</h2><p>Sayang sekali, Anda belum berhasil menang kali ini. Pemenangnya adalah <strong>{winner_id}</strong>. Jangan menyerah dan coba lagi lain waktu!</p></body></html>"
                    threading.Thread(target=send_game_notification, args=(pdata['email'], subject, body)).start()
            time.sleep(5); break
        time.sleep(max(0, 1.0/TICK_RATE - (time.time()-loop_start_time)))

def main():
    find_walkable_tiles()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server 'Demam Emas' berjalan di {HOST}:{PORT}")
    threading.Thread(target=game_loop, daemon=True).start()
    while game_status == "playing":
        try:
            sock, addr = server_socket.accept()
            threading.Thread(target=client_handler, args=(sock,)).start()
        except OSError: break
    print("Server berhenti."); server_socket.close()

if __name__ == "__main__":
    main()