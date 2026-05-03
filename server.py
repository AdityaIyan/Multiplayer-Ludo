import socket
import threading
import json
import random


HOST = 'localhost'
PORT = 12345

COLORS = {
    'R': "#E74C3C", 'G': "#2ECC71", 'Y': "#F1C40F", 'B': "#3498DB",
}

class LudoServer:
    def __init__(self):
        self.players = [{'id': i, 'pieces': [-1]*4, 'score': 0} for i in range(4)]
        self.turn = 0
        self.global_path = self._generate_path()
        self.last_roll = 0
        self.game_over = False
        self.winner = None
        self.waiting_for_move = False
        self.clients = [None, None, None, None]
        self.lock = threading.Lock()

    def _generate_path(self):
        path = []
        for c in range(1, 6): path.append((c, 6))
        for r in range(5, -1, -1): path.append((6, r))
        path.append((7, 0))
        for r in range(6): path.append((8, r))
        for c in range(9, 15): path.append((c, 6))
        path.append((14, 7))
        for c in range(14, 8, -1): path.append((c, 8))
        for r in range(9, 15): path.append((8, r))
        path.append((7, 14))
        for r in range(14, 8, -1): path.append((6, r))
        for c in range(5, -1, -1): path.append((c, 8))
        path.append((0, 7))
        for c in range(6): path.append((c, 7))
        return path

    def get_valid_moves(self, roll):
        if self.game_over: return []
        valid = []
        for i, pos in enumerate(self.players[self.turn]['pieces']):
            if pos == -1 and roll == 6: valid.append(i)
            elif pos != -1 and pos + roll <= 57: valid.append(i)
        return valid

    def move_piece(self, piece_idx, roll):
        p_id = self.turn
        curr = self.players[p_id]['pieces'][piece_idx]
        new_pos = 0 if curr == -1 else curr + roll
        
        self.players[p_id]['pieces'][piece_idx] = new_pos
        reward = 1 + new_pos * 0.1
        log_txt = f"Player {p_id} moved piece {piece_idx} to {new_pos}"

        if new_pos < 51:
            my_glob = (p_id * 13 + new_pos) % 52
            if new_pos not in [0, 8, 13, 21, 26, 34, 39, 47]:
                for oid in range(4):
                    if oid == p_id: continue
                    for opi, opos in enumerate(self.players[oid]['pieces']):
                        if opos != -1 and opos < 51:
                            if (oid * 13 + opos) % 52 == my_glob:
                                self.players[oid]['pieces'][opi] = -1
                                reward += 50
                                log_txt += " [KILL]"

        if new_pos == 57:
            reward += 100
            log_txt += " [HOME]"
            if sum(1 for p in self.players[p_id]['pieces'] if p == 57) == 4:
                self.game_over = True
                self.winner = ['Red', 'Green', 'Yellow', 'Blue'][p_id]
                log_txt += " [WINNER]"

        self.players[p_id]['score'] += reward
        return reward, log_txt

    def roll_dice(self):
        return random.randint(1, 6)

    def get_state(self):
        return {
            'players': self.players,
            'turn': self.turn,
            'last_roll': self.last_roll,
            'game_over': self.game_over,
            'winner': self.winner,
            'valid_moves': self.get_valid_moves(self.last_roll)
        }

    def broadcast_state(self):
        state = self.get_state()
        msg = json.dumps(state) + "\n"
        for client_sock in self.clients:
            if client_sock:
                try:
                    client_sock.sendall(msg.encode())
                except:
                    pass

game_server = LudoServer()

def handle_client(conn, player_id):
    game_server.clients[player_id] = conn
    print(f"[CONNECTED] Player {player_id} joined")
    
    # Send player_id to client
    init_msg = json.dumps({"type": "init", "player_id": player_id}) + "\n"
    conn.sendall(init_msg.encode())
    
    game_server.broadcast_state()
    
    while not game_server.game_over:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break
            
            with game_server.lock:
                msg = json.loads(data)
                
                if msg["type"] == "roll" and msg["player_id"] == game_server.turn:
                    game_server.last_roll = game_server.roll_dice()
                    print(f"[ROLL] Player {player_id} rolled {game_server.last_roll}")
                    game_server.broadcast_state()
                    
                    # Auto-skip turn if no valid moves after rolling
                    if not game_server.get_valid_moves(game_server.last_roll):
                        print(f"[SKIP] Player {game_server.turn} has no valid moves after rolling {game_server.last_roll}, skipping turn")
                        game_server.turn = (game_server.turn + 1) % 4
                        game_server.last_roll = 0
                        game_server.broadcast_state()
                
                elif msg["type"] == "move" and msg["player_id"] == game_server.turn:
                    piece_idx = msg["piece_idx"]
                    valid_moves = game_server.get_valid_moves(game_server.last_roll)
                    
                    if piece_idx in valid_moves:
                        reward, log_txt = game_server.move_piece(piece_idx, game_server.last_roll)
                        
                        # Only change turn if dice was NOT 6
                        if game_server.last_roll != 6:
                            game_server.turn = (game_server.turn + 1) % 4
                        
                        game_server.last_roll = 0
                        print(f"[MOVE] {log_txt}")
                        game_server.broadcast_state()
                    else:
                        print(f"[INVALID] Player {player_id} tried to move piece {piece_idx}, but not in valid moves: {valid_moves}")
        except Exception as e:
            print(f"Error handling player {player_id}: {e}")
            break
    
    conn.close()

def start():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(4)
    print(f"[SERVER] Ludo Server started on {HOST}:{PORT}")

    player_id = 0
    while player_id < 4:
        conn, addr = server_socket.accept()
        print(f"[CONNECTION] {addr}")
        threading.Thread(target=handle_client, args=(conn, player_id)).start()
        player_id += 1

if __name__ == "__main__":
    start()



