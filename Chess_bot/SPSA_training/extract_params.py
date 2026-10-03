import numpy as np

# --- 1. DEFINE BASES (Must match Training Script exactly) ---

# Base Piece Values
BASE_PIECES = [100, 950, 320, 300, 900] # P, R, N, B, Q
PIECE_NAMES = ["PAWN", "RIGHT", "KNIGHT", "BISHOP", "QUEEN"]

# Base Heuristics
BASE_PASSED_PAWN = 50
BASE_MOBILITY = 5
BASE_TEMPO = 10

# Base PSTs (The "White" tables from bit_v5_1.py)
# We need these to calculate: Final = Base + (Theta * Scale)
def mirror_pst(pst): return pst[::-1]

PST_RIGHT_WHITE = [
    5,  10,  10,  10,  5,
    10, 30,  35,  30, 10,
    10, 35,  60,  35, 10,
    10, 30,  35,  30, 10,
    5,  10,  15,  10,  5
]
PST_QUEEN_WHITE = [
    5,  10,  10,  10,  5,
    10, 20,  25,  20, 10,
    10, 25,  40,  25, 10,
    10, 20,  25,  20, 10,
    5,  10,  10,  10,  5
]
PST_KING_SAFETY_WHITE = [
    -50, -50, -50, -50, -50,
    -30, -30, -30, -30, -30,
    -30, -20, -20, -20, -30,
    -20,   0,   0,   0, -20,
    -40,  20,  30,  20, -40
]
PST_KING_ACTIVE_WHITE = [ # Not tuned in schema loop, usually?
    # Wait, the training loop iterated over TABLES_WHITE.
    # We must match that list structure exactly.
    # TABLES_WHITE = [PST_PAWN, PST_RIGHT, PST_MINOR, PST_MINOR, PST_QUEEN, PST_KING_SAFETY]
    # Note: PST_KING_ACTIVE was NOT in TABLES_WHITE in the training script provided.
    # It only included: [PST_PAWN_WHITE, PST_RIGHT_WHITE, PST_MINOR_WHITE, PST_MINOR_WHITE, PST_QUEEN_WHITE, PST_KING_SAFETY_WHITE]
    # So King Active is NOT tuned.
    -10,  10,  20,  10, -10,
    10,  20,  30,  20,  10,
    20,  30,  40,  30,  20,
    10,  20,  30,  20,  10,
    -10,  10,  20,  10, -10
]
PST_PAWN_WHITE = [
    0,   0,   0,   0,   0,
    60,  60,  60,  60,  60,
    30,  30,  35,  30,  30,
    10,  10,  15,  10,  10,
    0,   0,   0,   0,   0
]
PST_MINOR_WHITE = [
    -10, -5, -5, -5, -10,
    -5,   5, 10,  5, -5,
    -5,  10, 20, 10, -5,
    -5,   5, 10,  5, -5,
    -10, -5, -5, -5, -10
]

# The list order used in training
BASE_TABLES = [
    ("PST_PAWN_WHITE", PST_PAWN_WHITE),
    ("PST_RIGHT_WHITE", PST_RIGHT_WHITE),
    ("PST_KNIGHT_WHITE", PST_MINOR_WHITE),
    ("PST_BISHOP_WHITE", PST_MINOR_WHITE), # Note: Knight and Bishop shared a base, but evolved separately
    ("PST_QUEEN_WHITE", PST_QUEEN_WHITE),
    ("PST_KING_SAFETY_WHITE", PST_KING_SAFETY_WHITE)
]

# --- 2. RECONSTRUCT SCHEMA ---
PARAM_SCHEMA = []
# Pieces
PARAM_SCHEMA.append({"name": "Pawn",   "type": "PIECE", "idx": 0, "base": 100, "scale": 50})
PARAM_SCHEMA.append({"name": "Right",  "type": "PIECE", "idx": 1, "base": 950, "scale": 100})
PARAM_SCHEMA.append({"name": "Knight", "type": "PIECE", "idx": 2, "base": 320, "scale": 50})
PARAM_SCHEMA.append({"name": "Bishop", "type": "PIECE", "idx": 3, "base": 300, "scale": 50})
PARAM_SCHEMA.append({"name": "Queen",  "type": "PIECE", "idx": 4, "base": 900, "scale": 100})
# Vars
PARAM_SCHEMA.append({"name": "PassedPawn", "type": "VAR", "base": 50, "scale": 50})
PARAM_SCHEMA.append({"name": "Mobility",   "type": "VAR", "base": 5,  "scale": 10})
PARAM_SCHEMA.append({"name": "Tempo",      "type": "VAR", "base": 10, "scale": 20})
# PSTs
for t_name, table in BASE_TABLES:
    for s_idx in range(25):
        PARAM_SCHEMA.append({
            "name": t_name, 
            "type": "PST", 
            "sq_idx": s_idx, 
            "base": table[s_idx], 
            "scale": 20 
        })

# --- 3. LOAD AND EXTRACT ---

def print_pst(name, values):
    print(f"{name} = [")
    for r in range(5):
        row_vals = values[r*5 : (r+1)*5]
        row_str = ", ".join(f"{v:3d}" for v in row_vals)
        print(f"    {row_str},")
    print("]")
    print()

