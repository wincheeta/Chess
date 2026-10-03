import math
from extension.board_utils import list_legal_moves_for, copy_piece_move, take_notes
from extension.board_rules import get_result
import time
import random

PIECE_VALUES = {
    "pawn": 100,
    "knight": 320,
    "bishop": 330,
    "right": 700,  # This custom piece is very strong (Rook + Knight)
    "queen": 900,
    "king": 20000
}

TIMEOUT_DEADLINE = 0.25
class TimeoutException(Exception):
    pass
TIMEOUT_BUFFER = 0.5
PIECE_VALUES = {
    "pawn": 100,
    "knight": 320,
    "bishop": 330,
    "right": 400,  # Stronger than knight/bishop due to flexibility?
    "rook": 500,   # If standard rook existed
    "queen": 900,
    "king": 20000
}

class AlphaBetaAgent:
    def __init__(self, depth=4):
        self.depth = depth
        self.my_color = None
        self.opponent_color = None

    def get_move(self, board, player, time_budget_info):
        """
        Main entry point.
        time_budget_info is usually a list: [ply_number, time_limit_in_seconds]
        """
        self.my_color = player.name.lower()
        self.opponent_color = "black" if self.my_color == "white" else "white"
        
        # Handle time budget
        start_time = time.perf_counter()
        time_limit = time_budget_info[1] if time_budget_info else 14.0
        
        # 1. Convert Board to Bitboards
        bitboards = board_to_bitboards(board)
        
        # 2. Run Alpha-Beta Search
        try:
            best_move_coords = self.find_best_move(bitboards, self.depth, start_time, time_limit)
        except TimeoutException:
            # If we timed out, just return whatever we have or None
            print("Timeout reached in search.")
            best_move_coords = None

        # 3. Convert back to chessmaker objects
        if best_move_coords:
            return self.coords_to_move_object(board, best_move_coords)
            
        # Fallback: If search failed or timed out, try to get ANY valid move quickly
        legal_moves = get_possible_moves(bitboards, self.my_color)
        if legal_moves:
            return self.coords_to_move_object(board, legal_moves[0])
            
        return None, None

    def coords_to_move_object(self, board, coords):
        start_sq, end_sq = coords
        start_x, start_y = start_sq % 5, start_sq // 5
        end_x, end_y = end_sq % 5, end_sq // 5
        
        moving_piece = None
        for p in board.get_player_pieces(self.board_player_obj(board)):
            if p.position.x == start_x and p.position.y == start_y:
                moving_piece = p
                break
        
        if moving_piece:
            for move_opt in moving_piece.get_move_options():
                if move_opt.position.x == end_x and move_opt.position.y == end_y:
                    return moving_piece, move_opt
        return None, None

    def board_player_obj(self, board):
        # Helper to get the actual player object from the board
        for p in board.players:
            if p.name.lower() == self.my_color:
                return p
        return board.current_player

    def find_best_move(self, bitboards, depth, start_time, time_limit):
        alpha = float('-inf')
        beta = float('inf')
        
        # Initial move generation
        moves = self.get_ordered_moves(bitboards, self.my_color)
        
        if not moves:
            return None
            
        best_move = moves[0] # Default to first move
        best_val = float('-inf')
        
        for start_sq, end_sq in moves:
            piece_name = self.get_piece_name_at(bitboards, start_sq, self.my_color)
            new_bitboards = apply_move_from_coords(bitboards, start_sq, end_sq, piece_name, self.my_color)
            
            # Start recursive search
            val = self.alpha_beta(new_bitboards, depth - 1, alpha, beta, start_time, time_limit, is_maximizing=False)
            
            if val > best_val:
                best_val = val
                best_move = (start_sq, end_sq)
                
            alpha = max(alpha, best_val)
            
        return best_move

    def alpha_beta(self, bitboards, depth, alpha, beta, start_time, time_limit, is_maximizing):
        """
        Performs the alpha-beta minimax search.
        Mirrors the structure provided in the query.
        """
        
        # --- 1. Terminal Node Check (Base Case) ---
        
        # Check for timeout
        if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
            raise TimeoutException("Timeout")
            
        # Check for Game Over (Win/Loss/Draw)
        # We check based on the player whose turn it IS (is_maximizing determination)
        player_color = self.my_color if is_maximizing else self.opponent_color
        
        # Determine if the *previous* move ended the game
        # If is_maximizing=True, it's My turn. Did Opponent checkmate me?
        # If is_maximizing=False, it's Opponent's turn. Did I checkmate them?
        
        # Check checkmate/stalemate by generating moves
        # Note: get_possible_moves includes the 'is_in_check' filter, so if it returns empty,
        # it's either checkmate or stalemate.
        moves = self.get_ordered_moves(bitboards, player_color)
        
        if not moves:
            if is_in_check(bitboards, player_color):
                # Checkmate
                if is_maximizing:
                    return -math.inf # I am checkmated (Loss for Maximizer)
                else:
                    return math.inf  # Opponent is checkmated (Win for Maximizer)
            else:
                # Stalemate
                return 0

        # Check if maximum depth is reached
        if depth == 0:
            # Return the heuristic evaluation of the board
            # Pass alpha/beta into Quiescence for further pruning
            return self.quiescence_search(bitboards, alpha, beta, start_time, time_limit, is_maximizing)

        # --- 2. Recursive Step ---
        
        if is_maximizing:
            maxEval = -math.inf
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.my_color)
                sim_bitboards = apply_move_from_coords(bitboards, start_sq, end_sq, piece_name, self.my_color)
                
                score = self.alpha_beta(sim_bitboards, depth - 1, alpha, beta, start_time, time_limit, False)
                maxEval = max(maxEval, score)
                alpha = max(alpha, score)
                if beta <= alpha:
                    break # Beta Cut-off
            return maxEval
            
        else: # Minimizing player
            minEval = math.inf
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.opponent_color)
                sim_bitboards = apply_move_from_coords(bitboards, start_sq, end_sq, piece_name, self.opponent_color)
                
                score = self.alpha_beta(sim_bitboards, depth - 1, alpha, beta, start_time, time_limit, True)
                minEval = min(minEval, score)
                beta = min(beta, score)
                if beta <= alpha:
                    break # Alpha Cut-off
            return minEval

    def quiescence_search(self, bitboards, alpha, beta, start_time, time_limit, is_maximizing, q_depth=2):
        """
        Searches only capture moves to prevent the horizon effect.
        """
        # Check timeout
        if (time.perf_counter() - start_time) > (time_limit - TIMEOUT_BUFFER):
             return self.evaluate(bitboards)

        # Stand-pat (Evaluation of current state)
        # If we don't capture, this is the score.
        stand_pat = self.evaluate(bitboards)
        
        if is_maximizing:
            if stand_pat >= beta:
                return beta
            if stand_pat > alpha:
                alpha = stand_pat
        else:
            # In standard negamax Q-search, we often flip signs.
            # Here in Minimax, we handle min/max separately.
            # Minimizer wants low scores.
            if stand_pat <= alpha:
                return alpha
            if stand_pat < beta:
                beta = stand_pat

        if q_depth == 0:
            return stand_pat

        # Generate ONLY captures
        player_color = self.my_color if is_maximizing else self.opponent_color
        moves = self.get_ordered_moves(bitboards, player_color, captures_only=True)
        
        if is_maximizing:
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.my_color)
                sim_bitboards = apply_move_from_coords(bitboards, start_sq, end_sq, piece_name, self.my_color)
                
                score = self.quiescence_search(sim_bitboards, alpha, beta, start_time, time_limit, False, q_depth - 1)
                
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
            return alpha
        else:
            for start_sq, end_sq in moves:
                piece_name = self.get_piece_name_at(bitboards, start_sq, self.opponent_color)
                sim_bitboards = apply_move_from_coords(bitboards, start_sq, end_sq, piece_name, self.opponent_color)
                
                score = self.quiescence_search(sim_bitboards, alpha, beta, start_time, time_limit, True, q_depth - 1)
                
                if score <= alpha:
                    return alpha
                if score < beta:
                    beta = score
            return beta

    def get_ordered_moves(self, bitboards, color, captures_only=False):
        """
        Generates moves and sorts them to prioritize captures.
        """
        moves = get_possible_moves(bitboards, color)
        
        # Helper to check if a move is a capture
        opponent_color = "black" if color == "white" else "white"
        opp_occupied = bitboards[f"{opponent_color}_occupied"]
        
        capture_moves = []
        quiet_moves = []
        
        for start, end in moves:
            target_bit = 1 << end
            if (opp_occupied & target_bit):
                # MVV-LVA Heuristic (Most Valuable Victim - Least Valuable Aggressor)
                # could be added here. For now, just separating captures is a big win.
                capture_moves.append((start, end))
            else:
                if not captures_only:
                    quiet_moves.append((start, end))
        
        # Randomize quiets to avoid repetition in identical positions
        if not captures_only:
            random.shuffle(quiet_moves)
            
        return capture_moves + quiet_moves

    def evaluate(self, bitboards):
        """
        Material evaluation.
        """
        score = 0
        for piece_name in PIECE_NAMES:
            my_pieces = bitboards[f"{self.my_color}_{piece_name}s"]
            opp_pieces = bitboards[f"{self.opponent_color}_{piece_name}s"]
            
            score += bin(my_pieces).count('1') * PIECE_VALUES[piece_name]
            score -= bin(opp_pieces).count('1') * PIECE_VALUES[piece_name]
        return score

    def get_piece_name_at(self, bitboards, square_index, color):
        bit = 1 << square_index
        for name in PIECE_NAMES:
            if bitboards[f"{color}_{name}s"] & bit:
                return name
        return None
