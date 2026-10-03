from Piece_classes import pieces as parent
from gmpy2 import xmpz
import math

class Bishop(parent.Piece):
    def __init__(self,master,piece,row,col,piece_type):
        super().__init__(master,piece,row,col,piece_type)
    
    # generates all possible moves for a piece
    def update_legal_moves(self):
        self.legal_moves = xmpz(0)
        self.ghost_moves = xmpz(0)
        
        square = int(math.log2(self.pos))
        row,col = square//8,square%8
        
        #setting variables that controll how far the ray tracer searches in each dirrection
        left_up,left_down,right_up,right_down,a = False,False,False,False,1

        while left_up==False or left_down==False or right_up==False or right_down==False:
            this_left = col-a
            this_right = col+a
            this_up = row-a
            this_down = row+a
 
            if this_left >=0:
                if this_up >=0:
                    left_up = self.check_square((this_up<<3)+this_left,left_up)
                else:
                    left_up = True
                if this_down <=7:
                    left_down = self.check_square((this_down<<3)+this_left,left_down)
                else:
                    left_down = True
            else:
                left_up=True
                left_down=True
            
            if this_right <=7:
                if this_up >=0:
                    right_up = self.check_square((this_up<<3)+this_right,right_up)
                else:
                    right_up = True

                if this_down <=7:
                    right_down = self.check_square((this_down<<3)+this_right,right_down)
                else:
                    right_down = True
            else:
                right_up=True
                right_down=True
                
            # incriments to search sqaures 1 move away from the piece
            a+=1



"""

            if left_down == False and col-a >= 0 and row+a <=7 and self.master.board[row+a,col-a].colour == None:
                self.legal_moves = np.append(self.legal_moves,[[(row+a),(col-a)]], axis=0)
#                self.legal_moves_array[row+a,col-a] = self.master.ascii_board[row+a,col-a] if self.master.board[row+a,col-a].colour != None else "x"
            else:
                if col-a >= 0 and row+a <=7 and self.master.board[row+a,col-a].colour != None and self.master.board[row+a,col-a].colour != self.colour and left_down == False:
                    self.legal_moves = np.append(self.legal_moves,[[(row+a),(col-a)]], axis=0)
#                    self.legal_moves_array[row+a,col-a] = self.master.ascii_board[row+a,col-a]
                left_down = True
            
            if left_up == False and col-a >= 0 and row-a >=0 and self.master.board[row-a,col-a].colour == None:
                self.legal_moves = np.append(self.legal_moves,[[(row-a),(col-a)]], axis=0)
#                self.legal_moves_array[row-a,col-a] = self.master.ascii_board[row-a,col-a] if self.master.board[row-a,col-a].colour != None else "x"
            else:
                if col-a >= 0 and row-a >=0 and self.master.board[row-a,col-a].colour != None and self.master.board[row-a,col-a].colour != self.colour and left_up == False:
                    self.legal_moves = np.append(self.legal_moves,[[(row-a),(col-a)]], axis=0)
#                    self.legal_moves_array[row-a,col-a] = self.master.ascii_board[row-a,col-a]
                left_up = True

            if right_up == False and col+a <= 7 and row-a >=0 and self.master.board[row-a,col+a].colour == None:
                self.legal_moves = np.append(self.legal_moves,[[(row-a),(col+a)]], axis=0)
#                self.legal_moves_array[row-a,col+a] = self.master.ascii_board[row-a,col+a] if self.master.board[row-a,col+a].colour != None else "x"
            else:
                if col+a <=7 and row-a >=0 and self.master.board[row-a,col+a].colour != None and self.master.board[row-a,col+a].colour != self.colour and right_up == False:
                    self.legal_moves = np.append(self.legal_moves,[[(row-a),(col+a)]], axis=0)
#                    self.legal_moves_array[row-a,col+a] = self.master.ascii_board[row-a,col+a]
                right_up = True
            
            if right_down == False and col+a <=7 and row+a <=7 and self.master.board[row+a,col+a].colour == None:
                self.legal_moves = np.append(self.legal_moves,[[(row+a),(col+a)]], axis=0)
#                self.legal_moves_array[row+a,col+a] = self.master.ascii_board[row+a,col+a] if self.master.board[row+a,col+a].colour != None else "x"
            else:
                if col+a <=7 and row+a <=7 and self.master.board[row+a,col+a].colour != None and self.master.board[row+a,col+a].colour != self.colour and right_down == False:
                    self.legal_moves = np.append(self.legal_moves,[[(row+a),(col+a)]], axis=0)
#                    self.legal_moves_array[row+a,col+a] = self.master.ascii_board[row+a,col+a]
                right_down = True   
"""