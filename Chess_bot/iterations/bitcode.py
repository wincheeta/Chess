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