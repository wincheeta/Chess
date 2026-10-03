import random
import time
import math
import numpy as np
import concurrent.futures
import advanced_eval as engine
from advanced_eval import (
    PAWN, RIGHT, KNIGHT, BISHOP, QUEEN, KING,
    make_move, unmake_move, get_possible_moves,
    is_in_check, get_all_attacked_squares
)
# --- CONFIGURATION ---
engine.TIMEOUT_BUFFER = 0.0

# Search Config
SEARCH_DEPTH = 2        # Fixed depth for all games
SAFETY_TIME = 10.0      # Give engine 10s to finish Depth 2 (effectively infinite)

# Parallel Config
NUM_WORKERS = 3         
GAMES_PER_STEP = 12     

# Adam Hyperparameters
ALPHA = 0.05            
BETA_1 = 0.9            
BETA_2 = 0.999          
EPSILON = 1e-8          
PERTURBATION = 0.05     

# Training Config
ITERATIONS = 2000
OPENING_PLIES = 4       

# --- PARAMETER SCHEMA ---
PARAM_SCHEMA = []
PARAM_SCHEMA.append({"name": "Pawn",   "type": "PIECE", "idx": 0, "base": 100, "scale": 50})
PARAM_SCHEMA.append({"name": "Right",  "type": "PIECE", "idx": 1, "base": 950, "scale": 100})
PARAM_SCHEMA.append({"name": "Knight", "type": "PIECE", "idx": 2, "base": 320, "scale": 50})
PARAM_SCHEMA.append({"name": "Bishop", "type": "PIECE", "idx": 3, "base": 300, "scale": 50})
PARAM_SCHEMA.append({"name": "Queen",  "type": "PIECE", "idx": 4, "base": 900, "scale": 100})
try:
    PARAM_SCHEMA.append({"name": "PassedPawn", "type": "VAR", "ref": "PASSED_PAWN_BONUS", "base": 50, "scale": 50})
    PARAM_SCHEMA.append({"name": "Mobility",   "type": "VAR", "ref": "MOBILITY_WEIGHT",   "base": 5,  "scale": 10})
    PARAM_SCHEMA.append({"name": "Tempo",      "type": "VAR", "ref": "TEMPO_BONUS",       "base": 10, "scale": 20})
except AttributeError: pass

for t_idx, table in enumerate(engine.TABLES_WHITE):
    for s_idx in range(25):
        PARAM_SCHEMA.append({
            "name": f"PST_{t_idx}_{s_idx}", "type": "PST", 
            "table_idx": t_idx, "sq_idx": s_idx, "base": table[s_idx], "scale": 20 
        })

TOTAL_PARAMS = len(PARAM_SCHEMA)
print(TOTAL_PARAMS)
# --- WORKER FUNCTIONS ---

def set_engine_parameters(theta_vector):
    """Decodes theta vector into engine constants."""
    for i, p_def in enumerate(PARAM_SCHEMA):
        raw_val = p_def["base"] + (theta_vector[i] * p_def["scale"])
        int_val = int(round(raw_val))
        
        if p_def["type"] == "PIECE":
            engine.PIECE_VALUES[p_def["idx"]] = max(10, int_val)
        elif p_def["type"] == "VAR":
            try: setattr(engine, p_def["ref"], int_val)
            except AttributeError: pass
        elif p_def["type"] == "PST":
            engine.TABLES_WHITE[p_def["table_idx"]][p_def["sq_idx"]] = int_val

    engine.TABLES_BLACK = [engine.mirror_pst(t) for t in engine.TABLES_WHITE]

def get_start_board():
    bb = [0] * 15
    def place(p, c, x, y):
        sq = y * 5 + x
        bit = 1 << sq
        bb[c*7 + p] |= bit
        bb[c*7 + 6] |= bit
        bb[14] |= bit
        
    layout = [RIGHT, KNIGHT, BISHOP, QUEEN, KING]
    for i, piece in enumerate(layout):
        place(piece, 0, i, 4); place(PAWN, 0, i, 3)
        place(piece, 1, i, 0); place(PAWN, 1, i, 1)
    return bb

def get_random_opening_board(plies):
    """Generates a board state with N random moves applied."""
    bb = get_start_board()
    turn = 0
    for _ in range(plies):
        legal = get_possible_moves(bb, turn, 0)
        if not legal: break
        move = random.choice(legal)
        start, end = move
        p_idx = None
        base = turn * 7; bit = 1 << start
        for i in range(6): 
            if bb[base+i] & bit: p_idx = i; break
        if p_idx is not None:
            make_move(bb, start, end, p_idx, turn, 0)
            turn = 1 - turn
    return bb, turn