# Adapter function required by the framework
# The framework expects a function 'agent(board, player, var)'
# We'll wrap our class in this function.
_bot_instance = AlphaBetaAgent(depth=4)

def agent(board, player, var):
    # var is likely [ply, time_budget]
    return _bot_instance.get_move(board, player, var)


# piece = colour, royal, sliding, 
NOPIECE = 0
WPAWN = 9
WBISHOP = 10
WKNIGHT = 11
WRIGHT = 12
WQUEEN = 13
WKING = 14

BPAWN = 1
BBISHOP = 2
BKNIGHT = 3
BRIGHT = 4
BQUEEN = 5
BKING = 6

#  move = start | end | piece | type | 
#            5     5      5       
PIECE_NAMES = ["pawn", "right", "knight", "bishop", "queen", "king"]

PIECE_NAMES = ["pawn", "right", "knight", "bishop", "queen", "king"]

def initialize_bitboards():
    """
    Creates a dictionary to hold all 15 bitboards, initialized to 0.
    
    Includes:
    - 6 piece types * 2 colors = 12 bitboards
    - 1 occupancy board * 2 colors = 2 bitboards
    - 1 total occupancy board = 1 bitboard
    """
    bitboards = {}
    
    for color in ["white", "black"]:
        for piece_name in PIECE_NAMES:
            # e.g., 'white_pawns', 'black_kings'
            key = f"{color}_{piece_name}s" 
            bitboards[key] = 0
        
        # Add occupancy boards for all pieces of a single color
        bitboards[f"{color}_occupied"] = 0
        
    # Add a final occupancy board for all pieces
    bitboards["all_occupied"] = 0
    return bitboards

