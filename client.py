import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox

HOST = 'localhost'
PORT = 12345

CELL_SIZE = 40
BOARD_SIZE = 15
PANEL_WIDTH = 340
WINDOW_WIDTH = (CELL_SIZE * BOARD_SIZE) + PANEL_WIDTH
WINDOW_HEIGHT = CELL_SIZE * BOARD_SIZE

COLORS = {
    'R': "#E74C3C", 'G': "#2ECC71", 'Y': "#F1C40F", 'B': "#3498DB",
    'grid': "#BDC3C7", 'bg': "#ECF0F1", 'panel_bg': "#ffffff"
}

class LudoClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Ludo - Multiplayer")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        
        self.sock = None
        self.player_id = None
        self.game_state = None
        self.waiting_for_server = True
        self.selected_piece = None
        
        self._init_ui()
        self._connect_server()
        
    def _init_ui(self):
        self.canvas = tk.Canvas(self.root, width=CELL_SIZE * BOARD_SIZE, height=WINDOW_HEIGHT, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT)
        self.canvas.bind("<Button-1>", self.on_board_click)
        
        self.panel = tk.Frame(self.root, width=PANEL_WIDTH, bg=COLORS['panel_bg'])
        self.panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(self.panel, text="Ludo Multiplayer", font=("Arial", 14, "bold"), bg=COLORS['panel_bg']).pack(pady=(15,5))
        
        self.status_lbl = tk.Label(self.panel, text="Connecting...", font=("Arial", 10), bg=COLORS['panel_bg'])
        self.status_lbl.pack(pady=5)
        
        self.turn_lbl = tk.Label(self.panel, text="Waiting", font=("Arial", 12, "bold"), bg=COLORS['panel_bg'], fg="gray", width=25, pady=10)
        self.turn_lbl.pack(pady=10)
        
        self.dice_frame = tk.Canvas(self.panel, width=60, height=60, bg=COLORS['panel_bg'], highlightthickness=0)
        self.dice_frame.pack()
        self.dice_frame.bind("<Button-1>", self.on_dice_click)
        self.draw_dice(0)
        
        tk.Label(self.panel, text="Pieces:", font=("Arial", 10, "bold"), bg=COLORS['panel_bg']).pack(pady=(10,5))
        self.pieces_frame = tk.Frame(self.panel, bg=COLORS['panel_bg'])
        self.pieces_frame.pack(padx=10)
        
        self.log_box = tk.Text(self.panel, height=14, width=35, font=("Consolas", 8), relief=tk.FLAT, bg="#f9f9f9")
        self.log_box.pack(padx=10, pady=5)
        
        self._draw_board_static()

    def _draw_board_static(self):
        self.canvas.delete("all")
        self._draw_base_rect(0, 0, COLORS['R'])
        self._draw_base_rect(9, 0, COLORS['G'])
        self._draw_base_rect(9, 9, COLORS['Y'])
        self._draw_base_rect(0, 9, COLORS['B'])
        
        mid = 7.5 * CELL_SIZE
        self.canvas.create_polygon(6*CELL_SIZE, 6*CELL_SIZE, 9*CELL_SIZE, 6*CELL_SIZE, mid, mid, fill=COLORS['G'], outline="black")
        self.canvas.create_polygon(9*CELL_SIZE, 6*CELL_SIZE, 9*CELL_SIZE, 9*CELL_SIZE, mid, mid, fill=COLORS['Y'], outline="black")
        self.canvas.create_polygon(9*CELL_SIZE, 9*CELL_SIZE, 6*CELL_SIZE, 9*CELL_SIZE, mid, mid, fill=COLORS['B'], outline="black")
        self.canvas.create_polygon(6*CELL_SIZE, 9*CELL_SIZE, 6*CELL_SIZE, 6*CELL_SIZE, mid, mid, fill=COLORS['R'], outline="black")
        
        def fill(coords, c):
            for x, y in coords:
                x1, y1 = x * CELL_SIZE, y * CELL_SIZE
                self.canvas.create_rectangle(x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE, fill=c, outline=COLORS['grid'])
        
        fill([(i, 7) for i in range(1, 6)], COLORS['R'])
        fill([(7, i) for i in range(1, 6)], COLORS['G'])
        fill([(i, 7) for i in range(9, 14)], COLORS['Y'])
        fill([(7, i) for i in range(9, 14)], COLORS['B'])
        fill([(1, 6), (8, 1), (13, 8), (6, 13)], "#999")
        
        for r in range(15):
            for c in range(15):
                if not ((r < 6 and c < 6) or (r < 6 and c > 8) or (r > 8 and c < 6) or (r > 8 and c > 8)):
                    self.canvas.create_rectangle(c * CELL_SIZE, r * CELL_SIZE, (c + 1) * CELL_SIZE, (r + 1) * CELL_SIZE, width=1)
        
        for c, r in [(1, 6), (8, 1), (13, 8), (6, 13), (2, 8), (6, 2), (12, 6), (8, 12)]:
            self.canvas.create_text(c * CELL_SIZE + 20, r * CELL_SIZE + 22, text="★", font=("Arial", 20), fill="#7F8C8D")

    def _draw_base_rect(self, c, r, color):
        x, y = c * CELL_SIZE, r * CELL_SIZE
        self.canvas.create_rectangle(x, y, x + 6 * CELL_SIZE, y + 6 * CELL_SIZE, fill=color, outline="black")
        self.canvas.create_rectangle(x + CELL_SIZE, y + CELL_SIZE, x + 5 * CELL_SIZE, y + 5 * CELL_SIZE, fill="white", outline="black")

    def draw_dice(self, num):
        self.dice_frame.delete("all")
        self.dice_frame.create_rectangle(5, 5, 55, 55, fill="white", outline="#333", width=2)
        if num == 0:
            self.dice_frame.create_text(30, 30, text="ROLL", font=("Arial", 9, "bold"), fill="#999")
        else:
            dots = {1: [(30, 30)], 2: [(15, 15), (45, 45)], 3: [(15, 15), (30, 30), (45, 45)], 4: [(15, 15), (15, 45), (45, 15), (45, 45)], 5: [(15, 15), (15, 45), (45, 15), (45, 45), (30, 30)], 6: [(15, 15), (15, 45), (45, 15), (45, 45), (15, 30), (45, 30)]}
            for x, y in dots[num]:
                self.dice_frame.create_oval(x - 3, y - 3, x + 3, y + 3, fill="black")

    def _refresh_pieces(self):
        for widget in self.pieces_frame.winfo_children():
            widget.destroy()
        
        if not self.game_state:
            return
        
        pieces = self.game_state['players'][self.player_id]['pieces']
        for i, pos in enumerate(pieces):
            pos_text = "Home" if pos == -1 else f"P{pos}"
            btn = tk.Button(self.pieces_frame, text=f"P{i}: {pos_text}", width=15, height=2, command=lambda idx=i: self.select_piece(idx))
            btn.pack(pady=2)

    def select_piece(self, piece_idx):
        if self.game_state and self.game_state['turn'] == self.player_id and self.game_state['valid_moves']:
            if piece_idx in self.game_state['valid_moves']:
                self.selected_piece = piece_idx
                self.log("Selected piece: " + str(piece_idx))
            else:
                self.log("Invalid move for this piece")

    def on_dice_click(self, event):
        if not self.game_state:
            return
        if self.game_state['turn'] != self.player_id:
            self.log("Not your turn")
            return
        if self.game_state['last_roll'] > 0:
            self.log("Please move a piece first")
            return
        
        self.sock.sendall(json.dumps({"type": "roll", "player_id": self.player_id}).encode())
        self.log("Rolled dice...")

    def on_board_click(self, event):
        if self.selected_piece is not None and self.game_state['turn'] == self.player_id:
            self.sock.sendall(json.dumps({"type": "move", "player_id": self.player_id, "piece_idx": self.selected_piece}).encode())
            self.log(f"Moved piece {self.selected_piece}")
            self.selected_piece = None

    def log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)

    def _connect_server(self):
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.log("Connected to server")
            self.root.after(0, lambda: self.status_lbl.config(text="Waiting for player ID..."))
            self._receive_loop()
        except Exception as e:
            self.log(f"Connection error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Cannot connect to server: {e}"))

    def _receive_loop(self):
        buffer = ""
        try:
            while True:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                lines = buffer.split("\n")
                buffer = lines[-1]  # Keep incomplete line in buffer
                
                for line in lines[:-1]:
                    if not line.strip():
                        continue
                    
                    try:
                        msg = json.loads(line)
                        
                        # Handle init message with player_id
                        if msg.get("type") == "init":
                            self.player_id = msg["player_id"]
                            self.waiting_for_server = False
                            color_names = ["Red", "Green", "Yellow", "Blue"]
                            color_name = color_names[self.player_id]
                            def init_ui(pid=self.player_id, cn=color_name):
                                self.status_lbl.config(text=f"You are Player {pid} ({cn})")
                                self.log(f"Connected as Player {pid} ({cn})")
                            self.root.after(0, init_ui)
                            continue
                        
                        # Handle game state update
                        self.game_state = msg
                        self._update_ui()
                    except json.JSONDecodeError as e:
                        self.root.after(0, lambda err=str(e): self.log(f"JSON error: {err}"))
                        
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.log(f"Receive error: {err}"))

    def _update_ui(self):
        self.root.after(0, self._update_ui_main)
    
    def _update_ui_main(self):
        if not self.game_state:
            return
        
        player_colors = ['Red', 'Green', 'Yellow', 'Blue']
        color_hex = [COLORS['R'], COLORS['G'], COLORS['Y'], COLORS['B']]
        
        current_turn = self.game_state['turn']
        if current_turn == self.player_id:
            turn_text = "YOUR TURN"
            self.turn_lbl.config(text=turn_text, bg=color_hex[current_turn], fg="white")
        else:
            turn_text = f"{player_colors[current_turn]}'s Turn"
            self.turn_lbl.config(text=turn_text, bg=color_hex[current_turn], fg="white")
        
        dice = self.game_state['last_roll']
        self.draw_dice(dice)
        
        self._refresh_pieces()
        self._draw_pieces()
        
        if self.game_state['game_over']:
            self.log(f"GAME OVER! Winner: {self.game_state['winner']}")

    def _draw_pieces(self):
        self.canvas.delete("pieces")
        
        if not self.game_state:
            return
        
        color_map = ['R', 'G', 'Y', 'B']
        
        for player_idx, player in enumerate(self.game_state['players']):
            for piece_idx, pos in enumerate(player['pieces']):
                if pos == -1:
                    base = [(1.5, 1.5), (9.5, 1.5), (9.5, 9.5), (1.5, 9.5)][player_idx]
                    offset = [(0, 0), (2, 0), (0, 2), (2, 2)][piece_idx]
                    cx, cy = (base[0] + offset[0]) * CELL_SIZE, (base[1] + offset[1]) * CELL_SIZE
                else:
                    global_path = self._get_global_path()
                    if pos < 51:
                        path_pos = (player_idx * 13 + pos) % 52
                        x, y = global_path[path_pos]
                    else:
                        x, y = [1 + (pos - 51), 7], [7, 1 + (pos - 51)], [13 - (pos - 51), 7], [7, 13 - (pos - 51)]
                        x, y = x[player_idx], y[player_idx]
                    cx, cy = x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2
                
                self.canvas.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, fill=COLORS[color_map[player_idx]], outline="black", width=2, tags="pieces")

    def _get_global_path(self):
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


if __name__ == "__main__":
    root = tk.Tk()
    client = LudoClient(root)
    root.mainloop()
