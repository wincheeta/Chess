import time
import math
import random

# --- Constants ---
TIMEOUT_BUFFER = 0.4
MATE_SCORE = 30000
MAX_DEPTH = 30
TT_SIZE = 1048576  # 2^20 entries (approx 1 million positions)

# TT Flag Constants
TT_EXACT = 0
TT_LOWERBOUND = 1
TT_UPPERBOUND = 2

# Material Values
PIECE_VALUES = {
    "pawn": 100,
    "knight": 320,
    "bishop": 330,
    "right": 400,
    "queen": 900,
    "king": 20000
}

# --- Piece-Square Tables (PST) ---
PST_CENTER = [
    -10, -5, -5, -5, -10,
    -5,   5, 10,  5, -5,
    -5,  10, 20, 10, -5,
    -5,   5, 10,  5, -5,
    -10, -5, -5, -5, -10
]

PST_KING = [
    20,  30,  10,  30,  20,
    20,   0, -20,   0,  20,
    -10, -30, -50, -30, -10,
    20,   0, -20,   0,  20,
    20,  30,  10,  30,  20
]

PST_PAWN_WHITE = [
    0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,
    20,  20,  25,  20,  20,
    5,   5,   10,  5,   5,
    0,   0,   0,   0,   0
]

PST_PAWN_BLACK = [
    0,   0,   0,   0,   0,
    5,   5,   10,  5,   5,
    20,  20,  25,  20,  20,
    50,  50,  50,  50,  50,
    0,   0,   0,   0,   0
]

PST_MAP = {
    "white_pawn": PST_PAWN_WHITE,
    "black_pawn": PST_PAWN_BLACK,
    "knight": PST_CENTER,
    "bishop": PST_CENTER,
    "right": PST_CENTER,
    "queen": PST_CENTER,
    "king": PST_KING
}

# --- Zobrist Hashing Initialization ---
random.seed(42)  # Fixed seed for reproducibility
Z_PIECES = {
    color: {
        p_name: [random.getrandbits(64) for _ in range(25)]
        for p_name in ["pawn", "knight", "bishop", "right", "queen", "king"]
    }
    for color in ["white", "black"]
}
Z_BLACK_TO_MOVE = random.getrandbits(64)
# One hash per possible EP target square
Z_EP = [random.getrandbits(64) for _ in range(25)] 

class TimeoutException(Exception):
    pass

class TranspositionTable:
    def __init__(self):
        # Using a standard dict for O(1) average access. 
        # For a production C++ engine we'd use a fixed array, but dict is Pythonic.
        self.table = {}

    def store(self, z_hash, depth, score, flag, best_move):
        # Replacement scheme: Always replace if new depth is deeper or equal.
        # This keeps the most accurate calculations.
        if z_hash not in self.table or self.table[z_hash]['depth'] <= depth:
            self.table[z_hash] = {
                'depth': depth,
                'score': score,
                'flag': flag,
                'best_move': best_move
            }

    def probe(self, z_hash, depth, alpha, beta):
        if z_hash in self.table:
            entry = self.table[z_hash]
            # We can use the stored move for ordering even if depth is insufficient
            best_move = entry['best_move']
            
            if entry['depth'] >= depth:
                score = entry['score']
                
                if entry['flag'] == TT_EXACT:
                    return score, best_move
                if entry['flag'] == TT_LOWERBOUND and score >= beta:
                    return score, best_move
                if entry['flag'] == TT_UPPERBOUND and score <= alpha:
                    return score, best_move
            
            return None, best_move
        return None, None

    def clear(self):
        self.table.clear()