def board_to_bitboards(board):
    """
    Converts a chessmaker board object into a dictionary of bitboards.
    The 5x5 board (25 squares) is mapped to bits 0-24.
    """
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

def apply_move_to_bitboards(bitboards, piece, move_opt):
    """
    Applies a given move to a bitboard dictionary and returns a new dictionary.
    Handles standard moves, captures, En Passant, and Promotion.
    Note: 'piece' and 'move_opt' are objects from the original chessmaker board
    which we use here just for their metadata (color, name, type).
    If you only have coordinates, you'd need a different signature.
    """
    new_bitboards = {k: v for k, v in bitboards.items()}
    
    color = piece.player.name.lower()
    opponent_color = "black" if color == "white" else "white"
    piece_name = piece.name.lower()
    
    orig_x, orig_y = piece.position.x, piece.position.y
    dest_x, dest_y = move_opt.position.x, move_opt.position.y
    
    orig_bit_index = orig_y * 5 + orig_x
    dest_bit_index = dest_y * 5 + dest_x
    
    orig_bit_value = 1 << orig_bit_index
    dest_bit_value = 1 << dest_bit_index
    
    # 1. Clear origin
    new_bitboards[f"{color}_{piece_name}s"] &= ~orig_bit_value
    new_bitboards[f"{color}_occupied"] &= ~orig_bit_value
    new_bitboards["all_occupied"] &= ~orig_bit_value
    
    # 2. Standard Capture
    capture_processed = False
    if (bitboards[f"{opponent_color}_occupied"] & dest_bit_value):
        for opp_piece_name in PIECE_NAMES:
            key = f"{opponent_color}_{opp_piece_name}s"
            if (bitboards[key] & dest_bit_value):
                new_bitboards[key] &= ~dest_bit_value
                new_bitboards[f"{opponent_color}_occupied"] &= ~dest_bit_value
                capture_processed = True
                break
    
    # 3. En Passant Capture
    if piece_name == "pawn" and not capture_processed:
        dx = abs(dest_x - orig_x)
        dy = abs(dest_y - orig_y)
        
        if dx == 1 and dy == 1:
            capture_y = dest_y + 1 if color == "white" else dest_y - 1
            capture_bit_index = capture_y * 5 + dest_x
            capture_bit_value = 1 << capture_bit_index
            
            new_bitboards[f"{opponent_color}_pawns"] &= ~capture_bit_value
            new_bitboards[f"{opponent_color}_occupied"] &= ~capture_bit_value
            new_bitboards["all_occupied"] &= ~capture_bit_value

    # 4. Promotion
    is_promotion = False
    if piece_name == "pawn":
        if color == "white" and dest_y == 0:
            is_promotion = True
        elif color == "black" and dest_y == 4:
            is_promotion = True
            
    # 5. Place at destination
    if is_promotion:
        new_bitboards[f"{color}_queens"] |= dest_bit_value
    else:
        new_bitboards[f"{color}_{piece_name}s"] |= dest_bit_value
        
    new_bitboards[f"{color}_occupied"] |= dest_bit_value
    new_bitboards["all_occupied"] |= dest_bit_value
            
    return new_bitboards

