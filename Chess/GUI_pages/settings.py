import tkinter as tk
from tkinter import messagebox 
from Piece_classes import Pawn
import webbrowser
import re

class Settings_page(tk.Frame):
    def __init__(self,master):
        super().__init__(master,bg="#4b4b4b")
        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 15)
        self.grid_columnconfigure(0, weight = 1)

        header = tk.Label(self, text = "Settings", font = ("felix titling",20),bg="#5b5b5b",fg = "white",borderwidth=0)
        header.grid(row=0,column=0,sticky="nesw") 
        
        # frame to hold the main body of the page to keep it seperate from the header
        frame = tk.Frame(self, bg ="#4b4b4b")
        frame.grid(row=1,column=0,sticky="nesw")
        
        # a unique frame to contain the save/reset buttons so they can be formatted uniquelly
        button_frame = tk.Frame(self, bg ="#4b4b4b")
        button_frame.grid(row=2, column = 0)
        
        save = tk.Button(button_frame, text = "SAVE",font = ("felix titling",20),bg="gray",borderwidth=0, command = self.save_settings)
        save.pack(side="left")
        reset = tk.Button(button_frame, text = "RESET",font = ("felix titling",20),bg="gray",borderwidth=0, command = self.reset_settings)
        reset.pack(side="left")
        
        CheckVar1 = tk.IntVar()
        activate_bot = tk.Checkbutton(frame, bg = "#4b4b4b", fg="red",font = ("arial",15), text = "Play against bot", variable = CheckVar1, onvalue = 1, offvalue = 0).pack()
        
        
        items = ("ascii","periodic","hidden","secret","classic")
        # datatype of menu text 
        self.clicked = tk.StringVar() 
        self.clicked.set( "ascii" )
        
        self.piece_types = tk.OptionMenu(frame,self.clicked, *items, )
        self.piece_types.pack(pady=10)
        
        #self.colour_scheme = {"white":"#e2bd8d","black":"#5e2496"}
        
        self.white_colour = tk.Text(frame,height = 1, width = 30, font=("felix titling", 15))
        self.black_colour = tk.Text(frame,height = 1, width = 30, font=("felix titling", 15))
        self.white_colour.insert(tk.END, "#e2bd8d")
        self.black_colour.insert(tk.END, "#5e2496")
        self.white_colour.pack(pady=5)
        self.black_colour.pack(pady=5)
        
        link = tk.Label(frame, text="Use a colour picker like this to help", bg= "#4b4b4b",fg="#86CDFF", cursor="hand2")
        link.pack(pady=5)
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://htmlcolorcodes.com/color-picker/"))#https://stackoverflow.com/questions/23482748/how-to-create-a-hyperlink-with-a-label-in-tkinter
        
        self.example_board = Temp_board(frame,{"white":"#5e2496","black":"#e2bd8d"})
        self.example_board.pack(pady=60)
        
        for row in range(3):
            for col in range(3):
                tk.Frame(self.example_board, bg=self.white_colour.get(1.0, "end-1c")  if (row+col)%2==1 else self.black_colour.get(1.0, "end-1c") ,width=100, height=100, borderwidth=4).grid(row=row,column=col)
        
        self.example_pawn = Example_pawn(self.example_board,self.clicked.get())
        self.example_pawn.grid(row=2,column=1)


    def check_colour(self,colour):
        colour_pattern = re.compile(
            r'^\s*#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\s*$'
        )
        return bool(colour_pattern.match(colour))
    
    # applies the settings input to the board and updates the example board to reflect the new state
    def save_settings(self):
        if self.check_colour(self.white_colour.get(1.0, "end-1c")) and self.check_colour(self.black_colour.get(1.0, "end-1c")):
            board = self.master.frames["Play"]
            board.piece_type = self.clicked.get()
            board.colour_scheme = [self.white_colour.get(1.0, "end-1c"),self.black_colour.get(1.0, "end-1c")]
            self.example_board.piece_type = self.clicked.get()
            self.example_pawn.destroy()
            self.example_pawn = Example_pawn(self.example_board,self.clicked.get())
            self.example_pawn.grid(row=2,column=1)
            
            squares= 0
            for i in self.example_board.grid_slaves():
                row,col = squares %3,squares//3
                i.configure(bg=self.white_colour.get(1.0, "end-1c")  if (row+col)%2==0 else self.black_colour.get(1.0, "end-1c") )
                squares +=1
            
            tk.messagebox.showinfo(title="SAVED", message="Settings Saved!")
        else:
            tk.messagebox.showinfo(title="ERROR", message="invalid settings input")
        
    # returns the settings to their default value but doesn't save
    def reset_settings(self):
        self.white_colour.delete(1.0,"end")
        self.white_colour.insert(tk.END, "#e2bd8d")
        self.black_colour.delete(1.0,"end")
        self.black_colour.insert(tk.END, "#5e2496")
        self.example_board.colour_scheme = {"white":"#5e2496","black":"#e2bd8d"}
        self.example_board.piece_type = "ascii"
        

        self.clicked.set( "ascii" )


class Temp_board(tk.Frame):
    def __init__(self,frame,colours):
        super().__init__(frame, height = 240, width = 240)
        self.colour_scheme = colours
        self.black_positions = 0
        self.white_positions = 0
        self.white_pieces = []
        self.black_pieces = []
        self.piece_list = []
        self.border_width = 0
        self.active_colour = "w"
        self.en_passant = 0
        self.piece_type = "ascii"
        self.bpawn = 1
        self.wpawn = 9
        
        
class Example_pawn(Pawn.Pawn):
    def __init__(self,master,type):
        super().__init__(master,9,2,1,type)
    