import random
import math
import copy
import time
import advanced_eval as engine
from advanced_eval import (
    PAWN, RIGHT, KNIGHT, BISHOP, QUEEN, KING,
    make_move, unmake_move, get_possible_moves,
    is_in_check, get_all_attacked_squares
)
import numpy as np

# --- CONFIGURATION ---
engine.TIMEOUT_BUFFER = 0.0

# Adam Hyperparameters (Industry Standard)
ALPHA = 0.05            # Learning Rate (Stepsize)
BETA_1 = 0.9            # Momentum factor
BETA_2 = 0.999          # Velocity factor
EPSILON = 1e-8          # Numerical stability
PERTURBATION = 0.05     # Standard deviation of noise for SPSA exploration

# Training Config
ITERATIONS = 2000
GAMES_PER_STEP = 8      # Higher sample size for stable gradients
OPENING_PLIES = 4       # Random start moves

# --- PARAMETER SCHEMA (NORMALIZATION) ---
# We define a Base Value and a Scale for every parameter.
# The optimizer sees a number between -1.0 and 1.0.
# The engine sees: Base + (Optimizer_Value * Scale)
# This solves the "Queen vs Pawn" scale problem.

# Format: (Name, Index/Reference, Base, Scale)
PARAM_SCHEMA = []

# 1. Piece Values (Skip King)
# We treat the hardcoded initial constants as the "Base"
# Scale=50 means the optimizer can swing the value by +/- 50 easily.
PARAM_SCHEMA.append({"name": "Pawn",   "type": "PIECE", "idx": 0, "base": 100, "scale": 50})
PARAM_SCHEMA.append({"name": "Right",  "type": "PIECE", "idx": 1, "base": 950, "scale": 100})
PARAM_SCHEMA.append({"name": "Knight", "type": "PIECE", "idx": 2, "base": 320, "scale": 50})
PARAM_SCHEMA.append({"name": "Bishop", "type": "PIECE", "idx": 3, "base": 300, "scale": 50})
PARAM_SCHEMA.append({"name": "Queen",  "type": "PIECE", "idx": 4, "base": 900, "scale": 100})

# 2. Heuristics (Must be added to bit_v5_1 global scope manually first)
PARAM_SCHEMA.append({"name": "PassedPawn", "type": "VAR", "ref": "PASSED_PAWN_BONUS", "base": 50, "scale": 50})
PARAM_SCHEMA.append({"name": "Mobility",   "type": "VAR", "ref": "MOBILITY_WEIGHT",   "base": 5,  "scale": 10})
PARAM_SCHEMA.append({"name": "Tempo",      "type": "VAR", "ref": "TEMPO_BONUS",       "base": 10, "scale": 20})

# 3. PST Tables
# Flatten the white tables. Scale=10 allows fine-tuning.
pst_count = 0
for t_idx, table in enumerate(engine.TABLES_WHITE):
    for s_idx in range(25):
        PARAM_SCHEMA.append({
            "name": f"PST_{t_idx}_{s_idx}", 
            "type": "PST", 
            "table_idx": t_idx, 
            "sq_idx": s_idx, 
            "base": table[s_idx], 
            "scale": 20 
        })
        pst_count += 1

TOTAL_PARAMS = len(PARAM_SCHEMA)

# --- HELPER FUNCTIONS ---

def set_engine_parameters(theta_vector):
    """
    Decodes the normalized theta vector (-1 to 1) into actual game integers.
    """
    # 1. Update Piece Values
    for i, p_def in enumerate(PARAM_SCHEMA):
        # Calculate raw value: Base + (Normalized * Scale)
        raw_val = p_def["base"] + (theta_vector[i] * p_def["scale"])
        int_val = int(round(raw_val))
        
        if p_def["type"] == "PIECE":
            # Safety Clamp: Pieces shouldn't be negative or zero
            engine.PIECE_VALUES[p_def["idx"]] = max(10, int_val)
            
        elif p_def["type"] == "VAR":
            # Update global variable dynamically
            try:
                setattr(engine, p_def["ref"], int_val)
            except AttributeError:
                pass # Variable might not exist in older engine versions
                
        elif p_def["type"] == "PST":
            # Update the specific square in the specific table
            t_idx = p_def["table_idx"]
            s_idx = p_def["sq_idx"]
            engine.TABLES_WHITE[t_idx][s_idx] = int_val

    # 2. Re-mirror Black Tables (Crucial Step)
    # We recreate the black tables list entirely to ensure references update
    engine.TABLES_BLACK = [engine.mirror_pst(t) for t in engine.TABLES_WHITE]

def get_start_board():
    """Standard 5x5 Start Board."""
    bb = [0] * 15
    def place(p, c, x, y):
        sq = y * 5 + x
        bit = 1 << sq
        bb[c*7 + p] |= bit
        bb[c*7 + 6] |= bit
        bb[14] |= bit
        
    layout = [RIGHT, KNIGHT, BISHOP, QUEEN, KING]
    for i, piece in enumerate(layout):
        place(piece, 0, i, 4) # White
        place(PAWN, 0, i, 3)
        place(piece, 1, i, 0) # Black
        place(PAWN, 1, i, 1)
    return bb

# --- GAME ENGINE ---

