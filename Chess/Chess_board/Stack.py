import numpy as np
class Stack:
    def __init__(self):
        self.data = np.array([],int)

    def __str__(self):
        return f"{self.data}"
    
    # adds a new element to the top of the stack
    def push(self,item):
        self.data = np.append(self.data,item)
    
    # removes the to value from the stack and returns it
    def pop(self):
        if not self.is_empty():
            out = self.data[-1]
            self.data = self.data[:-1] if len(self.data)>1 else np.array([],int)
            return out
        return False
    
    # returns the top value from the stack without removing it
    def peak(self):
        if not self.is_empty():
            return self.data[-1]
        return 0
        
    #checks if the stack is empty -> cannot pop any data
    def is_empty(self):
        return( len(self.data) == 0)

    #returns the number of items in the stack
    def length(self):
        return len(self.data)
    
    def convert_to_algebraic(self,move):
        binary_reversed = {7: 'h', 6: 'g', 5: 'f', 4: 'e', 3: 'd', 2: 'c', 1: 'b', 0: 'a'}
        pieces = {1: '', 2: 'n', 3: 'b', 5: 'r', 6: 'q', 4: 'k', 9: '', 10: 'N', 11: 'B', 13: 'R', 14: 'Q', 12: 'K', 0: '-'}
        
        temp = int(move >> 4) % 64
        square = binary_reversed[temp%8]+str(8-temp//8)
        if move >1048576: # a piece has been captured
            return pieces[(move>>16)%16]+ "x" + square  
        return pieces[(move>>16)%16] + square


 
        
        # pieces = {1: "p", 2: 'n', 3: 'b', 5: 'r', 6: 'q', 4: 'k', 9: 'P', 10: 'N', 11: 'B', 13: 'R', 14: 'Q', 12: 'K', 0: 'nothing'}
        # binary_reversed = {7: 'h', 6: 'g', 5: 'f', 4: 'e', 3: 'd', 2: 'c', 1: 'b', 0: 'a'}
        # types = {0: 'quiet', 1: 'double', 2: 'king-side', 3: 'queen-side', 4: 'capture', 5: 'ep-capture', 8: 'n-promo', 9: 'b-promo', 10: 'r-promo', 11: 'q-promo', 12: 'n-promo-capture', 13: 'b-promo-capture', 14: 'r-promo-capture', 15: 'q-promo-capture'}
        
        # out = str(bin(self.data[-1])[2:].zfill(24))
        # sentence = pieces[int(out[:4],2)]+" was captured by "+ pieces[int(out[4:8],2)]+ " moving from "+ binary_reversed[(int(out[11:14],2))]+str(8-(int(out[8:11],2)))+ " to "+ binary_reversed[(int(out[17:20],2))]+str(8-(int(out[14:17],2)))+ " as " +types[int(out[20:],2)]
        # return sentence
        
        #for i in self.data:
            #temp.append(self.convert_to_algebraic(i))
            #temp.append(bin(i)[2:].zfill(24))