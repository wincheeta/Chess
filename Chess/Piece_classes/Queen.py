from Piece_classes import pieces as parent
from gmpy2 import xmpz
import time
import math

class Queen(parent.Piece):
    def __init__(self,master,piece,row,col,piece_type):
        super().__init__(master,piece,row,col,piece_type)

    def update_legal_moves(self):  # 2.7*10^-4 per move max -> imporved = 6.5*10^-6 -> imporve 8.2 *10^-8
        self.legal_moves = xmpz(0) 
        self.ghost_moves = xmpz(0)

        square = int(math.log2(self.pos))
        row,col = square//8,square%8 
        
        #sets variables for ray tracing search
        left,right,up,down,left_up,left_down,right_up,right_down,a = False,False,False,False,False,False,False,False,1
        
        # a combination of both the bishop and rook moves
        while left==False or right==False or up==False or down==False or left_up==False or left_down==False or right_up==False or right_down==False:
            this_left = col-a
            this_right = col+a
            this_up = row-a
            this_down = row+a

            if this_left >=0:
                if left == False:
                    left = self.check_square((row<<3)+this_left,left)
                if this_up >= 0:
                    left_up = self.check_square((this_up<<3)+this_left,left_up)
                else:
                    left_up = True
                if this_down <=7:
                    left_down = self.check_square((this_down<<3)+this_left,left_down)
                else:
                    left_down = True
            else:
                left = True
                left_down = True
                left_up = True

            if this_right <=7:
                if right == False:
                    right = self.check_square((row<<3)+this_right,right)
                if this_up >= 0:
                    right_up = self.check_square((this_up<<3)+this_right,right_up)
                else:
                    right_up = True
                if this_down <=7:
                    right_down = self.check_square((this_down<<3)+this_right,right_down)
                else:
                    right_down = True
            else:
                right = True
                right_down = True
                right_up = True

            if this_down <=7:
                down = self.check_square((this_down<<3)+col,down)
            else:
                down = True

            if this_up >=0:
                up = self.check_square((this_up<<3)+col,up)
            else:
                up = True
                
            # incriments to search the next squares around the piece
            a+=1

    