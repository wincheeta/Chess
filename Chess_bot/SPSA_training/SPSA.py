import random
import math
import time
import copy
from bitEval import AlphaBetaAgent, PIECE_VALUES, PIECE_NAMES, PST_MAP, is_in_check, make_move, initialize_bitboards, TimeoutException
import numpy as np
# ==========================================
# 1. THE AGENT
# ==========================================

class Player:
    def __init__(self, col):
        self.name = col

class TunableAgent(AlphaBetaAgent):
    """
    A version of the bot that:
    1. Uses dynamic Piece Values for tuning.
    2. Overrides get_move to accept raw bitboards directly.
    """
    def __init__(self, depth=2, piece_values=None):
        super().__init__(depth)
        self.piece_values = piece_values if piece_values else PIECE_VALUES.copy()

    def evaluate(self, bitboards):
        score = 0
        for piece_name in PIECE_NAMES:
            # My pieces
            my_pieces = bitboards[f"{self.my_color}_{piece_name}s"]
            pst = PST_MAP[f"{self.my_color}_pawn"] if piece_name == "pawn" else PST_MAP[piece_name]
            while my_pieces:
                lsb = my_pieces & -my_pieces
                my_pieces ^= lsb
                idx = lsb.bit_length() - 1
                score += self.piece_values[piece_name] + pst[idx]

            # Opponent pieces
            opp_pieces = bitboards[f"{self.opponent_color}_{piece_name}s"]
            pst = PST_MAP[f"{self.opponent_color}_pawn"] if piece_name == "pawn" else PST_MAP[piece_name]
            while opp_pieces:
                lsb = opp_pieces & -opp_pieces
                opp_pieces ^= lsb
                idx = lsb.bit_length() - 1
                score -= (self.piece_values[piece_name] + pst[idx])

        if is_in_check(bitboards, self.my_color): score -= 50
        if is_in_check(bitboards, self.opponent_color): score += 50
        return score

    def get_move(self, bitboards, player, time_budget_info):
        """
        Overridden to handle raw bitboards and perform Iterative Deepening.
        """
        self.my_color = player.name.lower()
        self.opponent_color = "black" if self.my_color == "white" else "white"
        
        start_time = time.perf_counter()
        # Use a small fixed time limit for SPSA speed (e.g., 0.1s or 0.5s)
        # or rely on the depth limit if time_budget is large.
        time_limit = time_budget_info[1] 
        
        # We assume 'bitboards' is already the dictionary, not a Board object
        root_ep_target = 0 # Simplified for tuning
        
        best_move_so_far = None
        
        try:
            # Iterative Deepening Loop
            for current_depth in range(1, self.max_depth + 1):
                self.node_count = 0
                
                found_move, score = self.find_best_move(
                    bitboards, 
                    current_depth, 
                    start_time, 
                    time_limit,
                    root_ep_target,
                    pv_move=best_move_so_far
                )
                
                if found_move:
                    best_move_so_far = found_move
                
                # Time Check
                if (time.perf_counter() - start_time) > (time_limit * 0.5):
                    break
                    
        except TimeoutException:
            pass # Return best move found so far
        
        return best_move_so_far

