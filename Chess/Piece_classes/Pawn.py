from Piece_classes import pieces as parent
from gmpy2 import xmpz
import time
import math


class Pawn(parent.Piece):
    def __init__(self,master,piece,row,col,piece_type):
        super().__init__(master,piece,row,col,piece_type)
        self.has_moved = 0
        if self.colour: # it works as they are passed by reference
            self.enemy = self.master.black_positions
            self.friend = self.master.white_positions
        else:
            self.enemy = self.master.white_positions
            self.friend = self.master.black_positions


    def update_legal_moves(self): # 5*10-6 per move generated
        self.legal_moves = xmpz(0)
        self.ghost_moves = xmpz(0)
        square = int(math.log2(self.pos))
        row,col = square//8,square%8  

        if self.colour:
            self.check_forward(((row-1)<<3)+col,(row-2<<3)+col)
            self.check_take(row-1,col)
        else:
            self.check_forward(((row+1)<<3)+col,(row+2<<3)+col)
            self.check_take(row+1,col)



    def check_forward(self,square1,square2):
        if ( 2**(square1) & (self.enemy | self.friend))==0:
            blocked = self.check_square(square1)
            if (not self.has_moved) and (not blocked) and (square2>0 and len(bin(square2))<=66) and ( 1<<(square2) & (self.enemy | self.friend))==0: #and (board[row2,col].colour == None):
                self.legal_moves[square2] =1
                self.ghost_moves[square2] =1
            elif not self.has_moved:
                self.ghost_moves[square2] =1
        else: 
            self.ghost_moves[square1] =1

    def check_take(self,row,col):
        left,right = (row<<3)+col-1,(row<<3)+col+1
        if col>=1:
            pos = xmpz(0)
            pos[left] =1 
            if (pos&self.enemy) | (pos & self.master.en_passant):
                self.legal_moves[left] =1
            self.ghost_moves[left] =1
        if col <=6:
            pos = xmpz(0)
            pos[right] =1 
            if (pos&self.enemy) | (pos & self.master.en_passant):
                self.legal_moves[right] =1
            self.ghost_moves[right] =1




"""             if row1<=7 and col>=1 and not board[row1,left].colour in (None,self.colour):
                self.legal_moves = append(self.legal_moves,[[row1,left]], axis=0)
                self.ghost_moves = append(self.ghost_moves,[[row1,left]], axis=0)
            if row1<=7 and col<=6:
                if not board[row1,right].colour in (None,self.colour):
                    self.legal_moves = append(self.legal_moves,[[row1,right]], axis=0)
                self.ghost_moves = append(self.ghost_moves,[[row1,left]], axis=0)
                self.ghost_moves = append(self.ghost_moves,[[row1,right]], axis=0)

    def pawn_moves(self,row,row1,row2,col,board):
        left1 = col- 1
        right1= col+ 1

        if row1>=0 and row1<=7 and board[row1,col].colour == None:
            self.check_square(row1,col)       
            if board[row2,col].colour == None and not self.has_moved:
                self.check_square(row1,col)

        #taking 
        if row>=1 and col>=1 and board[row1,left1].colour != None and board[row1,left1].colour != self.colour:
            self.legal_moves = append(self.legal_moves,[[(row1),(left1)]], axis=0)
        if row>=1 and col<=6 and board[row1,right1].colour != None and board[row1,right1].colour != self.colour:
            self.legal_moves = append(self.legal_moves,[[(row1),(right1)]], axis=0)

 """