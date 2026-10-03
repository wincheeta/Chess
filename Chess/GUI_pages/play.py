import tkinter as tk
from Chess_board import board

class Chess_game(tk.Frame):
    def __init__(self,master,piece_type):
        super().__init__(master,bg="#4b4b4b")
        self.chessboard = None
        self.master = master
        
        self.piece_type = piece_type
        self.colour_scheme = ["#e2bd8d","#5e2496"]
        
        # play and resign buttons
        tk.Button(self,width=10, text = "Play", bg = "#E9E9E9", borderwidth=0,font = ("felix titling",20), command = self.create_board).pack(side="left", padx=100)
        tk.Button(self,width=10, text = "Resign", bg = "red",borderwidth=0,font = ("felix titling",20), command = self.delete_board).pack(side="right", padx=100)
        
        # creates buttons and text field for the FEN import
        self.import_fen_text = tk.Text(self,height = 1, width = 60,borderwidth=0,font = ("arial",15) )
        self.import_fen_button = tk.Button(self,text="import board using FEN",borderwidth=0,font = ("felix titling",15), command=self.import_board)
        self.import_fen_text.place(relx=0.5,rely=0.5, anchor="s")
        self.import_fen_button.place(relx=0.5,rely=0.57, anchor="s")
        
    # creates a new inscance of the board and delets the old one if it exists
    def create_board(self,FEN="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",stack=[], game_type="p"):#"#e2bd8d","#421e00"  libs #300659
        if self.chessboard: 
            self.chessboard.destroy()
        
        self.chessboard = board.chessboard(self,FEN,stack,self.piece_type,game_type,self.colour_scheme)

        #centers chesboard in the page
        self.chessboard.place(relx=0.5,rely=0.5, anchor="center")
    
    def delete_board(self):
        self.last_game = self.chessboard.destroy()
        self.chessboard == None
        
    def import_board(self):
        inp = self.update_board.get(1.0, "end-1c") 
        self.create_board(FEN=str(inp))
  
    def random_move(self):
        while self.CheckVar1:
            self.chessboard.make_random_moves(1)
            