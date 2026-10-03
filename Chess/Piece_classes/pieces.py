import tkinter as tk
from PIL import ImageTk, Image
import numpy as np
#from functools import lru_cache
from gmpy2 import xmpz
import math

file_type = {"classic":"png","periodic":"png", "hidden":"png"}


#https://en.wikipedia.org/wiki/Chess_piece_relative_value#:~:text=The%20best%20known%20system%20assigns,piece%20is%20very%20position%20dependent.

#https://thenounproject.com FOR ICONS 
# https://www.photopea.com to create images
# piece parent class to all pieces, contains no functionality as each piece is unique 

class Piece(tk.Label):
    def __init__(self,master,piece,row,col,piece_type):
        self.master = master
        if piece != 0:
            if piece > 7:
                self.colour = 1
            else: 
                self.colour = 0
            if piece_type == "ascii":
                try:
                    pieces = {self.master.bpawn:"♟",self.master.bknight:"♞",self.master.bbishop:"♝",self.master.brook:"♜",self.master.bqueen:"♛",self.master.bking:"♚",self.master.wpawn:"♙", self.master.wknight:"♘", self.master.wbishop:"♗", self.master.wrook:"♖", self.master.wqueen:"♕", self.master.wking:"♔", self.master.no_piece:''}
                except:
                    pieces = {self.master.bpawn:"♟", self.master.wpawn:"♙"}
                    
                super().__init__(master,text = pieces[piece], font= ["arial",50], borderwidth=0,bg=master.colour_scheme["white"] if (row+col)%2==0 else master.colour_scheme["black"])
            elif piece_type == "secret":   
                super().__init__(master,text = '    ', font= ["arial",35], borderwidth=0,bg=master.colour_scheme["white"] if (row+col)%2==0 else master.colour_scheme["black"])
                    
            elif piece_type == "hidden":

                self.img = Image.open(f"Pieces_img/{piece_type}/{piece_type}.{file_type[piece_type]}")
                self.img = self.img.resize((75, 75))
                self.img = ImageTk.PhotoImage(self.img)
                super().__init__(master,borderwidth=0,image=self.img,bg="gray")
            else:
                #checks if the pieces is white (.isupper() will be True)
                to_ascii = {1: "p", 2: 'n', 3: 'b', 5: 'r', 6: 'q', 4: 'k', 9: 'P', 10: 'N', 11: 'B', 13: 'R', 14: 'Q', 12: 'K'}
                if piece > 7:
                    # fetches the white image corelating to the piece
                    self.img = Image.open(f"Pieces_img/{piece_type}/{piece_type}w{to_ascii[piece]}.{file_type[piece_type]}")
                else: 
                    #fetches the black image corelating to the piece
                    self.img = Image.open(f"Pieces_img/{piece_type}/{piece_type}b{to_ascii[piece]}.{file_type[piece_type]}")
                    if master.game_type =="2p":
                        self.img = self.img.transpose(Image.ROTATE_180)
                    
                #sets the image to a standard size and applys it to the object    
                self.img = self.img.resize((90, 90))
                self.img = ImageTk.PhotoImage(self.img)
                super().__init__(master,borderwidth=0,image=self.img,bg="gray")
        else:
            #used for empty squares so operations can be generalised to be performed on tk.lable objects
            super().__init__(master,borderwidth=0,bg=master.colour_scheme["white"] if (row+col)%2==0 else master.colour_scheme["black"])
            self.colour = None

        # piece attributes
            
        self.pos = xmpz(0)
        self.pos[(row<<3)+col]=1
        self.piece = piece
        try:
            values = {self.master.bpawn:100,self.master.bknight:305,self.master.bbishop:333,self.master.brook:563,self.master.bqueen:950,self.master.bking:0,self.master.no_piece:0}
        except: 
            values = {1:100}
        self.value = values[piece % 8]
        self.has_moved = 0
        self.legal_moves = xmpz(0)
        self.ghost_moves = xmpz(0)
        
        # passed by refenece so these will not need to be updated seperately
        if self.colour:
            self.enemy = self.master.black_positions
            self.friend = self.master.white_positions
        else:
            self.enemy = self.master.white_positions
            self.friend = self.master.black_positions
         
    def __str__(self):
        return f"{math.log2(self.pos),self.piece}"
    
    def destroy(self):
        super().destroy()

    # uses polymorphism to redefine this function so that it updates structures to show the piece has been captured
    def grid_remove(self):
        super().grid_remove()
        self.ghost_moves = xmpz(0)
        self.master.captured_pieces.push(self)
        if self.piece != 0:
            self.master.piece_list = np.delete(self.master.piece_list, np.where(self.master.piece_list == self))
            if self.colour: # checks if white
                self.master.white_pieces = np.delete(self.master.white_pieces, np.where(self.master.white_pieces == self))
            else:
                self.master.black_pieces = np.delete(self.master.black_pieces, np.where(self.master.black_pieces == self))

    # to ensure all pieces that are required to generate legal moves
    def update_legal_moves(self):
        raise NotImplementedError
  
    #checks if a sqaure is a legal move for the piece
    # returns True to signify that sliding pieces have met a barrier
    def check_square(self,square,found= False):
            pos = xmpz(2**square)
            if  (pos & (self.enemy | self.friend)) == 0 and not found:
                self.legal_moves[square] = 1
                self.ghost_moves[square] = 1
                return False
            else:
                if (pos & self.enemy) and not found:
                    self.legal_moves[square] = 1
                    self.ghost_moves[square] = 1
                if pos & self.friend:
                    self.ghost_moves[square] = 1
                return True
    
    def captured(self):
        self.ghost_moves = xmpz(0)
        self.master.captured_pieces.push(self)
        if self.piece != 0:
            self.master.piece_list = np.delete(self.master.piece_list, np.where(self.master.piece_list == self))
            if self.colour: # checks if white
                self.master.white_pieces = np.delete(self.master.white_pieces, np.where(self.master.white_pieces == self))
            else:
                self.master.black_pieces = np.delete(self.master.black_pieces, np.where(self.master.black_pieces == self))