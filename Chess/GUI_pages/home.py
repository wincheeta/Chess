import tkinter as tk
from GUI_pages import wrap

 
class Home_page(tk.Frame):
    def __init__(self,master):
        self.master = master
        super().__init__(master,bg="#4b4b4b") 

        header = tk.Label(self, text = "CHESSCAPE", font = ("felix titling",20),bg="#5b5b5b",fg = "white",borderwidth=0)
        header.grid(row=0,column=0,sticky="nesw",columnspan=2)
        
        # frame to hold the main body of the page to keep it seperate from the header
        frame = tk.Frame(self, bg ="#4b4b4b")
        frame.grid(row=1,column=0, columnspan=2, sticky="nesw")
        tk.Frame(frame, bg = "#4b4b4b", height = 50).pack(anchor="center")
        tk.Button(frame,bg = "#E9E9E9",fg ="black",width=20, height= 2, font= ("felix titling",20),text = "play", command = lambda : (self.master.show_frame("Play"), self.master.frames["Play"].create_board(),self.master.lastpage.append("Home"))).pack(anchor="center",pady=50)
        tk.Button(frame,bg = "#E9E9E9",fg ="black",width=15 ,height= 2, font= ("felix titling",20),text = "Settings", command = lambda : (self.master.show_frame("Settings"),self.master.lastpage.append("Home"))).pack(anchor="center",pady=0)
        
        # text for the tutorial of the program
        tutorial_text = "This software is a chess game for you to play against friends or against the in built bot: Rook-ie.\n\nTo start a game simply click the play button above and you will be navigated to the play page with a board waiting for you.\nTo move the pieces you simply just drag and drop them to the square you wish to move them to using your mouse left click. Whilst making a move squares around the piece will highlight to show all the places that this piece can legally move to.\nIf you ever make a move you aren't happy with, the back arrow in the bottom left corner of the board is a button which takes back your most recent move and allows you to make a difference once.\nIf you would like to customise the board in settings you can select from a dropdown of piece appearances by clicking the piece name or you can change the colour of the squares on the board by using the two input fields to input RGB colour codes.\nIn order to enable Rook-ie just go into settings and tick the enable bot button.\nOnce you're happy with the settings click save and the preview in the page will update to show you what the board should look like. To play a game with these settings just start a new game in the play tab by clicking play."
        
        tutorial = wrap.WrappingLabel(frame, text = tutorial_text, font = ("arial",15) ) 
        tutorial.pack(expand=True, fill=tk.X,anchor="nw",padx=100,pady=100)
        
        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 8)
        self.grid_rowconfigure(2, weight = 8) 
        self.grid_columnconfigure(0, weight = 1)
        self.grid_columnconfigure(1, weight = 1)

        
        
        