def play_match(theta_a, theta_b):
    """
    Plays a match between Normalized Vector A and Normalized Vector B.
    Returns: Score for A (1.0=Win, 0.0=Loss) + Reward Shaping
    """
    bot = engine.AlphaBetaAgent(depth=2)
    bb = get_start_board()
    turn = 0
    moves_played = 0
    history = []
    
    # 1. Randomized Opening (Prevent Deterministic Traps)
    for _ in range(OPENING_PLIES):
        legal = get_possible_moves(bb, turn, 0)
        if not legal: break
        move = random.choice(legal)
        # Apply move manually
        start, end = move
        base = turn * 7
        bit = 1 << start
        p_idx = None
        for i in range(6):
            if bb[base+i] & bit: p_idx = i; break
        if p_idx is not None:
            make_move(bb, start, end, p_idx, turn, 0)
            turn = 1 - turn
            moves_played += 1

    # 2. The Match
    while moves_played < 100:
        # Load Parameters for the specific side
        if turn == 0: set_engine_parameters(theta_a)
        else:         set_engine_parameters(theta_b)
        
        bot.my_color_idx = turn
        bot.game_history = history[:]
        current_hash = bot.compute_full_hash(bb, 0)
        
        if current_hash in history:
            return 0.5 # Draw
        history.append(current_hash)
        
        try:
            move, score = bot.find_best_move(bb, 2, time.perf_counter(), 1.0, 0, current_hash)
        except engine.TimeoutException:
            # Fallback
            try: move, score = bot.find_best_move(bb, 1, time.perf_counter(), 1.0, 0, current_hash)
            except: move = None

        if move is None:
            # Checkmate logic
            if is_in_check(bb, turn):
                return 0.0 if turn == 0 else 1.0
            return 0.0 # Stalemate logic (Stalemate = Loss)
            
        start, end = move
        p_idx = bot.get_piece_index_at(bb, start, turn)
        make_move(bb, start, end, p_idx, turn, 0)
        
        moves_played += 1
        turn = 1 - turn

    # 3. Reward Shaping (Sparse Reward Fix)
    # If game ended in draw/timeout, judge by material
    # We load Theta A to evaluate the board from White's perspective
    set_engine_parameters(theta_a)
    final_eval = bot.evaluate(bb, 0)
    
    # Sigmoid squash the eval to [-0.1, 0.1] to add texture to the draw result
    # This encourages the bot to gain material even if it can't find mate yet
    shaping = math.tanh(final_eval / 1000.0) * 0.1
    
    return 0.5 + shaping

# --- ADAM OPTIMIZER LOOP ---

def run_adam_spsa():
    # Initialize Theta at 0.0 (Which represents the Base values)
    theta = np.zeros(TOTAL_PARAMS)
    
    # Adam Moments
    m = np.zeros(TOTAL_PARAMS)
    v = np.zeros(TOTAL_PARAMS)
    
    print(f"Adam-SPSA: Optimizing {TOTAL_PARAMS} parameters.")
    print(f"Schema: {TOTAL_PARAMS} params mapped to engine constants.")
    
    for t in range(1, ITERATIONS + 1):
        # 1. Generate Perturbation Vector (Bernoulli +/- 1)
        delta = np.random.choice([-1, 1], size=TOTAL_PARAMS)
        
        # 2. Create Candidate Vectors (Normalized Space)
        # ck is constant in Adam-SPSA usually, or decays very slowly
        ck = PERTURBATION 
        
        theta_plus = theta + (ck * delta)
        theta_minus = theta - (ck * delta)
        
        # 3. Evaluate Gradient
        # We assume theta_plus is Player A (White) vs theta_minus (Black)
        # And flip colors to remove First-Move Advantage noise
        
        score_plus = 0.0
        score_minus = 0.0
        
        pairs = GAMES_PER_STEP // 2
        for _ in range(pairs):
            # Game 1: Plus is White
            res = play_match(theta_plus, theta_minus)
            score_plus += res
            
            # Game 2: Plus is Black (so Minus is White)
            # We invert the result because play_match returns score for First Arg
            res = play_match(theta_minus, theta_plus)
            score_minus += (1.0 - res) # If Minus won (1.0), Plus gets 0.0
            
        avg_diff = (score_plus - score_minus) / GAMES_PER_STEP
        
        # 4. SPSA Gradient Approximation
        # g = (y+ - y-) / (2 * ck * delta)
        # Since delta is +/- 1, dividing by delta is same as multiplying by delta
        gradient = (avg_diff / (2 * ck)) * delta
        
        # 5. Adam Update Rule
        m = BETA_1 * m + (1 - BETA_1) * gradient
        v = BETA_2 * v + (1 - BETA_2) * (gradient ** 2)
        
        m_hat = m / (1 - BETA_1 ** t)
        v_hat = v / (1 - BETA_2 ** t)
        
        update = ALPHA * m_hat / (np.sqrt(v_hat) + EPSILON)
        theta += update
        
        # 6. Logging
        if t % 1 == 0:
            # Decode a few values to see what's happening
            # Index 1 is 'Right' Piece Value
            # Index 5 is 'Passed Pawn' Bonus
            raw_right = PARAM_SCHEMA[1]["base"] + (theta[1] * PARAM_SCHEMA[1]["scale"])
            raw_pawn = PARAM_SCHEMA[5]["base"] + (theta[5] * PARAM_SCHEMA[5]["scale"])
            
            print(f"Iter {t}: GradEst {avg_diff:.3f} | Right: {int(raw_right)} | PassPawn: {int(raw_pawn)}")

        if t % 20 == 0:
             # Save Checkpoint
            with open("adam_params.txt", "w") as f:
                # We save the THETA vector, not the raw params, so we can resume
                np.savetxt(f, theta)
            print("--- Saved Checkpoint ---")

if __name__ == "__main__":
    run_adam_spsa()