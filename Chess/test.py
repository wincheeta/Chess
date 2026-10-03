from tkinter import *
import webbrowser

def callback(url):
    webbrowser.open_new(url)

root = Tk()
link1 = Label(root, text="Hyperlink", fg="blue", cursor="hand2")
link1.pack()
link1.bind("<Button-1>", lambda e: callback("http://www.example.com"))

link2 = Label(root, text="Hyperlink", fg="blue", cursor="hand2")
link2.pack()
link2.bind("<Button-1>", lambda e: callback("http://www.example.org"))

root.mainloop()




# import tkinter as tk

# window = tk.Tk()

# white = "white"
# black = "Gray"
# pieces = [["r","n","b","q","k","b","n","r"],["p","p","p","p","p","p","p","p"],['','','','','','','',''],['','','','','','','',''],['','','','','','','',''],['','','','','','','',''],["P","P","P","P","P","P","P","P"],["R","N","B","Q","K","B","N","R"]] #represent
# for row in range(8):
#     for col in range(8):
#         squares = tk.Button(window, bg= white if (row+col)%2==0 else black, width=5,height=3 )
#         squares.grid(row=row, column=col)

# print(bin(65280))        

# window.mainloop()


# print(bin(11))