import time
import math
import random

# --- Constants ---
TIMEOUT_BUFFER = 0.4
MATE_SCORE = 30000
MAX_DEPTH = 30
TT_SIZE = 1048576  # 2^20 entries

# TT Flag Constants
TT_EXACT = 0
TT_LOWERBOUND = 1
TT_UPPERBOUND = 2

# Piece Constants (Indices for list-based bitboards)
PAWN, RIGHT, KNIGHT, BISHOP, QUEEN, KING = 0, 1, 2, 3, 4, 5
PIECE_INDICES = { "pawn": 0, "right": 1, "knight": 2, "bishop": 3, "queen": 4, "king": 5 }
PIECE_NAMES = ["pawn", "right", "knight", "bishop", "queen", "king"]

# --- Advanced Piece-Square Tables (5x5 Specialized) ---
PIECE_VALUES = [103, 312, 336, 398, 900, 20000]

# Helper to flip tables for Black (Mirror Rank 0 <-> Rank 4)
def mirror_pst(pst):
    return pst[::-1] # In a flat 25-item list, reversing it perfectly mirrors 5x5 ranks

# 1. THE RIGHT (Knook): "The Queen Killer"
# Prioritizes the absolute center (Index 12) to maximize Jumps + Slides.
PST_RIGHT_WHITE = [
    5,  10,  10,  10,  5,   # Rank 0 (Attack Zone)
    10, 30,  35,  30, 10,   # Rank 1
    10, 35,  60,  35, 10,   # Rank 2 (God Square)
    10, 30,  35,  30, 10,   # Rank 3
    5,  10,  15,  10,  5    # Rank 4 (Home)
]
PST_RIGHT_BLACK = mirror_pst(PST_RIGHT_WHITE)

# 2. THE QUEEN
# Strong center, but slightly less aggressive penalty on edges than Right
# because she relies on diagonals which can be long from edges.
PST_QUEEN_WHITE = [
    5,  10,  10,  10,  5,
    10, 20,  25,  20, 10,
    10, 25,  40,  25, 10,
    10, 20,  25,  20,  10,
    5,  10,  10,  10,  5
]
PST_QUEEN_BLACK = mirror_pst(PST_QUEEN_WHITE)

# 3. KING SAFETY (Midgame)
# Avoids corners (traps). Prefers "Pocket" at Rank 4, Files 1-3.
PST_KING_SAFETY_WHITE = [
    -50, -50, -50, -50, -50, # Rank 0 (Suicide)
    -30, -30, -30, -30, -30, # Rank 1
    -30, -20, -20, -20, -30, # Rank 2
    -20,   0,   0,   0, -20, # Rank 3
    -40,  20,  30,  20, -40  # Rank 4 (Home: Corners unsafe, Center safe)
]
PST_KING_SAFETY_BLACK = mirror_pst(PST_KING_SAFETY_WHITE)

# 4. KING ACTIVITY (Endgame)
# When major threats are gone, King becomes a fighter.
PST_KING_ACTIVE_WHITE = [
    -10,  10,  20,  10, -10,
    10,  20,  30,  20,  10,
    20,  30,  40,  30,  20,
    10,  20,  30,  20,  10,
    -10,  10,  20,  10, -10
]
PST_KING_ACTIVE_BLACK = mirror_pst(PST_KING_ACTIVE_WHITE)

# 5. KNIGHT / BISHOP (Generic Centralization)
PST_MINOR_WHITE = [
    -10, -5, -5, -5, -10,
    -5,   5, 10,  5, -5,
    -5,  10, 20, 10, -5,
    -5,   5, 10,  5, -5,
    -10, -5, -5, -5, -10
]
PST_MINOR_BLACK = PST_MINOR_WHITE # Symmetric

