import tkinter as tk
from GUI_pages import wrap
class Rules(tk.Frame):
    def __init__(self,master):
        super().__init__(master,bg="#4b4b4b")
        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 15)
        self.grid_columnconfigure(0, weight = 50)
        

        header = tk.Label(self, text = "Rules",font = ("felix titling",20),bg="#5b5b5b",fg = "white",borderwidth=0)
        header.grid(row=0,column=0,sticky="nesw")

        container = tk.Canvas(self,bg="#4b4b4b")
        container.grid(row=1,column=0, sticky="nesw")

        # text contained in the window
        info_text = "Chess Rules Summary:\nBoard Setup:\n\n•The chessboard consists of 64 squares arranged in an 8x8 grid.\n•Each player starts with 16 pieces: one king, one queen, two rooks, two knights, two bishops, and eight pawns.\n\nObjective:\n•The primary goal is to checkmate your opponent's king. This means putting the king in a position where it is under attack and has no legal moves to escape the threat.\n\nPiece Movement:\nEach type of piece moves differently.\n•The king moves one square in any direction.\n•The queen moves diagonally, horizontally, or vertically any number of squares.\n•Rooks move horizontally or vertically any number of squares.\n•Bishops move diagonally any number of squares.\n•Knights move in an 'l' shape - two squares in one direction and one square perpendicular to that.\n\nPawns:\n•Pawns move forward one square but capture diagonally.\n•On their first move, pawns have the option to move two squares forward.\n•Pawns can be promoted to any other piece when reaching the eighth rank.\n\nSpecial Moves:\n•Castling involves moving the king and one of the rooks simultaneously, under certain conditions.\n•En passant allows a pawn to capture an opponent's pawn that has moved two squares forward from its starting position.\n\nCheck and Checkmate:\n•When a king is under direct threat of capture, it is in check.\n•Checkmate occurs when the king is in check, and there is no legal move to escape the threat.\n\nChess Tips for Beginners:\n\nControl the Center:\nTry to control the central squares of the board. This provides more mobility for your pieces and strategic advantages.\n\nDevelop Your Pieces:\nBring your knights and bishops into play early. Avoid moving the same piece multiple times in the opening.\n\nProtect Your King:\nCastle early to safeguard your king. This move connects your rooks and puts the king in a safer position.\n\nThink Ahead:\nAnticipate your opponent's moves and plan your strategy accordingly. Consider the consequences of each move.\n\nPawn Structure:\nBe mindful of your pawn structure. Avoid creating weaknesses that can be exploited by your opponent.\n\nPractice Tactics:\nLearn basic tactics such as forks, pins, and skewers. Solving tactical puzzles can improve your ability to spot these opportunities.\n\nTime Management:\nManage your time wisely during a game. Don't rush, but also avoid spending too much time on one move.\n\n Enjoy your games and learn from each experience!"
        
        # uses wrap label to make sure that the text adapts to fit the window
        info = wrap.WrappingLabel(container, text = info_text) 
        info.pack(expand=True, fill=tk.X,anchor="nw")