def apply_move_from_coords(bitboards, start_sq, end_sq, piece_name, color):
    """
    Simplified version of apply_move_to_bitboards that takes raw coordinates
    instead of chessmaker objects. Used for simulating moves during search.
    """
    new_bitboards = {k: v for k, v in bitboards.items()}
    opponent_color = "black" if color == "white" else "white"
    
    start_bit = 1 << start_sq
    end_bit = 1 << end_sq
    
    start_x, start_y = start_sq % 5, start_sq // 5
    end_x, end_y = end_sq % 5, end_sq // 5
    
    # 1. Clear origin
    new_bitboards[f"{color}_{piece_name}s"] &= ~start_bit
    new_bitboards[f"{color}_occupied"] &= ~start_bit
    new_bitboards["all_occupied"] &= ~start_bit
    
    # 2. Standard Capture
    capture_processed = False
    if (bitboards[f"{opponent_color}_occupied"] & end_bit):
        for opp_piece_name in PIECE_NAMES:
            key = f"{opponent_color}_{opp_piece_name}s"
            if (bitboards[key] & end_bit):
                new_bitboards[key] &= ~end_bit
                new_bitboards[f"{opponent_color}_occupied"] &= ~end_bit
                capture_processed = True
                break
    
    # 3. En Passant
    if piece_name == "pawn" and not capture_processed:
        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)
        if dx == 1 and dy == 1:
            capture_y = end_y + 1 if color == "white" else end_y - 1
            capture_sq = capture_y * 5 + end_x
            capture_bit = 1 << capture_sq
            new_bitboards[f"{opponent_color}_pawns"] &= ~capture_bit
            new_bitboards[f"{opponent_color}_occupied"] &= ~capture_bit
            new_bitboards["all_occupied"] &= ~capture_bit
            
    # 4. Promotion
    is_promotion = False
    if piece_name == "pawn":
        if (color == "white" and end_y == 0) or (color == "black" and end_y == 4):
            is_promotion = True
            
    # 5. Place at destination
    if is_promotion:
        new_bitboards[f"{color}_queens"] |= end_bit
    else:
        new_bitboards[f"{color}_{piece_name}s"] |= end_bit
        
    new_bitboards[f"{color}_occupied"] |= end_bit
    new_bitboards["all_occupied"] |= end_bit
    
    return new_bitboards

def reverse_move_bitboards(bitboards, piece, move_opt, captured_piece_name=None):
    """Reverses a move on the bitboards."""
    prev_bitboards = {k: v for k, v in bitboards.items()}

    color = piece.player.name.lower()
    opponent_color = "black" if color == "white" else "white"
    piece_name = piece.name.lower()

    orig_x, orig_y = piece.position.x, piece.position.y
    dest_x, dest_y = move_opt.position.x, move_opt.position.y

    orig_bit_value = 1 << (orig_y * 5 + orig_x)
    dest_bit_value = 1 << (dest_y * 5 + dest_x)

    is_promotion = False
    if piece_name == "pawn":
        if (color == "white" and dest_y == 0) or (color == "black" and dest_y == 4):
            is_promotion = True

    if is_promotion:
        prev_bitboards[f"{color}_queens"] &= ~dest_bit_value
    else:
        prev_bitboards[f"{color}_{piece_name}s"] &= ~dest_bit_value

    prev_bitboards[f"{color}_occupied"] &= ~dest_bit_value
    prev_bitboards["all_occupied"] &= ~dest_bit_value

    prev_bitboards[f"{color}_{piece_name}s"] |= orig_bit_value
    prev_bitboards[f"{color}_occupied"] |= orig_bit_value
    prev_bitboards["all_occupied"] |= orig_bit_value

    if captured_piece_name:
        opp_key = f"{opponent_color}_{captured_piece_name}s"
        prev_bitboards[opp_key] |= dest_bit_value
        prev_bitboards[f"{opponent_color}_occupied"] |= dest_bit_value
        prev_bitboards["all_occupied"] |= dest_bit_value

    return prev_bitboards

