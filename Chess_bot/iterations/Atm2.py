import math
from extension.board_utils import list_legal_moves_for, copy_piece_move, take_notes
from extension.board_rules import get_result
import time
import random
# import numpy as np 
"""
added traspotion table + quiescence search

to do 
improve eval
    - position of peieces
    - check value
    - encourace promotion
    - king safety

bitboards for effiency

reinforcement learning ^
    

"""
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
def quiescence_search(board, player, alpha, beta, start_time, time_limit, max_depth):
    """
    Performs a capture-only search from the current position
    to stabilize the evaluation.
    """

    # --- 0. Time Limit Check ---
    if TIMEOUT_DEADLINE >= (time_limit - (time.perf_counter() - start_time)):
        raise TimeoutException("Q search Timeout")

    # --- 1. Terminal Node Check ---
    res = get_result(board)
    if res:
        if "Draw" in res:
            return 0
        
        # If the current player (who is about to move) has lost...
        if f"{player.name} loses" in res:
            return -math.inf  # The maximizer (our agent) has lost.
        else:
            return math.inf  # The minimizer (opponent) has lost, so we win.
    
    # We must be able to at least achieve this score.
    if max_depth == 0:
        return evaluate_board(board,player) # Beta cut-off

    # --- 4. Recursive Step (Captures Only) ---
    maxEval = -math.inf
    capture_moves = find_all_captures(board, board.current_player)

    if not capture_moves:
        return evaluate_board(board,player)
    
    for piece, move in capture_moves:
        sim_board = board.clone()
        _, sim_piece, sim_move = copy_piece_move(sim_board, piece, move)
        
        if sim_piece and sim_move:
            sim_piece.move(sim_move)
            
            score = -quiescence_search(sim_board, player, -beta, -alpha, start_time, time_limit, max_depth-1)
            
            score = max(maxEval, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
    
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
        return quiescence_search(board, agent_player,-beta, -alpha, start_time, time_limit, 2)

    # check all captures first
    
    
    
    
    # --- 2. Recursive Step for rest of moves - non captures---

    maxEval = -math.inf
    # Get all legal moves for the current player (the maximizer)
    legal_moves = find_non_captures(board, board.current_player)
    
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

def find_all_captures(board,agent_player):
    captures = []
    for p,m in list_legal_moves_for(board, agent_player):
        if getattr(m, "captures", None):
            captures.append((p, m))
    return captures

def find_non_captures(board,agent_player):
    moves = []
    for p,m in list_legal_moves_for(board, agent_player):
        if not getattr(m, "captures", None):
            moves.append((p, m))
    return moves


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
    find_all_captures(sim_board,player)
    best_piece_found, best_move_found = best_move_at_depth(sim_board,player,var[1])
    print(best_piece_found, best_move_found)
    return best_piece_found, best_move_found




# class Transposition():
#     def __init__(self):
#         self.random_context = Ranctx()
    
#     def generate_random_number(self):
#         self.seed += 281 # arbitrary constant
#         self.raninit(self.random_context, self.seed)
#         return int(self.ranval(self.random_context) & 0xFFFFFFFFFFFFFFFF)
    
#     #creates all the masks that will be used to create the hash
#     def set_masks(self): 
#         self.seed = 0
#         self.white_kings =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.white_queens =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.white_rights =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.white_bishops =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.white_knights =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.white_pawns =np.array(np.append(np.append([[0,0,0,0,0,0,0,0]],[[self.generate_random_number() for a in range(5)]for b in range(6)],axis=0),[[0,0,0,0,0,0,0,0]],axis=0))
        
#         self.black_kings =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.black_queens =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.black_rights =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.black_bishops =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.black_knights =np.array([[self.generate_random_number() for a in range(5)]for b in range(5)])
#         self.black_pawns =np.array(np.append(np.append([[0,0,0,0,0,0,0,0]],[[self.generate_random_number() for a in range(5)]for b in range(6)],axis=0),[[0,0,0,0,0,0,0,0]],axis=0))
        
#         # packs all of the piece hashes into one list that can be accessed using the picee type -1 as an index
#         self.white_hash = np.array([self.white_pawns,self.white_knights,self.white_bishops,self.white_rights,self.white_queens,self.white_kings])
#         self.black_hash = np.array([self.black_pawns,self.black_knights,self.black_bishops,self.black_rights,self.black_queens,self.black_kings])
        
#         self.blacks_move = self.generate_random_number()
#         # self.castling = np.array([self.generate_random_number() for i in range(4)]) --- may have been removed??
#         self.passant_files = np.array([self.generate_random_number() for i in range(5)])
        
#     def rot(self,x, k):
#         return ((x << k) | (x >> (64 - k)))

#     def ranval(self,x):
#         e = x.a - self.rot(x.b, 7)
#         x.a = x.b ^ self.rot(x.c, 13)
#         x.b = x.c + self.rot(x.d, 37)
#         x.c = x.d + e
#         x.d = e + x.a
#         return x.d

#     def raninit(self,x, seed):
#         x.a = 0xf1ea5eed
#         x.b = x.c = x.d = seed
#         for _ in range(20):
#             self.ranval(x)
            
#     def initial_hash(self,board):
#         hash = 0
#         white,black = board
#         for i in range(6):
#             a= white[i].bit_scan1(0)
#             while a != None:
#                 hash ^= int(self.white_hash[i][a//8,a%8])
#                 a= white[i].bit_scan1(a+1)

#             b= black[i].bit_scan1(0)
#             while b != None:
#                 hash ^= int(self.black_hash[i][b//8,b%8])
#                 b= black[i].bit_scan1(b+1)
        
#         b= self.master.available_castle.bit_scan1(0)
#         while b != None:
#             hash ^=  int(self.castling[b])
#             b = self.master.available_castle.bit_scan1(b+1)
            
#         return hash
    
#     # updates the hash for the move made
#     def hash(self,move,hash):
#         # alteres whos turn it is and removes any previous en passant files
#         hash ^= self.blacks_move ^ self.prev_passant
        
#         #decodes the move
#         out = str(bin(move)[2:].zfill(24))
#         captured,piece,start,end,type = [int(out[:4],2), int(out[4:8],2), [(int(out[8:11],2)),(int(out[11:14],2))], [(int(out[14:17],2)),(int(out[17:20],2))], int(out[20:],2)]
        
#         # removes a captured piece from the hash
#         if captured:
#             if captured >7:
#                 hash ^= int(self.white_hash[captured%8-1][end[0],end[1]])
#             else:
#                 hash ^= int(self.black_hash[captured-1][end[0],end[1]])
        
#         # moves the piece between squares on the hash
#         if piece >7:
#             hash ^= int(self.white_hash[piece%8-1][start[0],start[1]]) ^ int(self.white_hash[piece%8-1][end[0],end[1]])
#         else:
#             hash ^= int(self.black_hash[piece-1][start[0],start[1]]) ^ int(self.black_hash[piece%8-1][end[0],end[1]])
            
#         return hash
    
#         # takes the index which has lost its castling rights 
#     # in the boards castling varriable and removes it from the hash
#     def undo_castling(self,hash,index):
#         return hash ^ self.castling[index]
        
#     def insert(self,hash,eval):
#         self.data[hash] = eval
#         #inserts data at a give index
        
#     # returns the data at a given hash
#     def find(self,hash):
#         if hash in self.data.keys():
#             return self.data[hash]
#         else:
#             return False
            
# class Ranctx:
#     def __init__(self):
#         self.a = 0
#         self.b = 0
#         self.c = 0
#         self.d = 0