def play_game_from_position(bot, start_bb, start_turn, theta_white, theta_black):
    """
    Plays a game using FIXED DEPTH (Depth 2).
    """
    # 1. Reset Bot State
    bot.tt.clear()
    
    bb = list(start_bb) 
    turn = start_turn
    moves_played = 0
    history = []
    
    while moves_played < 100:
        # Load Parameters
        if turn == 0: set_engine_parameters(theta_white)
        else:         set_engine_parameters(theta_black)
        
        bot.my_color_idx = turn
        bot.game_history = history[:] 
        
        current_hash = bot.compute_full_hash(bb, 0)
        if current_hash in history: return 0.5
        history.append(current_hash)
        
        # --- FIXED DEPTH SEARCH ---
        try:
            # We give a massive time buffer (SAFETY_TIME) to ensure Depth 2 always completes.
            move, score = bot.find_best_move(bb, SEARCH_DEPTH, time.perf_counter(), SAFETY_TIME, 0, current_hash)
        except engine.TimeoutException:
            # Panic fallback if computer is extremely overloaded
            try: move, score = bot.find_best_move(bb, 1, time.perf_counter(), SAFETY_TIME, 0, current_hash)
            except: move = None

        if move is None:
            if is_in_check(bb, turn): return 0.0 if turn == 0 else 1.0
            return 0.0 # Stalemate
            
        start, end = move
        p_idx = bot.get_piece_index_at(bb, start, turn)
        make_move(bb, start, end, p_idx, turn, 0)
        moves_played += 1
        turn = 1 - turn

    # Reward Shaping
    set_engine_parameters(theta_white)
    final_eval = bot.evaluate(bb, 0)
    shaping = math.tanh(final_eval / 1000.0) * 0.1
    return 0.5 + shaping

def evaluate_batch(theta_a, theta_b, num_games):
    """Runs a batch of games on a single core."""
    random.seed(time.time_ns())
    bot = engine.AlphaBetaAgent(depth=SEARCH_DEPTH)
    
    score_diff_sum = 0.0
    pairs = num_games // 2
    
    for _ in range(pairs):
        start_bb, start_turn = get_random_opening_board(OPENING_PLIES)
        
        # Game 1: A is White
        score_a = play_game_from_position(bot, start_bb, start_turn, theta_a, theta_b)
        score_b = 1.0 - score_a
        score_diff_sum += (score_a - score_b)
        
        # Game 2: B is White (Swap colors, Same Opening)
        score_b_rev = play_game_from_position(bot, start_bb, start_turn, theta_b, theta_a)
        score_a_rev = 1.0 - score_b_rev
        score_diff_sum += (score_a_rev - score_b_rev)
        
    return score_diff_sum

# --- MAIN CONTROLLER ---

def run_parallel_adam():
    theta = np.zeros(TOTAL_PARAMS)
    m = np.zeros(TOTAL_PARAMS)
    v = np.zeros(TOTAL_PARAMS)
    
    print(f"Parallel Adam-SPSA: {NUM_WORKERS} Workers | {GAMES_PER_STEP} Games/Step")
    print(f"Mode: FIXED DEPTH ({SEARCH_DEPTH})")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        
        for t in range(1, ITERATIONS + 1):
            delta = np.random.choice([-1, 1], size=TOTAL_PARAMS)
            ck = PERTURBATION
            
            theta_plus = theta + (ck * delta)
            theta_minus = theta - (ck * delta)
            
            # Distribute work
            games_per_worker = GAMES_PER_STEP // NUM_WORKERS
            if games_per_worker % 2 != 0: games_per_worker += 1
            
            futures = []
            for _ in range(NUM_WORKERS):
                futures.append(
                    executor.submit(evaluate_batch, theta_plus, theta_minus, games_per_worker)
                )
            
            total_diff = 0.0
            total_games = 0
            
            for f in concurrent.futures.as_completed(futures):
                diff_sum = f.result()
                total_diff += diff_sum
                total_games += games_per_worker
                
            avg_diff = total_diff / total_games
            
            # Adam Update
            gradient = (avg_diff / (2 * ck)) * delta
            m = BETA_1 * m + (1 - BETA_1) * gradient
            v = BETA_2 * v + (1 - BETA_2) * (gradient ** 2)
            
            m_hat = m / (1 - BETA_1 ** t)
            v_hat = v / (1 - BETA_2 ** t)
            
            update = ALPHA * m_hat / (np.sqrt(v_hat) + EPSILON)
            theta += update
            
            # Logging
            if t % 1 == 0:
                raw_right = PARAM_SCHEMA[1]["base"] + (theta[1] * PARAM_SCHEMA[1]["scale"])
                raw_pawn = PARAM_SCHEMA[5]["base"] + (theta[5] * PARAM_SCHEMA[5]["scale"])
                print(f"Iter {t}: Grad {avg_diff:.3f} | Right: {int(raw_right)} | PassPawn: {int(raw_pawn)}")

            if t % 20 == 0:
                with open("parallel_params.txt", "w") as f:
                    np.savetxt(f, theta)
                print("--- Checkpoint Saved ---")

if __name__ == "__main__":
    run_parallel_adam()