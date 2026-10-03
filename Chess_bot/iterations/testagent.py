from chessmaker.chess.base import Board
from itertools import cycle
from agent import agent
from extension.board_utils import print_board_ascii, list_legal_moves_for, copy_piece_move
from extension.piece_pawn import Pawn_Q
from samples import white, black, sample0, sample1
import sys, time
from itertools import cycle
from chessmaker.chess.base import Board
from extension.board_utils import print_board_ascii, copy_piece_move
from extension.board_rules import get_result, thinking_with_timeout, THINKING_TIME_BUDGET, GAME_TIME_BUDGET
from samples import white, black, sample0, sample1


if __name__ == "__main__":
    board = Board(
    squares = sample0,
    players=[white,black],
        turn_iterator=cycle([white,black]),
    )
    print_board_ascii(board)
    print(list_legal_moves_for(board,white))
    print(board.current_player.name)