# ==========================================
# 2. THE ARENA
# ==========================================
class BitboardGame:
    def __init__(self):
        self.bitboards = initialize_bitboards()
        # 5x5 Gardner Setup
        # Black
        self.bitboards["black_pawns"] = 0b00000_00000_00000_11111_00000
        self.bitboards["black_rights"] = (1 << 0)
        self.bitboards["black_knights"] = (1 << 1)
        self.bitboards["black_bishops"] = (1 << 2)
        self.bitboards["black_queens"] = (1 << 3)
        self.bitboards["black_kings"] = (1 << 4)
        # White
        self.bitboards["white_pawns"] = 0b00000_11111_00000_00000_00000
        self.bitboards["white_rights"] = (1 << 20)
        self.bitboards["white_knights"] = (1 << 21)
        self.bitboards["white_bishops"] = (1 << 22)
        self.bitboards["white_queens"] = (1 << 23)
        self.bitboards["white_kings"] = (1 << 24)
        
        self.update_occupied()

    def update_occupied(self):
        w, b = 0, 0
        for p in PIECE_NAMES:
            w |= self.bitboards[f"white_{p}s"]
            b |= self.bitboards[f"black_{p}s"]
        self.bitboards["white_occupied"] = w
        self.bitboards["black_occupied"] = b
        self.bitboards["all_occupied"] = w | b

    def play_match(self, agent_white, agent_black, max_moves=40):
        turn = "white"
        ep_target = 0
        
        for _ in range(max_moves * 2):
            current_agent = agent_white if turn == "white" else agent_black
            
            # 1. Use get_move (Clean!)
            # We pass [0, 0.5] as time budget: [start_time_unused, duration]
            # Passing Player(turn) ensures the agent knows its color
            move = current_agent.get_move(self.bitboards, Player(turn), [0, 1])
            
            # 2. Check Result
            if move is None:
                if is_in_check(self.bitboards, turn):
                    return -1 if turn == "white" else 1 # Checkmate
                return 0 # Stalemate

            # 3. Execute Move
            start, end = move
            piece = current_agent.get_piece_name_at(self.bitboards, start, turn)
            
            new_ep = 0
            if piece == "pawn" and abs(start - end) == 10:
                new_ep = 1 << ((start + end) // 2)
            
            make_move(self.bitboards, start, end, piece, turn, ep_target)
            ep_target = new_ep
            
            opp_color = "black" if turn == "white" else "white"
            if self.bitboards[f"{opp_color}_kings"] == 0:
                 return 1 if turn == "white" else -1
            
            turn = opp_color
            
        return 0 # Draw

# ==========================================
# 3. SPSA OPTIMIZER
# ==========================================

def run_spsa():
    param_keys = ["pawn", "knight", "bishop", "right", "queen"]
    theta = [100, 320, 310, 950, 900] # Start with decent guesses
    
    alpha = 0.602
    gamma = 0.101
    a = 20.0
    c = 15.0
    A = 10.0
    iterations = 5000 
    
    print(f"Starting SPSA on parameters: {param_keys}")
    print(f"Initial Values: {theta}")

    for k in range(1, iterations + 1):
        ak = a / ((k + A) ** alpha)
        ck = c / (k ** gamma)

        delta = [random.choice([-1, 1]) for _ in range(len(theta))]
        
        theta_plus_vals = [t + ck * d for t, d in zip(theta, delta)]
        theta_minus_vals = [t - ck * d for t, d in zip(theta, delta)]
        
        config_plus = PIECE_VALUES.copy()
        config_minus = PIECE_VALUES.copy()
        for i, key in enumerate(param_keys):
            config_plus[key] = int(theta_plus_vals[i])
            config_minus[key] = int(theta_minus_vals[i])

        # Play 2 games (mirrored colors) to reduce noise
        # Game 1: P vs M
        bot_p = TunableAgent(depth=2, piece_values=config_plus)
        bot_m = TunableAgent(depth=2, piece_values=config_minus)
        
        result1 = BitboardGame().play_match(bot_p, bot_m)
        result2 = BitboardGame().play_match(bot_m, bot_p)
        
        # If P wins G1 (+1) and M wins G2 (+1 for M => -1 for result), Net = +1 - (-1) = +2
        # We want P - M
        # result1 is P's score (1, 0, -1)
        # result2 is M's score (1, 0, -1) ... Wait, play_match returns 1 if White wins.
        # In Game 2, M is White. So result2=1 means M won.
        # So score_plus = result1 - result2
        
        score_plus = result1 - result2 
        
        y = -score_plus 

        ghat = []
        for d in delta:
            grad = y / (2 * ck * d) 
            ghat.append(grad)

        new_theta = []
        for i, t in enumerate(theta):
            new_val = t - ak * ghat[i]
            new_theta.append(new_val)
        
        theta = new_theta
        
        if k % 10 == 0:
            print(f"Iter {k}: Result={score_plus}. Params: {[int(x) for x in theta]}")

    print("Final Tuned Values:")
    for i, key in enumerate(param_keys):
        print(f"  {key}: {int(theta[i])}")

    
# [103, 312, 336, 398, 900]
# [103, 312, 337, 400, 899]

def get_paramaters():
    PIECE_VALUES = [100, 950, 320, 300, 900, 20000]

    # --- PIECE SQUARE TABLES ---

    # Helper to flip tables for Black
    def mirror_pst(pst):
        return pst[::-1]

    # 1. THE RIGHT (Knook) - Controls the board
    PST_RIGHT_WHITE = [
        5,  10,  10,  10,  5,
        10, 30,  35,  30, 10,
        10, 35,  60,  35, 10,
        10, 30,  35,  30, 10,
        5,  10,  15,  10,  5
    ]
    PST_RIGHT_BLACK = mirror_pst(PST_RIGHT_WHITE)

    # 2. THE QUEEN
    PST_QUEEN_WHITE = [
        5,  10,  10,  10,  5,
        10, 20,  25,  20, 10,
        10, 25,  40,  25, 10,
        10, 20,  25,  20, 10,
        5,  10,  10,  10,  5
    ]
    PST_QUEEN_BLACK = mirror_pst(PST_QUEEN_WHITE)

    # 3. KING SAFETY (Danger Phase) - Hide in pockets
    PST_KING_SAFETY_WHITE = [
        -50, -50, -50, -50, -50,
        -30, -30, -30, -30, -30,
        -30, -20, -20, -20, -30,
        -20,   0,   0,   0, -20,
        -40,  20,  30,  20, -40
    ]
    PST_KING_SAFETY_BLACK = mirror_pst(PST_KING_SAFETY_WHITE)

    # 4. KING ACTIVITY (Safe Phase) - Fight in center
    PST_KING_ACTIVE_WHITE = [
        -10,  10,  20,  10, -10,
        10,  20,  30,  20,  10,
        20,  30,  40,  30,  20,
        10,  20,  30,  20,  10,
        -10,  10,  20,  10, -10
    ]
    PST_KING_ACTIVE_BLACK = mirror_pst(PST_KING_ACTIVE_WHITE)

    # 5. PAWNS - Sprint to promotion
    PST_PAWN_WHITE = [
        0,   0,   0,   0,   0,
        60,  60,  60,  60,  60,
        30,  30,  35,  30,  30,
        10,  10,  15,  10,  10,
        0,   0,   0,   0,   0
    ]
    PST_PAWN_BLACK = mirror_pst(PST_PAWN_WHITE)

    # 6. MINOR PIECES (Knight/Bishop)
    PST_MINOR_WHITE = [
        -10, -5, -5, -5, -10,
        -5,   5, 10,  5, -5,
        -5,  10, 20, 10, -5,
        -5,   5, 10,  5, -5,
        -10, -5, -5, -5, -10
    ]
    PST_MINOR_BLACK = PST_MINOR_WHITE

    # PST Lookup Tables
    # Index: 0=P, 1=Right, 2=Knight, 3=Bishop, 4=Queen, 5=King
    TABLES_WHITE = [PST_PAWN_WHITE, PST_RIGHT_WHITE, PST_MINOR_WHITE, PST_MINOR_WHITE, PST_QUEEN_WHITE, PST_KING_SAFETY_WHITE, PST_KING_ACTIVE_WHITE]
    TABLES_BLACK = [PST_PAWN_BLACK, PST_RIGHT_BLACK, PST_MINOR_BLACK, PST_MINOR_BLACK, PST_QUEEN_BLACK, PST_KING_SAFETY_BLACK, PST_KING_ACTIVE_BLACK]

    # --- OPTIMIZED PRECOMPUTED MASKS ---

    MOBILITY_BONUS = [
        1,  3,  3,  3,  1,
        3,  7,  8,  7,  3,
        3,  8, 10,  8,  3,
        3,  7,  8,  7,  3,
        1,  3,  3,  3,  1
    ]

    return [PIECE_VALUES, TABLES_WHITE, TABLES_BLACK, MOBILITY_BONUS]


if __name__ == "__main__":
    print(get_paramaters())
    # run_spsa()