def get_sliding_moves_bitmask(square_index, all_occupied, own_occupied, piece_name):
    """Generates moves for sliding pieces."""
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
    """Generates move (push + capture) bitmask for pawns."""
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
    """Generates moves for Knights and jumping aspect of Right pieces."""
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
    """Generates moves for King."""
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
    """Generates a bitmask of squares ATTACKED by a pawn."""
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
    """Calculates a single bitboard containing ALL squares attacked by the given color."""
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
    """Determines if the King of the specified 'color' is currently in check."""
    opponent_color = "black" if color == "white" else "white"
    attacked_mask = get_all_attacked_squares(bitboards, opponent_color)
    king_bitboard = bitboards[f"{color}_kings"]
    if (king_bitboard & attacked_mask):
        return True
    return False

def get_possible_moves(bitboards, color, en_passant_target_bit=0):
    """
    Generates ALL legal moves for a given color from the current position.
    
    Parameters
    ----------
    bitboards: dict representing current board state.
    color: str ('white' or 'black').
    en_passant_target_bit: int (optional bitmask for en passant target).

    Returns
    -------
    list of tuples: [(start_sq_index, end_sq_index), ...]
    """
    possible_moves = []
    
    all_occupied = bitboards["all_occupied"]
    own_occupied = bitboards[f"{color}_occupied"]
    opponent_occupied = bitboards[f"black_occupied"] if color == "white" else bitboards[f"white_occupied"]
    
    # 1. Iterate through all piece types
    for piece_name in PIECE_NAMES:
        piece_bits = bitboards[f"{color}_{piece_name}s"]
        
        # Iterate through every piece of this type
        for i in range(25):
            if (piece_bits >> i) & 1:
                start_sq = i
                moves_mask = 0
                
                # Generate pseudo-legal moves bitmask based on piece type
                if piece_name == "pawn":
                    moves_mask = get_pawn_moves_bitmask(start_sq, color, all_occupied, opponent_occupied, en_passant_target_bit)
                elif piece_name == "knight":
                    moves_mask = get_jumping_moves_bitmask(start_sq, own_occupied)
                elif piece_name == "bishop":
                    moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, "bishop")
                elif piece_name == "right":
                    # Right is Rook + Knight
                    moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, "right")
                    moves_mask |= get_jumping_moves_bitmask(start_sq, own_occupied)
                elif piece_name == "queen":
                    moves_mask = get_sliding_moves_bitmask(start_sq, all_occupied, own_occupied, "queen")
                elif piece_name == "king":
                    moves_mask = get_king_moves_bitmask(start_sq, own_occupied)
                
                # Convert bitmask to individual moves
                for target_sq in range(25):
                    if (moves_mask >> target_sq) & 1:
                        # 2. Filter for Legality (Does this move leave King in Check?)
                        # Simulate the move
                        next_state = apply_move_from_coords(bitboards, start_sq, target_sq, piece_name, color)
                        
                        # Check if our King is attacked in the new state
                        if not is_in_check(next_state, color):
                            possible_moves.append((start_sq, target_sq))
                            
    return possible_moves

def is_checkmate(bitboards, color, en_passant_target_bit=0):
    """
    Determines if the specified 'color' is in checkmate.
    
    Conditions for Checkmate:
    1. The King IS currently in check.
    2. There are NO legal moves available that can escape the check.
    
    Parameters
    ----------
    bitboards: dict representing current board state.
    color: str ('white' or 'black').
    en_passant_target_bit: int (optional bitmask for en passant target).

    Returns
    -------
    bool: True if in checkmate, False otherwise.
    """
    # 1. Verify King is in Check
    if not is_in_check(bitboards, color):
        return False
        
    # 2. Verify no legal moves exist
    # get_possible_moves handles the legality check (filtering moves that leave King in check)
    moves = get_possible_moves(bitboards, color, en_passant_target_bit)
    
    # If list is empty, no moves can save the King -> Checkmate
    if len(moves) == 0:
        return True
        
    return False

def print_bitboard(bitboard, board_size=5):
    """Helper to print bitboard."""
    print(f"--- (Int value: {bitboard}) ---")
    for y in range(board_size):
        row = []
        for x in range(board_size):
            bit_index = y * board_size + x
            if (bitboard >> bit_index) & 1:
                row.append("1")
            else:
                row.append(".")
        print(" ".join(row))
    print("-" * (board_size * 2 + 2))