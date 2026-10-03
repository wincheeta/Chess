import random
import time
from extension.board_utils import list_legal_moves_for, take_notes, copy_piece_move

def agent(board, player, var):
    """"
    This is an example of your designed Agent

    Parameters
    ----------
    board: the current chess board
    player: your assigned player role (white or black)
    var:  [ply, THINKING_TIME_BUDGET] a list cotaining the ply ID and the thinking_time_budget (secs)

    Returns
    -------
    piece: your selected chess piece
    move_opt: your selected move of your selected chess piece
    
    Hints:
    -----
    - List of players on the current board game: list(board.players) - default list: [Player (white), Player (black)]
    - board.players[0].name = "white" and board.players[1].name = "black"
    - Name of the player assigned to the Agent (either "white" or "black"): player.name
    - list of pieces of the current player: list(board.get_player_pieces(player))
    - List of pieces and corresponding moves for each pieces of the player: piece, move_opt = list_legal_moves_for(board, player)
    - From var: ply ID = var[0], timeout = var[1]
    - Use the timeout variable together with time.perf_counter()
    to ensure the agent returns its best move before the time limit expires.
    """
    piece, move_opt = None, None
    print(f"Ply: {var[0]}")
    
    if player.name == "white":
        legal = list_legal_moves_for(board, player)
        if legal:
            # Randome choice from a list of legal move from all pieces
            piece, move_opt = random.choice(legal)
    else:
        legal = list_legal_moves_for(board, player)
        if legal:
            # Randome choice from a list of legal move from all pieces
            piece, move_opt = random.choice(legal)

    return piece, move_opt



PIECE_VALUES = {
    "pawn": 100,
    "knight": 320,
    "bishop": 330,
    "right": 750,  
    "queen": 900,
    "king": 20000
}

def alphaBeta (board, player, depth, alpha, beta, start_time, time_limit, old_best = None): # starts with results of last search to find best
    time_passed = time.time() - start_time
    if time_passed >= time_limit:
        raise Exception("Timeout")
    if is_terminal(board):
        return eval(board), None
        ## if white eval(board)
        ## if black - eval(board)
    elif depth == 0:
        return eval(board), None
        # if last move was capture -> keep looking for more captues
        # else return eval(board)
        
    best_move = None
    if player == 0:
        maxEva = -float("infinity")
        # if old_best - make that move first then continue
        for piece, move in list_legal_moves_for(board, player):
            cloned_board = board.clone()

            cloned_board.make_move(piece, move)

            # Recursive call:
            # - 'depth - 1' as we go one level deeper
            # - '-beta', '-alpha' is the NegaMax swap
            # - The score is *negated* on return, as a good score for the
            #   opponent is a bad score for us.
            score, move = alphaBeta(cloned_board, 1, depth - 1, -beta, -alpha, start_time, time_limit)

            if score > maxEva:
                maxEva = score
                best_move = move
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return maxEva, best_move
    else:
        minEva = float("infinity")
        # if old_best - make that move first then continue
        for piece, move in list_legal_moves_for(board, player):
            cloned_board = board.clone()

            cloned_board.make_move(piece, move)

            # Recursive call:
            # - 'depth - 1' as we go one level deeper
            # - '-beta', '-alpha' is the NegaMax swap
            # - The score is *negated* on return, as a good score for the
            #   opponent is a bad score for us.
            score, move = alphaBeta(cloned_board, 1, depth - 1, -beta, -alpha, start_time, time_limit)

            if score < maxEva:
                maxEva = score
                best_move = move
            alpha = min(beta, eval)
            if beta <= alpha:
                break
        return minEva, best_move
    
def find_best_move(thinking_time):
    depth = 1
    start_time = time.time()
    old_best = None
    while ((thinking_time - (time.time()-start_time)) >= 0):
        alpha,beta,best_move = float('-inf'),float('inf'), None
        # best_move = alphaBeta(board, depth, (thinking_time - (time.time()-start_time)), alpha, beta)
        old_best = best_move
        depth += 1
        pass
    return old_best

def is_terminal(board): # check final state of board and return a numerical eval
    pass

def check_old_best(): # s
    pass

def eval(baord):
    pass