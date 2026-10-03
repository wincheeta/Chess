import tkinter as tk

class WrappingLabel(tk.Label):
    '''a type of Label that automatically adjusts the wrap to the size'''
    def __init__(self, master=None,text="",font =("arial",10), **kwargs):
        tk.Label.__init__(self, master,text=text,font=font,wraplength=800,justify="left",bg="#4b4b4b",fg="white", **kwargs)
        self.bind('<Configure>', lambda e: self.config(wraplength=self.winfo_width()))
 