class AlphaBetaAgent:
    def __init__(self, depth=4):
        self.max_depth = depth
        self.my_color = None
        self.opponent_color = None
        self.node_count = 0
        self.tt = TranspositionTable()

    def get_move(self, board, player, time_budget_info):
        self.my_color = player.name.lower()
        self.opponent_color = "black" if self.my_color == "white" else "white"
        
        start_time = time.perf_counter()
        time_limit = time_budget_info[1] if time_budget_info else 2.0
        
        bitboards = board_to_bitboards(board)
        
        # Initial Hash Calculation
        current_hash = self.compute_full_hash(bitboards, 0)
        
        root_ep_target = 0 
        best_move_so_far = None
        
        # Manage TT size
        if len(self.tt.table) > TT_SIZE:
            self.tt.clear()
        
        try:
            for current_depth in range(1, self.max_depth + 1):
                self.node_count = 0
                
                found_move, score = self.find_best_move(
                    bitboards, 
                    current_depth, 
                    start_time, 
                    time_limit,
                    root_ep_target,
                    current_hash,
                    pv_move=best_move_so_far
                )
                
                if found_move:
                    best_move_so_far = found_move
                    print(f"Depth {current_depth} done. Nodes: {self.node_count}. Best: {found_move}. Score: {score}")
                
                if score >= 29985: # end if it spots mate in 15 
                    break
                
                if (time.perf_counter() - start_time) > (time_limit * 0.5):
                    break
                    
        except TimeoutException:
            print("Timeout! Returning best move from previous completed depth.")
        
        # Return Logic (Identical to before)
        if best_move_so_far:
            return self.coords_to_move_object(board, best_move_so_far)
            
        legal_moves = get_possible_moves(bitboards, self.my_color, root_ep_target)
        if legal_moves:
            return self.coords_to_move_object(board, legal_moves[0])
            
        return None, None

    def find_best_move(self, bitboards, depth, start_time, time_limit, ep_target, current_hash, pv_move=None):
        alpha = float('-inf')
        beta = float('inf')
        
        # Probe TT for Move Ordering at Root
        # We don't return the score here because we want to ensure we get a move for this specific iteration
        # unless it's an exact match, but usually we just take the move for ordering.
        _, tt_move = self.tt.probe(current_hash, depth, alpha, beta)
        
        ordered_move_guess = pv_move if pv_move else tt_move

        moves = self.get_ordered_moves(bitboards, self.my_color, ep_target, pv_move=ordered_move_guess)
        
        if not moves: return None, 0
            
        best_move = moves[0]
        best_val = float('-inf')
        
        for start_sq, end_sq in moves:
            piece_name = self.get_piece_name_at(bitboards, start_sq, self.my_color)
            
            new_ep_target = 0
            if piece_name == "pawn" and abs(start_sq - end_sq) == 10:
                new_ep_target = 1 << ((start_sq + end_sq) // 2)

            # --- INCREMENTAL HASH ---
            hash_diff = self.get_hash_diff(bitboards, start_sq, end_sq, piece_name, self.my_color, ep_target, new_ep_target)
            new_hash = current_hash ^ hash_diff ^ Z_BLACK_TO_MOVE # Toggle turn bit

            undo_info = make_move(bitboards, start_sq, end_sq, piece_name, self.my_color, ep_target)
            
            try:
                val = self.alpha_beta(bitboards, depth - 1, alpha, beta, start_time, time_limit, 
                                    is_maximizing=False, ply=1, ep_target=new_ep_target, current_hash=new_hash)
            finally:
                unmake_move(bitboards, start_sq, end_sq, piece_name, self.my_color, undo_info)
            
            if val > best_val:
                best_val = val
                best_move = (start_sq, end_sq)
            
            alpha = max(alpha, best_val)
            
            if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
                raise TimeoutException("Timeout")

        # Store Root Result
        self.tt.store(current_hash, depth, best_val, TT_EXACT, best_move)
        return best_move, best_val

    def alpha_beta(self, bitboards, depth, alpha, beta, start_time, time_limit, is_maximizing, ply, ep_target, current_hash):
        self.node_count += 1
        
        if self.node_count & 4095 == 0:
            if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
                raise TimeoutException("Timeout")

        # --- TT PROBE ---
        tt_val, tt_move = self.tt.probe(current_hash, depth, alpha, beta)
        if tt_val is not None:
            # Normalize Mate Score: Retrieve score relative to root, convert to relative to current ply
            # If stored > 20000, it was (MATE - ply_at_store). 
            # We want to return (MATE - ply_now) approx. 
            # Actually, standard is: Store = Score + Ply (if winning). Retrieve = Score - Ply.
            if tt_val > 20000: tt_val -= ply
            elif tt_val < -20000: tt_val += ply
            return tt_val

        player_color = self.my_color if is_maximizing else self.opponent_color
        moves = self.get_ordered_moves(bitboards, player_color, ep_target, pv_move=tt_move)

        if not moves:
            if is_in_check(bitboards, player_color):
                return (-MATE_SCORE + ply) if is_maximizing else (MATE_SCORE - ply)
            return 0 

        if depth == 0:
            return self.quiescence_search(bitboards, alpha, beta, start_time, time_limit, is_maximizing, 2, ep_target)

        orig_alpha = alpha
        best_move = None
        
        if is_maximizing:
            maxEval = float('-inf')
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.my_color)
                
                new_ep_target = 0
                if piece_name == "pawn" and abs(start_sq - end_sq) == 10:
                    new_ep_target = 1 << ((start_sq + end_sq) // 2)

                hash_diff = self.get_hash_diff(bitboards, start_sq, end_sq, piece_name, self.my_color, ep_target, new_ep_target)
                new_hash = current_hash ^ hash_diff ^ Z_BLACK_TO_MOVE

                undo_info = make_move(bitboards, start_sq, end_sq, piece_name, self.my_color, ep_target)
                val = self.alpha_beta(bitboards, depth - 1, alpha, beta, start_time, time_limit, False, ply + 1, new_ep_target, new_hash)
                unmake_move(bitboards, start_sq, end_sq, piece_name, self.my_color, undo_info)
                
                if val > maxEval:
                    maxEval = val
                    best_move = (start_sq, end_sq)
                
                alpha = max(alpha, maxEval)
                if beta <= alpha: break
            final_val = maxEval
        else:
            minEval = float('inf')
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.opponent_color)
                
                new_ep_target = 0
                if piece_name == "pawn" and abs(start_sq - end_sq) == 10:
                    new_ep_target = 1 << ((start_sq + end_sq) // 2)

                hash_diff = self.get_hash_diff(bitboards, start_sq, end_sq, piece_name, self.opponent_color, ep_target, new_ep_target)
                new_hash = current_hash ^ hash_diff ^ Z_BLACK_TO_MOVE

                undo_info = make_move(bitboards, start_sq, end_sq, piece_name, self.opponent_color, ep_target)
                val = self.alpha_beta(bitboards, depth - 1, alpha, beta, start_time, time_limit, True, ply + 1, new_ep_target, new_hash)
                unmake_move(bitboards, start_sq, end_sq, piece_name, self.opponent_color, undo_info)
                
                if val < minEval:
                    minEval = val
                    best_move = (start_sq, end_sq)
                
                beta = min(beta, minEval)
                if beta <= alpha: break
            final_val = minEval

        # --- TT STORE ---
        flag = TT_EXACT
        if final_val <= orig_alpha: flag = TT_UPPERBOUND
        elif final_val >= beta: flag = TT_LOWERBOUND
        
        # Normalize Mate Score for Storage:
        # Score is currently (MATE - ply). We want to store (MATE - 0) effectively, so it's depth independent.
        # Stored = Score + Ply (if Max winning)
        store_val = final_val
        if store_val > 20000: store_val += ply
        elif store_val < -20000: store_val -= ply
        
        self.tt.store(current_hash, depth, store_val, flag, best_move)
        
        return final_val

    def quiescence_search(self, bitboards, alpha, beta, start_time, time_limit, is_maximizing, q_depth, ep_target):
        self.node_count += 1
        if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
            raise TimeoutException("Timeout")

        stand_pat = self.evaluate(bitboards)
        
        if is_maximizing:
            if stand_pat >= beta: return beta
            if stand_pat > alpha: alpha = stand_pat
        else:
            if stand_pat <= alpha: return alpha
            if stand_pat < beta: beta = stand_pat
            
        if q_depth == 0: return stand_pat

        player_color = self.my_color if is_maximizing else self.opponent_color
        
        in_check = is_in_check(bitboards, player_color)
        moves = self.get_ordered_moves(bitboards, player_color, ep_target, captures_only=not in_check)
        
        if is_maximizing:
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.my_color)
                undo_info = make_move(bitboards, start_sq, end_sq, piece_name, self.my_color, ep_target)
                score = self.quiescence_search(bitboards, alpha, beta, start_time, time_limit, False, q_depth - 1, 0)
                unmake_move(bitboards, start_sq, end_sq, piece_name, self.my_color, undo_info)
                if score >= beta: return beta
                if score > alpha: alpha = score
            return alpha
        else:
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.opponent_color)
                undo_info = make_move(bitboards, start_sq, end_sq, piece_name, self.opponent_color, ep_target)
                score = self.quiescence_search(bitboards, alpha, beta, start_time, time_limit, True, q_depth - 1, 0)
                unmake_move(bitboards, start_sq, end_sq, piece_name, self.opponent_color, undo_info)
                if score <= alpha: return alpha
                if score < beta: beta = score
            return beta

    def compute_full_hash(self, bitboards, ep_target):
        h = 0
        for color in ["white", "black"]:
            for name in PIECE_NAMES:
                pieces = bitboards[f"{color}_{name}s"]
                for i in range(25):
                    if (pieces >> i) & 1:
                        h ^= Z_PIECES[color][name][i]
        
        if ep_target:
            idx = ep_target.bit_length() - 1
            h ^= Z_EP[idx]
        return h

    def get_hash_diff(self, bitboards, start, end, piece, color, old_ep, new_ep):
        """Calculates the XOR mask to update the hash."""
        h = 0
        # 1. Remove moving piece from source
        h ^= Z_PIECES[color][piece][start]
        
        # 2. Add moving piece to destination (Handle Promotion)
        target_piece = piece
        if piece == "pawn" and ((color == "white" and end < 5) or (color == "black" and end >= 20)):
            target_piece = "queen"
        h ^= Z_PIECES[color][target_piece][end]
        
        # 3. Handle Standard Capture
        opp_color = "black" if color == "white" else "white"
        if bitboards[f"{opp_color}_occupied"] & (1 << end):
            # Find captured piece
            for name in PIECE_NAMES:
                if bitboards[f"{opp_color}_{name}s"] & (1 << end):
                    h ^= Z_PIECES[opp_color][name][end]
                    break
                    
        # 4. Handle En Passant Capture
        elif piece == "pawn" and (1 << end) == old_ep:
            # Capture is 'behind' the destination
            cap_idx = end + 5 if color == "white" else end - 5
            h ^= Z_PIECES[opp_color]["pawn"][cap_idx]

        # 5. Update EP Target
        if old_ep: h ^= Z_EP[old_ep.bit_length() - 1]
        if new_ep: h ^= Z_EP[new_ep.bit_length() - 1]
            
        return h

    def get_ordered_moves(self, bitboards, color, ep_target, captures_only=False, pv_move=None):
        moves = get_possible_moves(bitboards, color, ep_target)
        opponent_color = "black" if color == "white" else "white"
        opp_occupied = bitboards[f"{opponent_color}_occupied"]
        
        capture_moves = []
        quiet_moves = []
        pv_moves_list = []
        
        for start, end in moves:
            if pv_move and (start == pv_move[0] and end == pv_move[1]):
                pv_moves_list.append((start, end))
                continue

            target_bit = 1 << end
            if (opp_occupied & target_bit) or (target_bit == ep_target):
                capture_moves.append((start, end))
            else:
                if not captures_only:
                    quiet_moves.append((start, end))
        
        if not captures_only:
            random.shuffle(quiet_moves)
            
        return pv_moves_list + capture_moves + quiet_moves

    def evaluate(self, bitboards):
        score = 0
        for piece_name in PIECE_NAMES:
            my_pieces = bitboards[f"{self.my_color}_{piece_name}s"]
            pst = PST_MAP[f"{self.my_color}_pawn"] if piece_name == "pawn" else PST_MAP[piece_name]
            while my_pieces:
                lsb = my_pieces & -my_pieces
                my_pieces ^= lsb
                idx = lsb.bit_length() - 1
                score += PIECE_VALUES[piece_name] + pst[idx]

            opp_pieces = bitboards[f"{self.opponent_color}_{piece_name}s"]
            pst = PST_MAP[f"{self.opponent_color}_pawn"] if piece_name == "pawn" else PST_MAP[piece_name]
            while opp_pieces:
                lsb = opp_pieces & -opp_pieces
                opp_pieces ^= lsb
                idx = lsb.bit_length() - 1
                score -= (PIECE_VALUES[piece_name] + pst[idx])

        if is_in_check(bitboards, self.my_color): score -= 50
        if is_in_check(bitboards, self.opponent_color): score += 50
        return score

    def get_piece_name_at(self, bitboards, square_index, color):
        bit = 1 << square_index
        for name in PIECE_NAMES:
            if bitboards[f"{color}_{name}s"] & bit:
                return name
        return None

    def coords_to_move_object(self, board, coords):
        start_sq, end_sq = coords
        start_x, start_y = start_sq % 5, start_sq // 5
        end_x, end_y = end_sq % 5, end_sq // 5
        
        moving_piece = None
        current_player_obj = self.board_player_obj(board)
        for p in board.get_player_pieces(current_player_obj):
            if p.position.x == start_x and p.position.y == start_y:
                moving_piece = p
                break
        
        if moving_piece:
            for move_opt in moving_piece.get_move_options():
                if move_opt.position.x == end_x and move_opt.position.y == end_y:
                    return moving_piece, move_opt
        return None, None

    def board_player_obj(self, board):
        for p in board.players:
            if p.name.lower() == self.my_color:
                return p
        return board.current_player

