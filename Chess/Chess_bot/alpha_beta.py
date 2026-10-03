import math as maths
import numpy as np
import gmpy2
import time

class Alpha_Beta:
    def __init__(self,master):
        self.master = master
    
    def search_all_captures(self,alpha, beta):
        if self.thinking_time < (time.time()-self.start_time):
            return self.master.evalute()
        if self.master.terminal():
            return self.master.evaluate() 
        elif self.master.was_capture():
            self.search_all_captures(alpha,beta) 
                        
        if self.master.active_colour: 
            maxEva= -float("infinity")        
            for move in self.master.possible_captures():
                self.master.make_move(move)
                eva= self.search_all_captures(alpha, beta)
                self.master.unmake_move() 
                
                maxEva = max(maxEva, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return maxEva
        
        else:
            minEva= float("infinity")
            for move in self.master.possible_captures():
                self.master.make_move(move)
                eva= self.search_all_captures(alpha, beta)
                self.master.unmake_move()
                
                minEva= min(minEva, eva)   
                beta= min(beta, eva)  
                if beta<=alpha:
                    break          
            return minEva
    
    # recursively makes moves until the maximum depth is reached or a terminal state is reached
    # the retuturns the evaluation of that position
    def alpha_beta(self, depth, alpha, beta):
        if self.thinking_time < (time.time()-self.start_time):
            return self.master.evaluate() 
        
        if self.master.terminal(): # ckecmate/stalemate
                return self.master.evaluate() 
        elif depth == 0 :
            if self.master.was_capture(): # Quiescence Search to avoid horizon affect
               self.search_all_captures() 
            else:
                return self.master.evaluate()
        
        if self.master.active_colour: 
            maxEva= -float("infinity")        
            for move in self.master.possible_moves():
                self.master.make_move(move)
                eva= self.alpha_beta(depth-1,alpha, beta)
                self.master.unmake_move() 
                
                maxEva = max(maxEva, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return maxEva
        
        else:
            minEva= float("infinity")
            for move in self.master.possible_moves():
                self.master.make_move(move)
                eva= self.alpha_beta(depth-1,alpha, beta)
                self.master.unmake_move()
                
                minEva= min(minEva, eva)   
                beta= min(beta, eva)  
                if beta<=alpha:
                    break          
            return minEva 
        
    def get_best_move(self,thinking_time):
        # uses the best move from the previous search to start the next search depth
        # depth increases with each iteration until time has been exceeded
        depth = 1
        self.thinking_time,self.start_time = thinking_time,time.time()
        while (time.time()-self.start_time) < thinking_time:
            best_move,alpha,beta = self.check_old_best()
            alpha,beta,best_move = float('-inf'),float('inf'), None      
            for move in self.master.possible_moves():
                if move == old_best_move:
                    continue
                self.master.make_move(move)
                eva= self.alpha_beta(depth-1,alpha, beta) # calls recursive search
                self.master.unmake_move()  
                
                if self.master.active_colour:
                    if eva > max_eval:
                        max_eval = eval
                        best_move = move
                    alpha = max(alpha, eva)
                else:
                    if eva < min_eval:
                        min_eval = eval
                        best_move = move
                    beta = min(beta, eva)  
            if (time.time()-self.start_time) < thinking_time:
                break                                     
            depth += 1 # iterative deepening 
            old_best_move = best_move # makes sure to return fully completed search
        return old_best_move
    
    def check_old_best(self,move,depth,alpha,beta):
        self.master.make_move(move)
        eva= self.alpha_beta(depth-1,alpha, beta) # calls recursive search
        self.master.unmake_move()  
        
        if self.master.active_colour:
            if eva > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eva)
        else:
            if eva < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eva)

        return best_move,alpha,beta  

