# protocol.py

# Definisikan perintah agar konsisten
# Client to Server
C_LOGIN = "100"
C_SET_VELOCITY = "101"
C_ATTACK = "102"
# [DIUBAH] Perintah ini sekarang membawa nama dan email pemain
C_START_GAME = "103" 

# Server to Client
S_GAME_UPDATE = "200"
S_PLAYER_DEFEATED = "201"
S_GAME_FINISHED = "202"

# Karakter pemisah untuk data
MSG_SEP = "|"
DATA_SEP = ";"
FIELD_SEP = ","

def create_message(command, *args):
    """Membuat pesan dengan format 'COMMAND|arg1|arg2'."""
    payload = MSG_SEP.join(map(str, args))
    return f"{command}{MSG_SEP}{payload}\n"

def parse_message(data_string):
    """Mem-parsing satu baris pesan."""
    data_string = data_string.strip()
    if not data_string:
        return None, []
    parts = data_string.split(MSG_SEP)
    command = parts[0]
    args = parts[1:]
    return command, args