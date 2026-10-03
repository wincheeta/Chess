import tkinter as tk
import numpy as np
from Piece_classes import pieces,Pawn,Bishop,Knight,Rook,Queen,King
from Chess_bot import Transposition_table,alpha_beta
from Chess_board import Stack,Move_handler
from gmpy2 import xmpz
import math
import re

# board class which will be used to create a chessboard from a given FEN string, is a child of tk.frame so it can contain the gui function of the board
class chessboard(tk.Frame):
    def __init__(self, master=None,FEN="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",stack=[],piece_type="classic", game_type="2p", colour_scheme=["#e2bd8d","#421e00"], border_width = 35):
        super().__init__(master,borderwidth=border_width, bg=colour_scheme[1])

        self.initialise_constants()
        
        self.master = master
        self.piece_type = piece_type
        self.game_type = game_type
        self.move_stored = False
    
        self.border_width =border_width
        self.recent_moves = Stack.Stack()
        self.captured_pieces = Stack.Stack()
        {self.recent_moves.push(int(i)) for i in stack}

        self.colour_scheme = {"white": colour_scheme[0], "black": colour_scheme[1]}

        self.move_handler = Move_handler.Move_handler(self)
        
        self.piece_board = np.zeros((8,8),dtype=int)
        self.FEN_extractor(FEN) #
        self.board_background()
        self.create_boarder()
        self.create_backbutton()
        
        self.create_widgets()

        self.board  = np.array([[self.grid_slaves()[-(65+(8*a+i))] for i in range(8)] for a in range(8)])
        self.set_all_piece_moves()
        
        self.update_can_take(1)
        self.update_can_take(0)
        self.white_king.update_legal_moves()
        self.black_king.update_legal_moves()

        
        self.transposition = Transposition_table.Transpoisition(self)
        self.bot = alpha_beta.Alpha_Beta(self)
                        
    def __str__(self): 
        return f"{self.convert_into_fen()}"
    
    def destroy(self):
        super().destroy() 
        try:
            self.master.update_board.delete("1.0", tk.END)
            self.master.update_board.insert(tk.END, self.convert_into_fen(),self.recent_moves)
        except:
            return self.convert_into_fen(),self.recent_moves

        #return self.convert_into_fen(),self.recent_moves

    # used to declutter the constructor and make it more readable. all constants and variables are defined here for the board class 
    def initialise_constants(self):
        self.pieces = {'p':"♟",'n':"♞",'b':"♝",'r':"♜",'q':"♛",'k':"♚", "P":"♙", "N":"♘", "B":"♗", "R":"♖", "Q":"♕", "K":"♔"}
        self.pieces_revesed = {'♟': 'p', '♞': 'n', '♝': 'b', '♜': 'r', '♛': 'q', '♚': 'k', '♙': 'P', '♘': 'N', '♗': 'B', '♖': 'R', '♕': 'Q', '♔': 'K'}

        self.binary = {"a":0,"b":1,"c":2,"d":3, "e":4, "f":5, "g":6, "h":7}
        self.binary_reversed = {7: 'h', 6: 'g', 5: 'f', 4: 'e', 3: 'd', 2: 'c', 1: 'b', 0: 'a'}
        
        # the numerical representation of each piece
        self.no_piece = 0
        self.bpawn = 1
        self.bknight = 2
        self.bbishop = 3
        self.brook = 5
        self.bqueen = 6
        self.bking = 4
        
        self.wpawn = 9
        self.wknight = 10
        self.wbishop = 11
        self.wrook = 13
        self.wqueen = 14
        self.wking = 12
        
        self.piece_list = []
        self.white_pieces = []
        self.black_pieces = []   
        self.white_positions= xmpz(0)
        self.black_positions= xmpz(0) 
        self.white_can_take = xmpz(0)
        self.black_can_take = xmpz(0)
        self.black_king = None
        self.white_king = None   
        self.available_castle = xmpz(0)
        self.en_passant = xmpz(0)
        self.old_passant = xmpz(0)
        
    # creates the tkinter "widgets" corresponding to each piece using their classes
    # then updates the board structures to reflect these pieces and places the piece on the GUI
    # finally the piece is given draggable functionality by the move handler
    def create_widgets(self):
        for row in range(8):
            for col in range(8):
                current = self.piece_board[row][col]
                temp = current % 8
                if temp == 0:
                    piece = pieces.Piece(self,current,row,col,self.piece_type)
                else:
                    if temp == self.bpawn:
                        piece = Pawn.Pawn(self,current,row,col,self.piece_type)
                    elif temp == self.bknight:
                        piece = Knight.Knight(self,current,row,col,self.piece_type)                    
                    elif temp == self.bbishop:
                        piece = Bishop.Bishop(self,current,row,col,self.piece_type)   
                    elif temp == self.brook:
                        piece = Rook.Rook(self,current,row,col,self.piece_type)       
                    elif temp == self.bqueen:
                        piece = Queen.Queen(self,current,row,col,self.piece_type)  
                    elif temp == self.bking:
                        piece = King.King(self,current,row,col,self.piece_type)  
                        
                    self.move_handler.add_dragable(piece)

                    if current > 7:
                        self.white_pieces = np.append(self.white_pieces,piece)
                        self.white_positions[(row<<3)+col] = 1
                    else:
                        self.black_pieces = np.append(self.black_pieces,piece)
                        self.black_positions[(row<<3)+col] = 1

                    self.piece_list = np.append(self.piece_list,piece)
                                                                             
                piece.grid(row=row, column=col)
    
    # once all pieces are placed on the board they can generate their possible moves
    def set_all_piece_moves(self):
        for i in self.piece_list:
            if (i.piece % 8) != self.bking: # checks that the piece is not a king as it must be calculated differently
                i.update_legal_moves()
    
    # creates the square notation that goes on the edge of the board
    def create_boarder(self):
        side_border = tk.Frame(self,bg=self.colour_scheme["black"],height=(800),width=self.border_width)
        bottom_border = tk.Frame(self,bg=self.colour_scheme["black"],width=(800),height=self.border_width)

        for i in range(1,9):
            tk.Label(side_border,text=str(9-i), font = ("arial",15),fg=self.colour_scheme["white"],bg=self.colour_scheme["black"],pady=34).grid(column=0,row=(i-1),sticky="nesw")
            tk.Label(bottom_border,text=self.binary_reversed[i-1], font = ("arial",15),fg=self.colour_scheme["white"],bg=self.colour_scheme["black"],padx=42).grid(column=(i-1),row=0,sticky="nesw")
        bottom_border.place(rely =((800+1.5*self.border_width)/(800+2*self.border_width)), relx = 0.5,anchor="center", bordermode="ignore")
        side_border.place(relx =((0.5*self.border_width)/(800+2*self.border_width)), rely = 0.5,anchor="center", bordermode="ignore")
    
    # creates a back button and places it in the bottom left hand of the board
    def create_backbutton(self): #symbol is just a placeholder
        tk.Button(self, text="⬅️",font =("arial",13),fg = self.colour_scheme["white"],bg = self.colour_scheme["black"],borderwidth=0, command=self.reverse_move).place(relx =0, rely =1,anchor="sw", bordermode="ignore")

    #creates a 8*8 grid of coloured squares to serve as the board being played on
    def board_background(self):
        for row in range(8):
            for col in range(8):
                squares = tk.Frame(self, bg= self.colour_scheme["white"] if (row+col)%2==0 else self.colour_scheme["black"] ,width=100, height=100, borderwidth=0)
                squares.grid(row=row, column=col, sticky="nesw")
    

    # creates 2 64 bit numbers to represent all the squares that each side attacks
    # this is then used to calculate check and checkmate later on
    def update_can_take(self,colour):
        column = 72340172838076673 # the numerical reprisentation of 1s down the left column of a 8x8 bitboard
        if colour: # black is 0 which is False in pyhton
            self.white_can_take = xmpz(0)
            for i in self.white_pieces:
                if i.piece == self.wpawn:# removes any forward moves the pawn can make as they do not threaten the king
                    self.white_can_take |= ((~(column << (int(math.log2(i.pos))%8))) & i.ghost_moves) 
                else:
                    self.white_can_take |= i.ghost_moves # adds all possible moves that could threaten the kingto the bitboard
        else: # same as above but performed on blacks pieces.
            self.black_can_take = xmpz(0)
            for i in self.black_pieces:
                if i.piece == self.bpawn:
                    self.black_can_take |= ((~(column << (int(math.log2(i.pos))%8))) & i.ghost_moves) 
                else:
                    self.black_can_take |= i.ghost_moves
                    
                    
    #converts the move into a unique integer that is added to the stack so it can be reversed at any time
    def store_move(self,start,end,piece,type="quiet",captured=0):
        #if not self.move_stored:
        #convert = {"p":1,"n":2,"b":3,"r":5,"q":6,"k":4,"P":9,"N":10,"B":11,"R":13,"Q":14,"K":12, "-":0}
        move_types = {'quiet': 0, 'double': 1, 'pawn': 1, 'push': 1, 'king-side': 2, 'queen-side': 3, 'capture': 4, 'ep-capture': 5, 'n-promo': 8, 'b-promo': 9, 'r-promo': 10, 'q-promo': 11, 'n-promo-capture': 12, 'b-promo-capture': 13, 'r-promo-capture': 14, 'q-promo-capture': 15}
        self.move =(captured << 20) + (piece <<16)+(((start[0]*8) + start[1]) <<10)+(((end[0]*8) + end[1]<<4)) +move_types[type]
        self.recent_moves.push(int(self.move)) # this is very ugly should be fixed
        self.move_stored = True
        
            #print(self.recent_moves.peak())
            #print(self.recent_moves)
    
    # removes last move from the stack of moves and reverses it updating the GUI to show this
    def reverse_move(self):
        move = self.recent_moves.pop() # returns false if the stack is empty
        if move:
            out = str(bin(move)[2:].zfill(24)) # normalises the number into a sting containing 24 bits
            
            # converts the string into an array holding all decoded information about the move
            breakdown = [int(out[:4],2), int(out[4:8],2), [(int(out[8:11],2)),(int(out[11:14],2))],
                         [(int(out[14:17],2)),(int(out[17:20],2))], int(out[20:],2)]
            erow,ecol = breakdown[2]
            srow,scol = breakdown[3]
            
            if breakdown[-1] >= 8: # checks if the move is a promotion and 
                self.board[srow,scol].destroy() # removed promoted piece
                piece = self.captured_pieces.pop()
            else:
                piece = self.board[srow,scol]
            
            # updates the gui to show the piece has returned to is origional square 
            self.board[erow,ecol].destroy()
            self.board[erow,ecol] = piece
            self.piece_board[erow,ecol] = piece.piece
            piece.grid(row=erow,column=ecol)
            piece.lift()
            piece.pos = xmpz(0)
            piece.pos[(erow<<3)+ecol] =1
           
           
            if self.piece_type in ["ascii","secret"]:
                piece.config(bg= self.colour_scheme["white"] if (erow+ecol)%2==0 else self.colour_scheme["black"])
                    
            piece.has_moved -= 1
            self.half_move -= 1
            
            # checks if last move was a double pawn push for en passant
            self.old_passant = self.en_passant
            previous = str(bin(self.recent_moves.peak())[2:].zfill(24))
            if int(previous[20:],2) == 1:
                row,col = (int(previous[8:11],2)),(int(previous[11:14],2))

                self.en_passant = xmpz(2**(((row-1)<<3)+col) if self.half_move % 2 == 1 else 2**(((row+1)<<3)+col))
                
            else:
                self.en_passant =xmpz(0)

            
            if breakdown[0] == 0: # checks if quiet move
                # replaces with empty piece if none taken
                self.replace_piece(0,tk.Label(self),[erow,ecol],[srow,scol])
            else:
                cap = self.captured_pieces.pop()
                if breakdown[-1] == 5: # accounts for ep capture when replacing piece
                    if self.half_move % 2 == 0:
                        temp_row = srow + 1
                    else:
                        temp_row = srow -1
                else:
                    temp_row = srow
            
                self.board[temp_row,scol] = cap
                self.piece_board[temp_row,scol] = cap.piece
                cap.pos=xmpz(0)
                cap.pos[(temp_row<<3)+scol] =1
                cap.grid(row=temp_row,column=scol)
                cap.lift()
                if self.half_move % 2 == 0:
                    self.black_pieces = np.append(self.black_pieces,cap)
                    self.black_positions[(temp_row<<3)+scol] = 1
                else:
                    self.white_pieces = np.append  (self.white_pieces,cap)
                    self.white_positions[(temp_row<<3)+scol] = 1
                self.piece_list = np.append(self.piece_list,cap)
                 
                cap.update_legal_moves()
                        
            
            if self.half_move % 2 == 0:
                self.white_positions[(erow<<3)+ecol] = 1
                self.white_positions[(srow<<3)+scol] = 0
                self.active_colour = 1
                
            else:
                self.active_colour = 0 
                self.full_move -= 1
                self.black_positions[(erow<<3)+ecol] = 1
                self.black_positions[(srow<<3)+scol] = 0
            
            piece.update_legal_moves()
            self.move_handler.update_affected_pieces(2**(erow*8+ecol),2**(srow*8+scol))
    

    #regex expression to check the format of the fen string
    def is_valid_fen(self, fen):
        fen_pattern = re.compile(
            r'^([rnbqkpRNBQKP1-8]{1,8}/){7}[rnbqkpRNBQKP1-8]{1,8} [wb] (-|K?Q?k?q?) (-|[a-h][2-7]) \d+ \d+$'
        )
        return bool(fen_pattern.match(fen))
    
    # converts an input from FEN string to the corresponding data used to represent it in this program
    def FEN_extractor(self,fen):
        if self.is_valid_fen(fen):
            fen = fen.split(" ")
            self.make_array_of_pieces(fen[0]) # creats board from string
            self.active_colour = 1 if fen[1] == "w" else 0 # 1 represents that it is whites turn to move
            self.convert_castling(fen[2],True) # updates integer representing castling rights
            self.en_passant = xmpz(self.convert_from_binary(fen[3])) # holds the index of the en passant square
            self.half_move = int(fen[4]) # holds half move count for 50 move rule
            self.full_move = int(fen[5]) # holds number of times black has made a move
        else:
            tk.messagebox.showinfo(title="ERROR", message="invalid FEN string input")
            
    #translates the FEN string into a 2D array of the pieces in ther respective positions (black at the top/start of the array)
    def make_array_of_pieces(self,board):
        pieces = {'p': self.bpawn, 'n': self.bknight, 'b': self.bbishop, 'r': self.brook, 'q': self.bqueen, 'k': self.bking, 'P': self.wpawn, 'N': self.wknight, 'B': self.wbishop, 'R': self.wrook, 'Q': self.wqueen, 'K': self.wking, '': self.no_piece}
        temp = board.split("/")
        for i in range(8):
            if temp[i].isalpha():
                row = [pieces[a] for a in temp[i]]
                self.piece_board[i] = np.array(row)
            elif not(temp[i].isnumeric()):
                row = []
                for a in temp[i]:
                    if a.isalpha():
                        row.append(pieces[a])
                    else:
                        for z in range(int(a)):
                            row.append(0)
                self.piece_board[i] = np.array(row)
        
    # converts the current board position into a FEN string
    def convert_into_fen(self):
        to_ascii = {1: "p", 2: 'n', 3: 'b', 5: 'r', 6: 'q', 4: 'k', 9: 'P', 10: 'N', 11: 'B', 13: 'R', 14: 'Q', 12: 'K'}
        board = ""
        count = 0
        for i in self.piece_board:
            temp = ""
            for a in range(len(i)):
                if i[a] == 0 :
                    count+= 1
                    if a == 7:
                        temp += str(count)
                        count = 0
                elif count > 0:
                    temp += str(count) + to_ascii[i[a]]
                    count = 0
                else:
                    temp += to_ascii[i[a]]
            board += temp + "/"
        board = board[:-1]
        self.active_colour = "w" if self.active_colour else "b"
        
        return f"{board} {self.active_colour} {self.convert_castling(self.available_castle,False)} {self.convert_to_binary(self.en_passant)} {self.half_move} {self.full_move}"
    
    # specific translator used to convert too and from the string notation of castling rights 
    # this is used in the FEN conversion
    def convert_castling(self,castle,forward):
        val = {"q":1,"k":2,"Q":4,"K":8,"-":0}
        rev_val = {0:"q",1:"k",2:"Q",3:"K"}
        if forward:
            for i in castle:
                self.available_castle += val[i]
        else:
            temp = ""
            for i in range(3,-1,-1):
                if castle[i]:
                    temp += rev_val[i]
            return temp if temp != "" else "-"

    # converts ep square into a number for the program
    def convert_from_binary(self,move):
        if move == '-':
            return 0
        return 2**((8-int(move[1]))*8+ self.binary[move[0]])
    
    # converts ep square back into binary notation form
    def convert_to_binary(self,move):
        if move:
            move = int(math.log2(move))
            row,col = move//8,move%8
            return self.binary_reversed[col] + str(8-row)
        return "-"
        
    
    # once a pawn has reached the last rank it is deleted and the user is offered 4 options between for which piece they would like to promote to 
    def promote(self,piece,start,move_type=None,captured=0):
        self.move_stored = True
        self.half_move += 1
        square = int(math.log2(piece.pos))
        row,col = square//8,square%8
        container = tk.Frame(self,width=100,height=100, bg="white" if (row+col)%2==0 else "gray", borderwidth=0,padx=0,pady=0)
        container.grid_columnconfigure(col, minsize=2)
        container.grid_rowconfigure(row, minsize=2)

        container.grid(row=row,column=col)
        #self.captured_pieces.push(piece)
        piece.grid_remove()
        
        tk.Button(container, bg= self.colour_scheme["white"], text="♛", font=["arial",15], command= 
                  lambda:[self.store_move(start,[row,col],piece.piece,"q-"+move_type,captured), 
                          self.replace_piece(self.bqueen,container,start,[row,col])]).grid(row=0,column=0, sticky= "nesw")
        tk.Button(container, bg= self.colour_scheme["black"], text="♜" ,font=["arial",15], command= lambda:[self.store_move(start,[row,col],piece.piece,"r-"+move_type,captured), self.replace_piece(self.brook,container,start,[row,col])]).grid(row=0,column=1, sticky= "nesw")
        tk.Button(container, bg= self.colour_scheme["black"], text="♝", font=["arial",15], command= lambda:[self.store_move(start,[row,col],piece.piece,"b-"+move_type,captured), self.replace_piece(self.bbishop,container,start,[row,col])]).grid(row=1,column=0, sticky= "nesw")
        tk.Button(container, bg= self.colour_scheme["white"], text="♞", font=["arial",15], command= lambda:[self.store_move(start,[row,col],piece.piece,"n-"+move_type,captured), self.replace_piece(self.bknight,container,start,[row,col])]).grid(row=1,column=1, sticky= "nesw")

        self.active_colour = None
        
        # self.store_move(start,[row,col],piece.ascii,"q-"+move_type,captured)
        # self.replace_piece("q",container,start,[row,col])

        # places a piece in the position of the pawn and corrects all the data structures to refelct this

    # creates a unique instance of a piece based on argumanents passed and updates the structures to represent this
    def replace_piece(self,p,container,start,pos):
        
        self.move_stored = False # essential as otherwise the program runs too fast in the drag handler and treats it as just a normal capture
        
        row,col = pos
        ssquare = 1<<(start[0]<<3+start[1])
        esquare = 1<<(row<<3+col)
        if p == self.no_piece:
            piece = pieces.Piece(self,0,row,col,piece_type='')
            piece_ascii = 0
        else:
            
            piece_ascii = p + 8*(self.half_move %2)
            
            if p == self.bpawn:
                piece = Pawn.Pawn(self,piece_ascii,row,col,self.piece_type)
            elif p == self.bqueen:
                piece = Queen.Queen(self,piece_ascii,row,col,self.piece_type)
            elif p == self.brook:
                piece = Rook.Rook(self,piece_ascii,row,col,self.piece_type)
            elif p == self.bknight:
                piece = Knight.Knight(self,piece_ascii,row,col,self.piece_type)
            elif p == self.bbishop:
                piece = Bishop.Bishop(self,piece_ascii,row,col,self.piece_type)

            if piece_ascii > 7:
                self.white_pieces = np.append(self.white_pieces,piece)
            elif piece_ascii >0:
                self.black_pieces = np.append(self.black_pieces,piece)
            self.piece_list = np.append(self.piece_list,piece)
            
            piece.update_legal_moves()
            self.move_handler.add_dragable(piece)
            
        
        self.piece_board[row,col] = piece_ascii
        self.board[row,col] = piece
        

        piece.grid(row=row,column=col)

        container.destroy()
        self.move_handler.update_affected_pieces(ssquare,esquare)

        #self.active_colour = 1 if self.half_move %2 ==0 else 0
        
        if self.half_move % 2 == 1:
            self.active_colour = 0
            if self.white_king.pos & self.black_can_take and p != 0:
                self.reverse_move()
        else:
            self.active_colour =1
            self.full_move += 1
            if self.black_king.pos & self.white_can_take and p != 0:
                self.reverse_move()  

    # returns an array of all the possible moves for the active side
    # stored as a 12 bit number (start square, end square)
    def possible_moves(self):
        moves = np.array([])
        if self.active_colour:
            pieces = self.white_pieces
        else:
            pieces = self.black_pieces
        for i in pieces:
            a = i.legal_moves.bit_scan1(0)
            while a != None:
                move = int(math.log2(i.pos))<<6 + a
                moves = np.append(moves,move)
                a = i.legal_moves.bit_scan1(a+1)
        return moves
    
    def possible_captures(self):
        moves = np.array([])
        # use a common variable to make the code shorter and more readable
        if self.active_colour: 
            pieces = self.white_pieces
            enemy_pos = self.black_positions
        else:
            pieces = self.black_pieces
            enemy_pos = self.white_positions
            
        for i in pieces:
            captures = xmpz(i.legal_moves & enemy_pos) # eliminates all quiet moves
            a = captures.bit_scan1(0)
            # goes through all moves that are captures and adds them to a list
            while a != None: 
                move = int(math.log2(i.pos))<<6 + a
                moves = np.append(moves,move)
                a = captures.bit_scan1(a+1)
        return moves
        
    # makes the move produced by the bot
    def bot_make_move(self,move):
        start,end = move&0b111111000000, move& 0b000000111111       
        self.move_handler.start_row,self.move_handler.start_col,self.move_handler.start_pos =start//8,start%8,2**(start)
        self.move_handler.on_drop("",False,end)
    
    def make_random_moves(self,depth=1):
        while depth >0:
            self.bot_make_move()
            depth-=1
            #time.sleep(0.3)
            self.update()
            
    # returns the total value on the board (+ve favours white)
    def get_material(self):
        sum = 0
        for i in self.white_pieces:
            sum += i.value
        for i in self.black_pieces:
            sum -= i.value
        return sum
    
    # returns a value for the overal mobility on the board
    def get_mobility(self):
        sum = 0
        a = self.white_can_take.bit_scan1(0)
        while a != None:
            sum += 1
            a = self.white_can_take.bit_scan1(a+1)
        a = self.black_can_take.bit_scan1(0)
        while a != None:
            sum -= 1
            a = self.black_can_take.bit_scan1(a+1)
        return sum

    # returns a value for the likelyhood of white to win from a given board
    def evaluate(self):
        
        # checks if board has already been visited
        board = self.transposition.find(self.hash)
        if board:
            return board
        
        # if not applies the eval function
        # checks material difference
        eval = self.get_material()
        eval += self.get_mobility()
        
        if self.active_colour:
            eval += 25
        else:
            eval -+ 25        
        # then saves board and its eval to transposition
        self.transposition.insert(self.hash,eval)
        
        return eval

    # checks for stalemate/checkmate
    def terminal(self):
        if self.active_colour:
            # checkmate 
            if self.black_king & self.white_can_take:
                return True
            
            #stalemate
            can_move = False
            for i in self.white_pieces:
                if i.legal_moves:
                    can_move = True
                    break
            return not can_move
                
        else:
            if self.white_king & self.black_can_take:
                return True
            
            can_move = False
            for i in self.black_pieces:
                if i.legal_moves:
                    can_move = True
                    break
            return not can_move
        
    def was_capture(self):
        return (self.recent_moves.peak() & 0b111100000000000000000000) > 0 # checks if a piece was captured

    def checkmate():
        
        #goes through all possible moves if cannot stop check ends game and displays a message to tell the user.
        pass

    def make_move(self,move):
        start,end = move&0b111111000000, move& 0b000000111111
        srow,scol,erow,ecol = start//8,start%8,end//8,end%8
        square = xmpz(0)            
        square[end] = 1
        promo = False
        piece = self.board[srow,scol]


        if  (move & piece.legal_moves) and self.active_colour == piece.colour:
            
            self.move_stored = False
            
            if move & (self.white_positions | self.black_positions):
                move_type = "capture"
                captured = self.board[erow,ecol]
                
                captured.ghost_moves = xmpz(0)
                self.captured_pieces.push(captured)
                if captured.piece != 0:
                    captured.master.piece_list = np.delete(self.piece_list, np.where(self.piece_list == captured))
                    if captured.colour: # checks if white
                        self.white_pieces = np.delete(self.white_pieces, np.where(self.white_pieces == captured))
                    else:
                        self.black_pieces = np.delete(self.black_pieces, np.where(self.black_pieces == captured))
                
                captured_piece= captured.piece
                if (captured_piece %8) == self.brook:
                    if not captured.has_moved:
                        if captured.colour:
                            if captured.pos < self.white_king.pos:
                                self.available_castle[2] = 0
                            else:
                                self.available_castle[3] = 0
                        else:
                            if captured.pos < self.black_king.pos:
                                self.available_castle[0] = 0
                            else:
                                self.available_castle[1] = 0

                
            else:
                move_type = "quiet"
                captured_piece = 0
                
            # updating the relevant data structures and gui
            
            self.board[erow,ecol] = piece
            piece.pos = xmpz(1<<end)
            self.board[srow,scol] = pieces.Piece(self,piece=0,row=srow,col=scol,piece_type='')
            
                        
            if self.half_move % 2 == 0:
                self.white_positions[end] = 1
                self.white_positions[start] = 0
                self.black_positions[end] = 0
            else:
                self.black_positions[end] = 1
                self.black_positions[start] = 0
                self.white_positions[end] = 0
                        
                        
            #promotion check
            if (piece.piece % 8)  == self.bpawn:
                if (move & self.en_passant):
                    r,c = erow,ecol

                    if self.half_move % 2 == 1:
                        r -=1
                        self.white_positions[((r)<<3)+c] = 0
                        self.store_move([srow,scol],[erow,ecol],self.wpawn,"ep-capture",self.bpawn)
                    else:
                        r+= 1
                        self.black_positions[((r)<<3)+c] =0
                        self.store_move([srow,scol],[erow,ecol],self.bpawn,"ep-capture",self.wpawn)
                        
                    self.board[r,c] = pieces.Piece(self,piece=0,row=srow,col=scol,piece_type='')
                    self.piece_board[r,c] = 0
                    self.update_passanted(2**(((r)<<3)+c))
                    
                elif not piece.has_moved and (erow in [srow-2,srow+2]):
                    self.old_passant = self.en_passant
                    self.en_passant = xmpz(2**(((erow-1)<<3)+ecol) if self.half_move % 2 == 1 else 2**(((erow+1)<<3)+ecol) )
                    self.store_move([srow,scol],[srow,scol],piece.piece,"double",captured_piece)
                    
                elif ((piece.pos[0:8] ^ 0) | (piece.pos[56:64] ^ 0)):
                    self.promote(piece,[srow,scol],move_type= "promo" if move_type == "quiet" else "promo-capture",captured=captured_piece)
                    self.store_move(start,[erow,ecol],piece.piece,"q-"+"promo" if move_type == "quiet" else "promo-capture",captured_piece), 
                    self.replace_piece(self.bqueen,tk.Label(self),start,[erow,ecol])
                    promo = True
                    self.old_passant = self.en_passant
                    self.en_passant = xmpz(0)
                    
                else:
                    self.old_passant = self.en_passant
                    self.en_passant = xmpz(0)
                    self.store_move([srow,scol],[erow,ecol],piece.piece,move_type,captured_piece)
                     
            elif (piece.piece % 8)  == self.bking:
                if not piece.has_moved:
                    if piece.colour:
                        self.available_castle %= 4
                    else:
                        self.available_castle[0]=0
                        self.available_castle[1]=0
                if move == self.start_pos << 2:
                    print("right")
                elif move == self.start_pos >> 2:
                    print("left")
                else:
                    if not self.move_stored:
                        self.store_move([srow,scol],[erow,ecol],piece.piece,move_type,captured_piece)
            else:
                if (piece.piece % 8)  == self.brook:
                    if not piece.has_moved:
                        if piece.colour:
                            if scol < int(math.log2(self.white_king.pos)) % 8:
                                self.available_castle[2] = 0
                            else:
                                self.available_castle[3] = 0
                        else:
                            if scol < int(math.log2(self.black_king.pos)) % 8:
                                self.available_castle[0] = 0
                            else:
                                self.available_castle[1] = 0
                self.old_passant = self.en_passant
                self.en_passant = xmpz(0)
                if not self.move_stored:
                    self.store_move([srow,scol],[erow,ecol],piece.piece,move_type,captured_piece)
                
            piece.has_moved +=1
            #s = time.time()
            #for i in range(10000):
            if not promo:
                self.half_move += 1
                self.move_handler.eupdate_affected_pieces(2**((srow<<3)+scol),2**((erow<<3)+ecol)) # 1/1000 per move
                #print((time.time()-s)/10000)

                #turn controlling
                if self.half_move % 2 == 1:
                    self.active_colour = 0
                    if self.white_king.pos & self.black_can_take:
                        self.reverse_move()
                    elif self.black_king.pos & self.white_can_take:
                        self.checkmate()
                else:
                    self.active_colour = 1
                    self.full_move += 1
                    if self.black_king.pos & self.white_can_take:
                        self.reverse_move()   
                    elif self.white_king.pos & self.black_can_take:
                        self.checkmate()
        else: 
            print("WHELP")
        #print(time.time()-s)
    
    def unmake_move(self):
        move = self.recent_moves.pop() # returns false if the stack is empty
        if move:
            out = str(bin(move)[2:].zfill(24)) # normalises the number into a sting containing 24 bits
            
            # converts the string into an array holding all decoded information about the move
            breakdown = [int(out[:4],2), int(out[4:8],2), [(int(out[8:11],2)),(int(out[11:14],2))],
                         [(int(out[14:17],2)),(int(out[17:20],2))], int(out[20:],2)]
            erow,ecol = breakdown[2]
            srow,scol = breakdown[3]
            
            if breakdown[-1] >= 8: # checks if the move is a promotion and 
                piece = self.captured_pieces.pop()
            else:
                piece = self.board[srow,scol]
            
            # updates the gui to show the piece has returned to is origional square 
            self.board[erow,ecol] = piece
            piece.pos = xmpz(0)
            piece.pos[(erow<<3)+ecol] =1
            piece.has_moved -= 1
            self.half_move -= 1
            
            # checks if last move was a double pawn push for en passant
            self.old_passant = self.en_passant
            previous = str(bin(self.recent_moves.peak())[2:].zfill(24))
            if int(previous[20:],2) == 1:
                row,col = (int(previous[8:11],2)),(int(previous[11:14],2))

                self.en_passant = xmpz(2**(((row-1)<<3)+col) if self.half_move % 2 == 1 else 2**(((row+1)<<3)+col))
                
            else:
                self.en_passant =xmpz(0)

            
            if breakdown[0] == 0: # checks if quiet move
                # replaces with empty piece if none taken
                self.board[srow,scol] = pieces.Piece(self,0,srow,scol,piece_type='')

            else:
                cap = self.captured_pieces.pop()
                if breakdown[-1] == 5: # accounts for ep capture when replacing piece
                    if self.half_move % 2 == 0:
                        temp_row = srow + 1
                    else:
                        temp_row = srow -1
                else:
                    temp_row = srow
            
                self.board[temp_row,scol] = cap
                cap.pos=xmpz(0)
                cap.pos[(temp_row<<3)+scol] =1
                if self.half_move % 2 == 0:
                    self.black_pieces = np.append(self.black_pieces,cap)
                    self.black_positions[(temp_row<<3)+scol] = 1
                else:
                    self.white_pieces = np.append  (self.white_pieces,cap)
                    self.white_positions[(temp_row<<3)+scol] = 1
                self.piece_list = np.append(self.piece_list,cap)
                 
                cap.update_legal_moves()
                        
            
            if self.half_move % 2 == 0:
                self.white_positions[(erow<<3)+ecol] = 1
                self.white_positions[(srow<<3)+scol] = 0
                self.active_colour = 1
                
            else:
                self.active_colour = 0 
                self.full_move -= 1
                self.black_positions[(erow<<3)+ecol] = 1
                self.black_positions[(srow<<3)+scol] = 0
            
            piece.update_legal_moves()
            self.move_handler.update_affected_pieces(2**(erow*8+ecol),2**(srow*8+scol))
















    # def convert_for_bot(self):
    #     # array p n b k r q - based of piece number representation
    #     black_pieces = np.array([xmpz(0) for i in range(6)])
    #     white_pieces = np.array([xmpz(0) for i in range(6)])
        
    #     moves = np.array([])
    #     for i in self.piece_list:
    #         if i.legal_moves and i.colour ==self.active_colour:
    #             b= i.legal_moves.bit_scan1(0)
    #             while b != None:
    #                 moves = np.append(moves,[[i.pos,xmpz(1<<b)]])
    #                 b = i.legal_moves.bit_scan1(b+1)
    #         if i.piece >7 :
    #             white_pieces[(i.piece%8) -1] |= i.pos # creates a 64 bit board for each type of piece
    #         elif i.piece > 0:
    #             black_pieces[i.piece - 1] |= i.pos
                     
    #     moves = moves.reshape(int(len(moves)/2),2)
        
    #     self.move_handler.hash = self.transposition.initial_hash([white_pieces,black_pieces])
        
    #     board = [white_pieces,black_pieces,self.available_castle,self.en_passant,self.active_colour]
    #     return board,moves