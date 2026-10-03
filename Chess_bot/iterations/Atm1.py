import math
from extension.board_utils import list_legal_moves_for, copy_piece_move, take_notes
from extension.board_rules import get_result
import time

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
# This is a placeholder for your heuristic evaluation function.
# It must return a numerical score from the perspective of `agent_player`.
# A positive score means `agent_player` is in a good position.
# A negative score means `agent_player` is in a bad position.
def evaluate_board(board, agent_player):
    """
    Calculates the static evaluation of the board from the
    perspective of the 'agent_player'.
    A positive score is good for the agent, negative is bad.
    """
    score = 0
    for piece in board.get_pieces():
        value = PIECE_VALUES.get(piece.name.lower(), 0)
        
        if piece.player == agent_player:
            score += value
        else:
            score -= value
            
    return score

def alpha_beta(board, agent_player, depth, alpha, beta, start_time, time_limit):
    """
    Performs the alpha-beta minimax search.

    Parameters:
    - board: The current board state (a clone).
    - depth: The remaining depth to search.
    - alpha: The best value found so far for the maximizer.
    - beta: The best value found so far for the minimizer.
    - is_maximizing_player: Boolean, true if it's the maximizer's turn.
    - agent_player: The player object (e.g., white) that we (the agent) are.
    """

    # --- 1. Terminal Node Check (Base Case) ---

    # Check for game over (win/loss/draw)
    # get_result() is called at the *start* of a player's turn.
    # If it returns a result, the 'board.current_player' is the one who
    # is checkmated or stalemated.
    
    if TIMEOUT_DEADLINE >= (time_limit - (time.perf_counter() - start_time)):
        raise TimeoutException("Timeout")
    
    start_time = time.perf_counter()
    res = get_result(board)
    if res:
        if "Draw" in res:
            return 0
        
        # If the current player (who is about to move) has lost...
        if f"{agent_player.name} loses" in res:
            return -math.inf  # The maximizer (our agent) has lost.
        else:
            return math.inf  # The minimizer (opponent) has lost, so we win.

    # Check if maximum depth is reached
    if depth == 0:
        # Return the heuristic evaluation of the board
        return evaluate_board(board, agent_player)

    # --- 2. Recursive Step ---

    maxEval = -math.inf
    # Get all legal moves for the current player (the maximizer)
    legal_moves = list_legal_moves_for(board, board.current_player)
    
    for piece, move in legal_moves:
        # Create a *new* clone for this specific move simulation
        sim_board = board.clone()
        
        # Find the corresponding piece/move on the new clone
        # We must use copy_piece_move to get the correct object references
        # for the new board.
        _, sim_piece, sim_move = copy_piece_move(sim_board, piece, move)
        
        if sim_piece and sim_move:
            # Perform the move on the new clone
            sim_piece.move(sim_move)
            
            # Recursive call (now it's the minimizer's turn)
            score = alpha_beta(sim_board, agent_player, depth - 1, -beta, -alpha, start_time, time_limit)
            maxEval = max(maxEval, score)
            alpha = max(alpha, maxEval)
            if alpha >= beta:
                break  # Beta cut-off
    return maxEval

def best_move_at_depth(board,agent_player,time_limit):
    """
    Performs an iterative deepening search.
    It searches to depth 1, then depth 2, then depth 3, and so on,
    until the time limit is reached.
    """
    start_time = time.perf_counter()
    depth = 1
    alpha, beta = -math.inf, math.inf
    best_move_found = None
    best_piece_found = None
    best_score = -math.inf
    
    while True:
        time_left = time_limit - (time.perf_counter() - start_time)
        if time_left < TIMEOUT_DEADLINE:  # Not enough time for another, deeper search
            take_notes("-> Not enough time for next depth.")
            break
            
        take_notes(f"Searching Depth {depth}, Time Left: {time_left:.2f}s")
        
        try:
            legal_moves = list_legal_moves_for(board, agent_player)
            
            # Iterate through all legal moves at the root
            for piece, move in legal_moves:
                # Simulate the move on a cloned board
                sim_board = board.clone()
                _, sim_piece, sim_move = copy_piece_move(sim_board, piece, move)
                
                if sim_piece and sim_move:
                    sim_piece.move(sim_move)
                    
                    # Call alpha_beta for the *opponent's* turn
                    score = alpha_beta(sim_board,agent_player, depth - 1, alpha, beta,start_time,time_left)
                    
                    # Update the best move found so far
                    if score > best_score:
                        best_score = score
                        best_piece_found = piece
                        best_move_found = move
                    
                    # Update alpha at the root
                    alpha = max(alpha, best_score)

            # Return the best piece and move found from the *original* board
            # If the search completes and returns a move (not a timeout)
            if move:
                take_notes(f"  > Depth {depth} complete. Score: {score}")
            else:
                # This can happen if the first move searched resulted in a timeout
                take_notes(f"  > Depth {depth} timed out before finding a move.")
                break

        except TimeoutException:
            take_notes(f"  > Timeout at depth {depth}.")
            break  # Time is up, stop searching deeper
        except Exception as e:
            take_notes(f"  > Error at depth {depth}: {e}")
            break
        depth += 1  # Increase depth for the next iteration

    return best_piece_found, best_move_found

# --- Main Agent Function ---
# This is the function that will be called by 'test_fullgame.py'
def agent(board, player, var):

    sim_board = board.clone()
    return best_move_at_depth(sim_board,player,var[1]*.9)