# Pawns (Retain existing, just ensuring naming consistency)
PST_PAWN_WHITE = [
    0,   0,   0,   0,   0,   # Rank 0 (Promotion happened)
    60,  60,  60,  60,  60,  # Rank 1 (1 step away - Huge incentive)
    30,  30,  35,  30,  30,  # Rank 2
    10,  10,  15,  10,  10,  # Rank 3
    0,   0,   0,   0,   0    # Rank 4
]
PST_PAWN_BLACK = mirror_pst(PST_PAWN_WHITE)

# Lookup Tables for fast access [Color][Piece]
# 0: Pawn, 1: Right, 2: Knight, 3: Bishop, 4: Queen, 5: King
TABLES_WHITE = [PST_PAWN_WHITE, PST_RIGHT_WHITE, PST_MINOR_WHITE, PST_MINOR_WHITE, PST_QUEEN_WHITE, PST_KING_SAFETY_WHITE]
TABLES_BLACK = [PST_PAWN_BLACK, PST_RIGHT_BLACK, PST_MINOR_BLACK, PST_MINOR_BLACK, PST_QUEEN_BLACK, PST_KING_SAFETY_BLACK]

# --- Zobrist Hashing Initialization ---
random.seed(42)
# Z_PIECES: [color_idx][piece_idx][square]
Z_PIECES = [
    [[random.getrandbits(64) for _ in range(25)] for _ in range(6)], # White (0)
    [[random.getrandbits(64) for _ in range(25)] for _ in range(6)]  # Black (1)
]
Z_BLACK_TO_MOVE = random.getrandbits(64)
Z_EP = [random.getrandbits(64) for _ in range(25)] 

class TimeoutException(Exception):
    pass

class TranspositionTable:
    def __init__(self, size=TT_SIZE):
        self.size = size
        self.table = [None] * size

    def store(self, z_hash, depth, score, flag, best_move, ply):
        # 1. Normalization: Adjust Mate Score to be relative to root
        # This prevents "Mate in 5" found at depth 10 being read as "Mate in 5" at depth 2
        if score > MATE_SCORE - 1000: score += ply     
        elif score < -MATE_SCORE + 1000: score -= ply  
        
        index = z_hash % self.size
        entry = self.table[index]

        # 2. Replacement Strategy: Depth-Preferred
        # Overwrite if new entry is deeper OR if the current slot is empty
        # Also could prioritize EXACT scores, but Depth is usually sufficient.
        if entry is None or depth >= entry['depth']:
            self.table[index] = {
                'key': z_hash,
                'depth': depth,
                'score': score,
                'flag': flag,
                'best_move': best_move
            }

    def probe(self, z_hash, depth, alpha, beta, ply):
        index = z_hash % self.size
        entry = self.table[index]

        if entry and entry['key'] == z_hash:
            score = entry['score']
            
            # 3. Un-Normalization: Retrieve score relative to current ply
            if score > MATE_SCORE - 1000: score -= ply
            elif score < -MATE_SCORE + 1000: score += ply

            if entry['depth'] >= depth:
                if entry['flag'] == TT_EXACT:
                    return score, entry['best_move']
                if entry['flag'] == TT_LOWERBOUND and score >= beta:
                    return score, entry['best_move']
                if entry['flag'] == TT_UPPERBOUND and score <= alpha:
                    return score, entry['best_move']
            
            return None, entry['best_move']
            
        return None, None

    def clear(self):
        self.table = [None] * self.size