def main():
    try:
        # Load the raw vector (shape: [158])
        theta = np.loadtxt("SPSA_training\\new_params.txt")
    except FileNotFoundError:
        print("Error: parallel_params.txt not found.")
        return

    print("--- EXTRACTED TUNED VALUES ---\n")

    # Storage for PSTs to print them as grids later
    tuned_psts = {name: [0]*25 for name, _ in BASE_TABLES}
    
    # 1. Print Piece Values
    print("# Material Values")
    print(f"PIECE_VALUES = [", end="")
    
    tuned_pieces = [0] * 6
    tuned_pieces[5] = 20000 # King is fixed
    
    # Extract Pieces
    for i in range(5):
        def_p = PARAM_SCHEMA[i]
        val = def_p["base"] + (theta[i] * def_p["scale"])
        tuned_pieces[i] = max(10, int(round(val)))
        
    print(f"{tuned_pieces[0]}, {tuned_pieces[1]}, {tuned_pieces[2]}, {tuned_pieces[3]}, {tuned_pieces[4]}, 20000]")
    print(f"# (Pawn, Right, Knight, Bishop, Queen, King)")
    print()

    # 2. Print Heuristics
    idx = 5
    passed_pawn = int(round(PARAM_SCHEMA[idx]["base"] + (theta[idx] * PARAM_SCHEMA[idx]["scale"])))
    idx += 1
    mobility = int(round(PARAM_SCHEMA[idx]["base"] + (theta[idx] * PARAM_SCHEMA[idx]["scale"])))
    idx += 1
    tempo = int(round(PARAM_SCHEMA[idx]["base"] + (theta[idx] * PARAM_SCHEMA[idx]["scale"])))
    idx += 1
    
    print("# Heuristics")
    print(f"PASSED_PAWN_BONUS = {passed_pawn}")
    print(f"MOBILITY_WEIGHT = {mobility}")
    print(f"TEMPO_BONUS = {tempo}")
    print()

    # 3. Process PSTs
    print("# --- TUNED PIECE-SQUARE TABLES ---")
    
    # Iterate through the rest of the schema
    while idx < len(PARAM_SCHEMA):
        p_def = PARAM_SCHEMA[idx]
        if p_def["type"] == "PST":
            val = p_def["base"] + (theta[idx] * p_def["scale"])
            int_val = int(round(val))
            
            # Store into correct table list
            tuned_psts[p_def["name"]][p_def["sq_idx"]] = int_val
            
        idx += 1

    # Print Grids
    for name, _ in BASE_TABLES:
        print_pst(name, tuned_psts[name])

import csv
import sys
import re

def export_last_params(csv_file="SPSA_training\\spsa_history.csv"):
    try:
        with open(csv_file, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find {csv_file}")
        return

    # 1. Get the Header and Last Valid Data Row
    # We iterate backwards to find the last line that starts with a number (ignoring potential duplicate headers)
    header = []
    last_values = []
    
    # Find header (first line)
    if len(lines) > 0:
        header = lines[0].strip().split(",")
    
    # Find last valid data row
    for line in reversed(lines):
        parts = line.strip().split(",")
        if len(parts) == len(header) and parts[0].replace('.', '', 1).isdigit():
            last_values = parts
            break
            
    if not last_values:
        print("Error: No valid data rows found in CSV.")
        return

    # 2. Parse Data into Dictionaries
    # Defaults
    piece_map = {0: 100, 1: 300, 2: 300, 3: 500, 4: 900, 5: 20000} # P, R, N, B, Q, K
    pst_tables = {} # Key: table_idx, Value: [25 ints]
    vars_map = {}

    print(f"--- EXTRACTED FROM ITERATION {last_values[0]} ---")

    for i, col_name in enumerate(header):
        val_str = last_values[i]
        
        try:
            value = int(float(val_str))
        except ValueError:
            continue # Skip non-numeric columns

        # Identify Parameter Type
        
        # A. Piece Values
        if col_name == "Right":  piece_map[1] = value # Note: Assuming 'Right' mapped to index 1 based on your schema
        elif col_name == "Knight": piece_map[2] = value
        elif col_name == "Bishop": piece_map[3] = value
        elif col_name == "Queen":  piece_map[4] = value
        
        # B. Strategic Variables
        elif col_name in ["PassedPawn", "Mobility", "Tempo"]:
            vars_map[col_name] = value
            
        # C. PST Values (Format: PST_tableIdx_sqIdx)
        elif col_name.startswith("PST_"):
            # Regex to parse PST_0_12
            match = re.match(r"PST_(\d+)_(\d+)", col_name)
            if match:
                t_idx = int(match.group(1))
                s_idx = int(match.group(2))
                
                if t_idx not in pst_tables:
                    pst_tables[t_idx] = [0] * 25
                
                pst_tables[t_idx][s_idx] = value

    # 3. Generate Code Output
    print("\n# --- COPY BELOW THIS LINE INTO advanced_eval.py ---\n")
    
    # Piece Values
    # Order: PAWN, RIGHT, KNIGHT, BISHOP, QUEEN, KING
    # Ensure King is kept high (20000) and Pawn is anchored (100)
    final_pieces = [piece_map.get(i, 0) for i in range(6)]
    # Force King to be safe if not in CSV
    final_pieces[5] = 20000 
    
    print(f"PIECE_VALUES = {final_pieces}")
    
    # Strategic Variables
    mapping = {
        "PassedPawn": "PASSED_PAWN_BONUS",
        "Mobility": "MOBILITY_WEIGHT",
        "Tempo": "TEMPO_BONUS"
    }
    for csv_name, code_name in mapping.items():
        if csv_name in vars_map:
            print(f"{code_name} = {vars_map[csv_name]}")

    # PST Tables
    # We reconstruct the list of lists
    if pst_tables:
        print("\nTABLES_WHITE = [")
        sorted_indices = sorted(pst_tables.keys())
        for idx in sorted_indices:
            print(f"    {pst_tables[idx]}, # Table {idx}")
        print("]")
        print("\n# Mirror for Black")
        print("TABLES_BLACK = [mirror_pst(t) for t in TABLES_WHITE]")
    
    print("\n# --------------------------------------------------")

if __name__ == "__main__":
    export_last_params()

# if __name__ == "__main__":
#     main()