# --- HIGH PERFORMANCE MOVE APPLICATION ---

def make_move(bitboards, start_sq, end_sq, piece_name, color, ep_target):
    """
    Applies move IN-PLACE.
    Returns undo_info tuple: (captured_piece_name, captured_sq, is_promotion, is_ep)
    """
    opponent_color = "black" if color == "white" else "white"
    start_bit = 1 << start_sq
    end_bit = 1 << end_sq

    # 1. Remove from Start
    bitboards[f"{color}_{piece_name}s"] ^= start_bit
    bitboards[f"{color}_occupied"] ^= start_bit
    bitboards["all_occupied"] ^= start_bit

    captured_piece_name = None
    captured_sq = None
    is_ep_capture = False
    is_promotion = False

    # 2. Handle Capture
    # Standard Capture
    if bitboards[f"{opponent_color}_occupied"] & end_bit:
        captured_sq = end_sq
        for name in PIECE_NAMES:
            key = f"{opponent_color}_{name}s"
            if bitboards[key] & end_bit:
                captured_piece_name = name
                bitboards[key] ^= end_bit
                bitboards[f"{opponent_color}_occupied"] ^= end_bit
                bitboards["all_occupied"] ^= end_bit
                break
    # En Passant Capture
    elif piece_name == "pawn" and end_bit == ep_target:
        is_ep_capture = True
        capture_y = (end_sq // 5) + 1 if color == "white" else (end_sq // 5) - 1
        capture_x = end_sq % 5
        captured_sq = capture_y * 5 + capture_x
        captured_bit = 1 << captured_sq
        
        captured_piece_name = "pawn"
        bitboards[f"{opponent_color}_pawns"] ^= captured_bit
        bitboards[f"{opponent_color}_occupied"] ^= captured_bit
        bitboards["all_occupied"] ^= captured_bit

    # 3. Handle Promotion
    if piece_name == "pawn":
        end_y = end_sq // 5
        if (color == "white" and end_y == 0) or (color == "black" and end_y == 4):
            is_promotion = True

    # 4. Place at Destination
    target_key = f"{color}_queens" if is_promotion else f"{color}_{piece_name}s"
    bitboards[target_key] ^= end_bit
    
    bitboards[f"{color}_occupied"] ^= end_bit
    bitboards["all_occupied"] ^= end_bit

    return (captured_piece_name, captured_sq, is_promotion, is_ep_capture)

def unmake_move(bitboards, start_sq, end_sq, piece_name, color, undo_info):
    """Reverses a move IN-PLACE using undo_info."""
    captured_name, captured_sq, is_promotion, is_ep = undo_info
    opponent_color = "black" if color == "white" else "white"
    start_bit = 1 << start_sq
    end_bit = 1 << end_sq

    # 1. Remove piece from Destination
    target_key = f"{color}_queens" if is_promotion else f"{color}_{piece_name}s"
    bitboards[target_key] ^= end_bit
    bitboards[f"{color}_occupied"] ^= end_bit
    bitboards["all_occupied"] ^= end_bit

    # 2. Restore captured piece (if any)
    if captured_name:
        captured_bit = 1 << captured_sq
        bitboards[f"{opponent_color}_{captured_name}s"] ^= captured_bit
        bitboards[f"{opponent_color}_occupied"] ^= captured_bit
        bitboards["all_occupied"] ^= captured_bit

    # 3. Restore piece to Start
    bitboards[f"{color}_{piece_name}s"] ^= start_bit
    bitboards[f"{color}_occupied"] ^= start_bit
    bitboards["all_occupied"] ^= start_bit

# --- Global Instance ---
_bot_instance = AlphaBetaAgent(depth=MAX_DEPTH)

def agent(board, player, var):
    return _bot_instance.get_move(board, player, var)


# --- HELPER FUNCTIONS ---

PIECE_NAMES = ["pawn", "right", "knight", "bishop", "queen", "king"]

def initialize_bitboards():
    bitboards = {}
    for color in ["white", "black"]:
        for piece_name in PIECE_NAMES:
            key = f"{color}_{piece_name}s" 
            bitboards[key] = 0
        bitboards[f"{color}_occupied"] = 0
    bitboards["all_occupied"] = 0
    return bitboards

def board_to_bitboards(board):
    bitboards = initialize_bitboards()
    for piece in board.get_pieces():
        try:
            x = piece.position.x
            y = piece.position.y
            piece_name = piece.name.lower()
            player_name = piece.player.name.lower()

            if player_name not in ["white", "black"] or piece_name not in PIECE_NAMES:
                continue
                
            bit_index = y * 5 + x
            bit_value = 1 << bit_index
            
            key = f"{player_name}_{piece_name}s"
            bitboards[key] |= bit_value
            bitboards[f"{player_name}_occupied"] |= bit_value
            bitboards["all_occupied"] |= bit_value
            
        except AttributeError as e:
            print(f"Warning: Error processing piece {piece}: {e}")
    return bitboards

def get_sliding_moves_bitmask(square_index, all_occupied, own_occupied, piece_name):
    moves_mask = 0
    start_x = square_index % 5
    start_y = square_index // 5
    directions = []
    
    if piece_name in ["bishop", "queen"]:
        directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
    if piece_name in ["right", "queen"]:
        directions.extend([(0, 1), (0, -1), (1, 0), (-1, 0)])
    
    for dx, dy in directions:
        curr_x, curr_y = start_x + dx, start_y + dy
        while 0 <= curr_x < 5 and 0 <= curr_y < 5:
            target_sq = curr_y * 5 + curr_x
            target_bit = 1 << target_sq
            
            if own_occupied & target_bit:
                break
            moves_mask |= target_bit
            if all_occupied & target_bit:
                break
            curr_x += dx
            curr_y += dy
    return moves_mask

def get_pawn_moves_bitmask(square_index, color, all_occupied, opponent_occupied, en_passant_target_bit=0):
    moves_mask = 0
    x = square_index % 5
    y = square_index // 5
    
    if color == "white":
        dy = -1; start_rank = 3
    else:
        dy = 1; start_rank = 1
        
    # Push
    curr_y = y + dy
    if 0 <= curr_y < 5:
        target_sq = curr_y * 5 + x
        target_bit = 1 << target_sq
        if not (all_occupied & target_bit):
            moves_mask |= target_bit
            
            # FIXED PAWN DOUBLE JUMP LOGIC (MUST CHECK PATH)
            if y == start_rank:
                double_y = y + (dy * 2)
                if 0 <= double_y < 5:
                    double_sq = double_y * 5 + x
                    double_bit = 1 << double_sq
                    if not (all_occupied & double_bit):
                        moves_mask |= double_bit

    # Capture
    for dx in [-1, 1]:
        cap_x = x + dx
        cap_y = y + dy
        if 0 <= cap_x < 5 and 0 <= cap_y < 5:
            target_sq = cap_y * 5 + cap_x
            target_bit = 1 << target_sq
            if (opponent_occupied & target_bit) or (en_passant_target_bit & target_bit):
                moves_mask |= target_bit
    return moves_mask

def get_jumping_moves_bitmask(square_index, own_occupied):
    moves_mask = 0
    x = square_index % 5
    y = square_index // 5
    offsets = [(1, 2), (1, -2), (-1, 2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)]
    for dx, dy in offsets:
        target_x = x + dx
        target_y = y + dy
        if 0 <= target_x < 5 and 0 <= target_y < 5:
            target_sq = target_y * 5 + target_x
            target_bit = 1 << target_sq
            if not (own_occupied & target_bit):
                moves_mask |= target_bit
    return moves_mask

def get_king_moves_bitmask(square_index, own_occupied):
    moves_mask = 0
    x = square_index % 5
    y = square_index // 5
    offsets = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    for dx, dy in offsets:
        target_x = x + dx
        target_y = y + dy
        if 0 <= target_x < 5 and 0 <= target_y < 5:
            target_sq = target_y * 5 + target_x
            target_bit = 1 << target_sq
            if not (own_occupied & target_bit):
                moves_mask |= target_bit
    return moves_mask

def get_pawn_attacks_bitmask(square_index, color):
    attacks = 0
    x = square_index % 5
    y = square_index // 5
    if color == "white": dy = -1
    else: dy = 1
    for dx in [-1, 1]:
        target_x = x + dx
        target_y = y + dy
        if 0 <= target_x < 5 and 0 <= target_y < 5:
            attacks |= (1 << (target_y * 5 + target_x))
    return attacks

def get_all_attacked_squares(bitboards, attacking_color):
    attacked_squares = 0
    all_occupied = bitboards["all_occupied"]
    attacker_occupied = bitboards[f"{attacking_color}_occupied"]
    
    pawn_bits = bitboards[f"{attacking_color}_pawns"]
    for i in range(25):
        if (pawn_bits >> i) & 1:
            attacked_squares |= get_pawn_attacks_bitmask(i, attacking_color)
            
    bishop_bits = bitboards[f"{attacking_color}_bishops"]
    for i in range(25):
        if (bishop_bits >> i) & 1:
            attacked_squares |= get_sliding_moves_bitmask(i, all_occupied, attacker_occupied, "bishop")
            
    queen_bits = bitboards[f"{attacking_color}_queens"]
    for i in range(25):
        if (queen_bits >> i) & 1:
            attacked_squares |= get_sliding_moves_bitmask(i, all_occupied, attacker_occupied, "queen")

    right_bits = bitboards[f"{attacking_color}_rights"]
    for i in range(25):
        if (right_bits >> i) & 1:
            attacked_squares |= get_sliding_moves_bitmask(i, all_occupied, attacker_occupied, "right")
            attacked_squares |= get_jumping_moves_bitmask(i, attacker_occupied)
            
    knight_bits = bitboards[f"{attacking_color}_knights"]
    for i in range(25):
        if (knight_bits >> i) & 1:
            attacked_squares |= get_jumping_moves_bitmask(i, attacker_occupied)
            
    king_bits = bitboards[f"{attacking_color}_kings"]
    for i in range(25):
        if (king_bits >> i) & 1:
            attacked_squares |= get_king_moves_bitmask(i, attacker_occupied)
            
    return attacked_squares

def is_in_check(bitboards, color):
    opponent_color = "black" if color == "white" else "white"
    attacked_mask = get_all_attacked_squares(bitboards, opponent_color)
    king_bitboard = bitboards[f"{color}_kings"]
    if (king_bitboard & attacked_mask):
        return True
    return False

def get_possible_moves(bitboards, color, en_passant_target_bit=0):
    possible_moves = []
    all_occupied = bitboards["all_occupied"]
    own_occupied = bitboards[f"{color}_occupied"]
    opponent_occupied = bitboards[f"black_occupied"] if color == "white" else bitboards[f"white_occupied"]
    
    for piece_name in PIECE_NAMES:
        piece_bits = bitboards[f"{color}_{piece_name}s"]
        for i in range(25):
            if (piece_bits >> i) & 1:
                start_sq = i
                moves_mask = 0
                if piece_name == "pawn":
                    moves_mask = get_pawn_moves_bitmask(start_sq, color, all_occupied, opponent_occupied, en_passant_target_bit)
                elif piece_name == "knight":
                    moves_mask = get_jumping_moves_bitmask(start_sq, own_occupied)
                elif piece_name == "bishop":
                    moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, "bishop")
                elif piece_name == "right":
                    moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, "right")
                    moves_mask |= get_jumping_moves_bitmask(start_sq, own_occupied)
                elif piece_name == "queen":
                    moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, "queen")
                elif piece_name == "king":
                    moves_mask = get_king_moves_bitmask(start_sq, own_occupied)
                
                for target_sq in range(25):
                    if (moves_mask >> target_sq) & 1:
                        # Safety Check
                        undo_info = make_move(bitboards, start_sq, target_sq, piece_name, color, en_passant_target_bit)
                        is_safe = not is_in_check(bitboards, color)
                        unmake_move(bitboards, start_sq, target_sq, piece_name, color, undo_info)
                        
                        if is_safe:
                            possible_moves.append((start_sq, target_sq))
                            
    return possible_moves