class AlphaBetaAgent:
    def __init__(self, depth=4):
        self.max_depth = depth
        self.tt = TranspositionTable()
        # History: [color][from][to]
        self.history = [[[0] * 25 for _ in range(25)] for _ in range(2)]
        self.killers = [[None] * 2 for _ in range(MAX_DEPTH + 1)]
        self.node_count = 0
        self.my_color_idx = 0

    def adjust_time_for_moves(self,ply,t):
        return max(1,t * (1 - (ply/40)))
    
    def get_move(self, board, player, time_budget_info):
        self.my_color_idx = 0 if player.name.lower() == "white" else 1
        
        start_time = time.perf_counter()
        
        time_limit = self.adjust_time_for_moves(time_budget_info[0],time_budget_info[1])
        print(time_limit)
        
        bitboards = board_to_bitboards(board)
        current_hash = self.compute_full_hash(bitboards, 0)
        
        best_move_coords = None
        best_score = 0
        
        # Reset per-search heuristics
        self.killers = [[None] * 2 for _ in range(MAX_DEPTH + 1)]
        # We generally KEEP History between moves, but scale it down to adapt to new position
        for c in range(2):
            for s in range(25):
                for e in range(25):
                    self.history[c][s][e] //= 8

        try:
            for current_depth in range(1, self.max_depth + 1):
                self.node_count = 0
                
                # Aspiration Windows (Optional optimization, sticking to standard AB for stability)
                move, score = self.find_best_move(
                    bitboards, 
                    current_depth, 
                    start_time, 
                    time_limit,
                    0, # root ep target
                    current_hash,
                    pv_move=best_move_coords
                )
                
                if move:
                    best_move_coords = move
                    best_score = score
                    print(f"Depth {current_depth} | Nodes: {self.node_count} | Best: {move} | Score: {score}")
                
                if score >= 29995:
                    break
                
                # Time Management: If >50% time used, don't start next depth
                if (time.perf_counter() - start_time) > (time_limit * 0.5):
                    break
                    
        except TimeoutException:
            print("Timeout! Returning best move from previous depth.")
        
        if best_move_coords:
            return self.coords_to_move_object(board, best_move_coords)
            
        # Fallback
        legal_moves = get_possible_moves(bitboards, self.my_color_idx, 0)
        if legal_moves:
            return self.coords_to_move_object(board, legal_moves[0])
        return None, None

    def find_best_move(self, bitboards, depth, start_time, time_limit, ep_target, current_hash, pv_move=None):
        alpha = float('-inf')
        beta = float('inf')
        
        moves = self.get_ordered_moves(bitboards, self.my_color_idx, ep_target, 0, pv_move=pv_move)
        if not moves: return None, 0
            
        best_move = moves[0]
        best_val = float('-inf')
        
        # Root search is explicit to handle the 'best_move' return value safely
        for start_sq, end_sq in moves:
            piece_idx = self.get_piece_index_at(bitboards, start_sq, self.my_color_idx)
            
            new_ep = 0
            if piece_idx == PAWN and abs(start_sq - end_sq) == 10:
                new_ep = 1 << ((start_sq + end_sq) // 2)

            # Note: We pass 0 as old_ep because at root we don't have the history of the previous EP
            hash_diff = self.get_hash_diff(bitboards, start_sq, end_sq, piece_idx, self.my_color_idx, ep_target, new_ep)
            new_hash = current_hash ^ hash_diff ^ Z_BLACK_TO_MOVE 

            undo_info = make_move(bitboards, start_sq, end_sq, piece_idx, self.my_color_idx, ep_target)
            
            try:
                val = -self.alpha_beta(bitboards, depth - 1, -beta, -alpha, start_time, time_limit, 
                                     1 - self.my_color_idx, 1, new_ep, new_hash)
            finally:
                unmake_move(bitboards, start_sq, end_sq, piece_idx, self.my_color_idx, undo_info)
            
            if val > best_val:
                best_val = val
                best_move = (start_sq, end_sq)
            
            alpha = max(alpha, best_val)
            
            if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
                raise TimeoutException()

        self.tt.store(current_hash, depth, best_val, TT_EXACT, best_move, 0)
        return best_move, best_val

    def alpha_beta(self, bitboards, depth, alpha, beta, start_time, time_limit, color_idx, ply, ep_target, current_hash):
        self.node_count += 1
        if self.node_count & 1023 == 0: 
            if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
                raise TimeoutException()

        tt_val, tt_move = self.tt.probe(current_hash, depth, alpha, beta, ply)
        if tt_val is not None:
            return tt_val

        if depth == 0:
            return self.quiescence_search(bitboards, alpha, beta, start_time, time_limit, color_idx, 0, ep_target)

        moves = self.get_ordered_moves(bitboards, color_idx, ep_target, ply, pv_move=tt_move)

        if not moves:
            return -MATE_SCORE + ply

        flag = TT_UPPERBOUND
        best_move = None
        max_val = float('-inf')

        for start_sq, end_sq in moves:
            piece_idx = self.get_piece_index_at(bitboards, start_sq, color_idx)
            
            new_ep = 0
            if piece_idx == PAWN and abs(start_sq - end_sq) == 10:
                new_ep = 1 << ((start_sq + end_sq) // 2)

            hash_diff = self.get_hash_diff(bitboards, start_sq, end_sq, piece_idx, color_idx, ep_target, new_ep)
            new_hash = current_hash ^ hash_diff ^ Z_BLACK_TO_MOVE

            undo_info = make_move(bitboards, start_sq, end_sq, piece_idx, color_idx, ep_target)
            val = -self.alpha_beta(bitboards, depth - 1, -beta, -alpha, start_time, time_limit, 1 - color_idx, ply + 1, new_ep, new_hash)
            unmake_move(bitboards, start_sq, end_sq, piece_idx, color_idx, undo_info)
            
            if val > max_val:
                max_val = val
                best_move = (start_sq, end_sq)

            if val >= beta:
                if undo_info[0] is None: # Quiet move
                    self.store_killer(ply, (start_sq, end_sq))
                    self.history[color_idx][start_sq][end_sq] += depth * depth
                
                self.tt.store(current_hash, depth, beta, TT_LOWERBOUND, (start_sq, end_sq), ply)
                return beta
            
            if val > alpha:
                alpha = val
                flag = TT_EXACT

        self.tt.store(current_hash, depth, max_val, flag, best_move, ply)
        return max_val

    def quiescence_search(self, bitboards, alpha, beta, start_time, time_limit, color_idx, q_depth, ep_target):
        self.node_count += 1
        if self.node_count & 1023 == 0:
            if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
                raise TimeoutException()

        stand_pat = self.evaluate(bitboards, color_idx)
        if stand_pat >= beta: return beta
        if stand_pat > alpha: alpha = stand_pat
        
        # Limit Q-Search depth to prevent explosion
        if q_depth > 10: return stand_pat

        # Only captures in Q-Search
        moves = self.get_ordered_moves(bitboards, color_idx, ep_target, 0, captures_only=True)
        
        for start_sq, end_sq in moves:
            piece_idx = self.get_piece_index_at(bitboards, start_sq, color_idx)
            undo_info = make_move(bitboards, start_sq, end_sq, piece_idx, color_idx, ep_target)
            score = -self.quiescence_search(bitboards, -beta, -alpha, start_time, time_limit, 1 - color_idx, q_depth + 1, 0)
            unmake_move(bitboards, start_sq, end_sq, piece_idx, color_idx, undo_info)
            
            if score >= beta: return beta
            if score > alpha: alpha = score
            
        return alpha

    def get_ordered_moves(self, bitboards, color_idx, ep_target, ply, captures_only=False, pv_move=None):
        moves = get_possible_moves(bitboards, color_idx, ep_target)
        if not moves: return []
        
        opp_color_idx = 1 - color_idx
        # Opponent occupied is index 13 (7*1 + 6) or 6 (7*0 + 6)
        opp_occupied = bitboards[opp_color_idx * 7 + 6]
        
        scored_moves = []
        
        killer1 = self.killers[ply][0] if ply < MAX_DEPTH else None
        killer2 = self.killers[ply][1] if ply < MAX_DEPTH else None

        for start, end in moves:
            score = 0
            
            # 1. PV Move
            if pv_move and (start == pv_move[0] and end == pv_move[1]):
                score = 2000000
            else:
                target_bit = 1 << end
                is_capture = (opp_occupied & target_bit) or (target_bit == ep_target)
                
                if is_capture:
                    attacker = self.get_piece_index_at(bitboards, start, color_idx)
                    victim = PAWN
                    if opp_occupied & target_bit:
                        victim = self.get_piece_index_at(bitboards, end, opp_color_idx)
                    score = 1000000 + (PIECE_VALUES[victim] * 10) - PIECE_VALUES[attacker]
                    
                else:
                    if captures_only: continue
                    # 2. Killers
                    if (start, end) == killer1: score = 900000
                    elif (start, end) == killer2: score = 800000
                    else:
                        # 3. History
                        score = self.history[color_idx][start][end]
            
            scored_moves.append((score, (start, end)))
            
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [m for s, m in scored_moves]

    def store_killer(self, ply, move):
        if ply < MAX_DEPTH:
            if self.killers[ply][0] != move:
                self.killers[ply][1] = self.killers[ply][0]
                self.killers[ply][0] = move

    def evaluate(self, bitboards, color_idx):
        score = 0
        
        # 1. Identify Game Phase
        # If opponent has a Queen(4) or Right(1), King must be Safe.
        # Otherwise, King should be Active.
        opp_idx = 1 - color_idx
        base_opp = opp_idx * 7
        
        # Check if opponent has dangerous heavy pieces
        opp_has_heavy = (bitboards[base_opp + QUEEN] | bitboards[base_opp + RIGHT]) != 0
        
        # 2. Score My Pieces
        base_own = color_idx * 7
        
        # Mobility counter (pseudo-mobility to detect stalemate danger)
        my_mobility_score = 0 
        
        for p_idx in range(6):
            pieces = bitboards[base_own + p_idx]
            if not pieces: continue
            
            # Select correct PST
            if p_idx == KING:
                if color_idx == 0:
                    pst = PST_KING_SAFETY_WHITE if opp_has_heavy else PST_KING_ACTIVE_WHITE
                else:
                    pst = PST_KING_SAFETY_BLACK if opp_has_heavy else PST_KING_ACTIVE_BLACK
            elif color_idx == 0:
                pst = TABLES_WHITE[p_idx]
            else:
                pst = TABLES_BLACK[p_idx]
            
            val = PIECE_VALUES[p_idx]
            
            while pieces:
                lsb = pieces & -pieces
                pieces ^= lsb
                idx = lsb.bit_length() - 1
                
                # Material + Positional
                score += val + pst[idx]
                
                # Pseudo-Mobility Bonus:
                # In 5x5, having space is life. We add small bonuses for center proximity 
                # for sliding pieces as a proxy for mobility calculation (which is expensive).
                if p_idx in [RIGHT, QUEEN, BISHOP]:
                    # Indices 6,7,8, 11,12,13, 16,17,18 are central-ish
                    if idx in [6, 7, 8, 11, 12, 13, 16, 17, 18]:
                        my_mobility_score += 5

        # 3. Score Opponent Pieces
        # We need to check if *WE* have heavy pieces to dictate *THEIR* King safety
        my_has_heavy = (bitboards[base_own + QUEEN] | bitboards[base_own + RIGHT]) != 0
        
        for p_idx in range(6):
            pieces = bitboards[base_opp + p_idx]
            if not pieces: continue
            
            if p_idx == KING:
                if opp_idx == 0:
                    pst = PST_KING_SAFETY_WHITE if my_has_heavy else PST_KING_ACTIVE_WHITE
                else:
                    pst = PST_KING_SAFETY_BLACK if my_has_heavy else PST_KING_ACTIVE_BLACK
            elif opp_idx == 0:
                pst = TABLES_WHITE[p_idx]
            else:
                pst = TABLES_BLACK[p_idx]
                
            val = PIECE_VALUES[p_idx]
            while pieces:
                lsb = pieces & -pieces
                pieces ^= lsb
                idx = lsb.bit_length() - 1
                score -= (val + pst[idx])

        # 4. Mobility Adjustment
        # If the search sees 0 legal moves, it returns Mate score. 
        # But here we give a small nudge to positions that "look" free.
        score += my_mobility_score

        return score
    
    def compute_full_hash(self, bitboards, ep_target):
        h = 0
        for c in range(2):
            base = c * 7
            for p in range(6):
                pieces = bitboards[base + p]
                if pieces:
                    # Iterate set bits
                    temp = pieces
                    while temp:
                        lsb = temp & -temp
                        temp ^= lsb
                        sq = lsb.bit_length() - 1
                        h ^= Z_PIECES[c][p][sq]
        
        if ep_target:
            idx = ep_target.bit_length() - 1
            h ^= Z_EP[idx]
        return h

    def get_hash_diff(self, bitboards, start, end, piece, color, old_ep, new_ep):
        h = 0
        h ^= Z_PIECES[color][piece][start]
        
        target_piece = piece
        # Promotion check
        if piece == PAWN and ((color == 0 and end < 5) or (color == 1 and end >= 20)):
            target_piece = QUEEN
        h ^= Z_PIECES[color][target_piece][end]
        
        opp_color = 1 - color
        opp_occupied = bitboards[opp_color * 7 + 6]
        
        if opp_occupied & (1 << end):
            # Capture
            victim = self.get_piece_index_at(bitboards, end, opp_color)
            h ^= Z_PIECES[opp_color][victim][end]
        elif piece == PAWN and (1 << end) == old_ep:
            # EP Capture
            cap_idx = end + 5 if color == 0 else end - 5
            h ^= Z_PIECES[opp_color][PAWN][cap_idx]

        if old_ep: h ^= Z_EP[old_ep.bit_length() - 1]
        if new_ep: h ^= Z_EP[new_ep.bit_length() - 1]
        return h

    def get_piece_index_at(self, bitboards, sq, color_idx):
        bit = 1 << sq
        base = color_idx * 7
        for i in range(6):
            if bitboards[base + i] & bit:
                return i
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
        target = "white" if self.my_color_idx == 0 else "black"
        for p in board.players:
            if p.name.lower() == target:
                return p
        return board.current_player

# --- HIGH PERFORMANCE MOVE APPLICATION ---

def make_move(bitboards, start_sq, end_sq, piece_idx, color_idx, ep_target):
    """
    Applies move IN-PLACE using integer lists.
    Indices: 0-5 (White Pieces), 6 (White Occ), 7-12 (Black Pieces), 13 (Black Occ), 14 (All Occ)
    """
    opp_color_idx = 1 - color_idx
    base_own = color_idx * 7
    base_opp = opp_color_idx * 7
    
    start_bit = 1 << start_sq
    end_bit = 1 << end_sq

    # 1. Remove from Start
    bitboards[base_own + piece_idx] ^= start_bit
    bitboards[base_own + 6] ^= start_bit
    bitboards[14] ^= start_bit

    captured_piece_idx = None
    captured_sq = None
    is_ep_capture = False
    is_promotion = False

    # 2. Handle Capture
    if bitboards[base_opp + 6] & end_bit:
        captured_sq = end_sq
        # Find which piece was captured
        for i in range(6):
            if bitboards[base_opp + i] & end_bit:
                captured_piece_idx = i
                bitboards[base_opp + i] ^= end_bit
                bitboards[base_opp + 6] ^= end_bit
                bitboards[14] ^= end_bit
                break
    elif piece_idx == PAWN and end_bit == ep_target:
        is_ep_capture = True
        capture_y = (end_sq // 5) + 1 if color_idx == 0 else (end_sq // 5) - 1
        capture_x = end_sq % 5
        captured_sq = capture_y * 5 + capture_x
        captured_bit = 1 << captured_sq
        
        captured_piece_idx = PAWN
        bitboards[base_opp + PAWN] ^= captured_bit
        bitboards[base_opp + 6] ^= captured_bit
        bitboards[14] ^= captured_bit

    # 3. Handle Promotion
    if piece_idx == PAWN:
        end_y = end_sq // 5
        if (color_idx == 0 and end_y == 0) or (color_idx == 1 and end_y == 4):
            is_promotion = True

    # 4. Place at Destination
    target_idx = QUEEN if is_promotion else piece_idx
    bitboards[base_own + target_idx] ^= end_bit
    bitboards[base_own + 6] ^= end_bit
    bitboards[14] ^= end_bit

    return (captured_piece_idx, captured_sq, is_promotion, is_ep_capture)

def unmake_move(bitboards, start_sq, end_sq, piece_idx, color_idx, undo_info):
    captured_idx, captured_sq, is_promotion, is_ep = undo_info
    
    opp_color_idx = 1 - color_idx
    base_own = color_idx * 7
    base_opp = opp_color_idx * 7
    
    start_bit = 1 << start_sq
    end_bit = 1 << end_sq

    # 1. Remove piece from Destination
    target_idx = QUEEN if is_promotion else piece_idx
    bitboards[base_own + target_idx] ^= end_bit
    bitboards[base_own + 6] ^= end_bit
    bitboards[14] ^= end_bit

    # 2. Restore captured piece
    if captured_idx is not None:
        captured_bit = 1 << captured_sq
        bitboards[base_opp + captured_idx] ^= captured_bit
        bitboards[base_opp + 6] ^= captured_bit
        bitboards[14] ^= captured_bit

    # 3. Restore piece to Start
    bitboards[base_own + piece_idx] ^= start_bit
    bitboards[base_own + 6] ^= start_bit
    bitboards[14] ^= start_bit

# --- Global Instance ---
_bot_instance = AlphaBetaAgent(depth=MAX_DEPTH)

def agent(board, player, var):
    print(var)
    return _bot_instance.get_move(board, player, var)

# --- HELPER FUNCTIONS ---

def initialize_bitboards():
    # 0-5: White P,R,N,B,Q,K
    # 6: White Occ
    # 7-12: Black P,R,N,B,Q,K
    # 13: Black Occ
    # 14: All Occ
    return [0] * 15

def board_to_bitboards(board):
    bb = initialize_bitboards()
    for piece in board.get_pieces():
        try:
            x = piece.position.x
            y = piece.position.y
            p_name = piece.name.lower()
            pl_name = piece.player.name.lower()

            if pl_name not in ["white", "black"] or p_name not in PIECE_INDICES:
                continue
                
            bit_index = y * 5 + x
            bit_value = 1 << bit_index
            
            p_idx = PIECE_INDICES[p_name]
            c_idx = 0 if pl_name == "white" else 1
            
            base = c_idx * 7
            bb[base + p_idx] |= bit_value
            bb[base + 6] |= bit_value
            bb[14] |= bit_value
            
        except AttributeError:
            continue
    return bb

# --- Low Level Move Generation (Unchanged logic, updated calling convention) ---

def get_sliding_moves_bitmask(square_index, all_occupied, own_occupied, piece_idx):
    moves_mask = 0
    start_x = square_index % 5
    start_y = square_index // 5
    directions = []
    
    # Bishop(3), Queen(4)
    if piece_idx in [3, 4]:
        directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
    # Right(1), Queen(4)
    if piece_idx in [1, 4]:
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

def get_pawn_moves_bitmask(square_index, color_idx, all_occupied, opponent_occupied, en_passant_target_bit=0):
    moves_mask = 0
    x = square_index % 5
    y = square_index // 5
    
    if color_idx == 0: # White
        dy = -1; start_rank = 3
    else:
        dy = 1; start_rank = 1
        
    curr_y = y + dy
    if 0 <= curr_y < 5:
        target_sq = curr_y * 5 + x
        target_bit = 1 << target_sq
        if not (all_occupied & target_bit):
            moves_mask |= target_bit
            
            if y == start_rank:
                double_y = y + (dy * 2)
                if 0 <= double_y < 5:
                    double_sq = double_y * 5 + x
                    double_bit = 1 << double_sq
                    if not (all_occupied & double_bit):
                        moves_mask |= double_bit

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

def get_pawn_attacks_bitmask(square_index, color_idx):
    attacks = 0
    x = square_index % 5
    y = square_index // 5
    dy = -1 if color_idx == 0 else 1
    for dx in [-1, 1]:
        target_x = x + dx
        target_y = y + dy
        if 0 <= target_x < 5 and 0 <= target_y < 5:
            attacks |= (1 << (target_y * 5 + target_x))
    return attacks

def get_all_attacked_squares(bitboards, attacking_color_idx):
    attacked_squares = 0
    all_occupied = bitboards[14]
    
    base_atk = attacking_color_idx * 7
    attacker_occupied = bitboards[base_atk + 6]
    
    # Pawns
    pawn_bits = bitboards[base_atk + PAWN]
    for i in range(25):
        if (pawn_bits >> i) & 1:
            attacked_squares |= get_pawn_attacks_bitmask(i, attacking_color_idx)
            
    # Sliding (Bishop 3, Queen 4, Right 1)
    for p_idx in [BISHOP, QUEEN, RIGHT]:
        bits = bitboards[base_atk + p_idx]
        if bits:
            for i in range(25):
                if (bits >> i) & 1:
                    attacked_squares |= get_sliding_moves_bitmask(i, all_occupied, attacker_occupied, p_idx)

    # Jumping (Knight 2, Right 1 has jumps too? Logic says Right is sliding+jumping? 
    # Wait, the original code had Right as sliding + jumping.
    # In original: "right" had sliding AND jumping calls.
    # Let's verify 'get_sliding' handles 'right'. Yes, I added logic there.
    # Now adding Jumping logic for Right and Knight.
    for p_idx in [KNIGHT, RIGHT]:
        bits = bitboards[base_atk + p_idx]
        if bits:
            for i in range(25):
                if (bits >> i) & 1:
                    attacked_squares |= get_jumping_moves_bitmask(i, attacker_occupied)
            
    # King
    king_bits = bitboards[base_atk + KING]
    if king_bits:
        i = king_bits.bit_length() - 1
        attacked_squares |= get_king_moves_bitmask(i, attacker_occupied)
            
    return attacked_squares

def is_in_check(bitboards, color_idx):
    opp_idx = 1 - color_idx
    attacked_mask = get_all_attacked_squares(bitboards, opp_idx)
    king_bitboard = bitboards[color_idx * 7 + KING]
    if (king_bitboard & attacked_mask):
        return True
    return False

def get_possible_moves(bitboards, color_idx, en_passant_target_bit=0):
    possible_moves = []
    all_occupied = bitboards[14]
    base = color_idx * 7
    own_occupied = bitboards[base + 6]
    
    opp_idx = 1 - color_idx
    opp_occupied = bitboards[opp_idx * 7 + 6]
    
    for p_idx in range(6):
        piece_bits = bitboards[base + p_idx]
        if not piece_bits: continue
        
        # Iterate bits
        temp = piece_bits
        while temp:
            lsb = temp & -temp
            temp ^= lsb
            start_sq = lsb.bit_length() - 1
            
            moves_mask = 0
            if p_idx == PAWN:
                moves_mask = get_pawn_moves_bitmask(start_sq, color_idx, all_occupied, opp_occupied, en_passant_target_bit)
            elif p_idx == KNIGHT:
                moves_mask = get_jumping_moves_bitmask(start_sq, own_occupied)
            elif p_idx == BISHOP:
                moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, BISHOP)
            elif p_idx == RIGHT:
                moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, RIGHT)
                moves_mask |= get_jumping_moves_bitmask(start_sq, own_occupied)
            elif p_idx == QUEEN:
                moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, QUEEN)
            elif p_idx == KING:
                moves_mask = get_king_moves_bitmask(start_sq, own_occupied)
            
            while moves_mask:
                lsb_target = moves_mask & -moves_mask
                moves_mask ^= lsb_target
                target_sq = lsb_target.bit_length() - 1
                
                # Verify safety
                undo = make_move(bitboards, start_sq, target_sq, p_idx, color_idx, en_passant_target_bit)
                if not is_in_check(bitboards, color_idx):
                    possible_moves.append((start_sq, target_sq))
                unmake_move(bitboards, start_sq, target_sq, p_idx, color_idx, undo)
                            
    return possible_moves