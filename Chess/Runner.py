from GUI_pages import master,home,Rules,play,settings    

# runner that collects all GUI elements to assembles them into the interface
window = master.Window()

#creates a cpeceific instance of the chesspage so it can be called later
chess = play.Chess_game(window,"ascii")

# adds all the pages to the navigation bar
window.add_frame(home.Home_page(window),"Home")
window.add_frame(Rules.Rules(window),"Rules")
window.add_frame(chess,"Play")
window.add_frame(settings.Settings_page(window),"Settings")

window.show_frame("Play")
chess.create_board()

window.mainloop() 



"""
Using SIMD instructions to do bit-wise operations on multiple bit-boards at the same time.
Using Kogge-Stone Generators when calculating slider moves for multiple pieces at the same time (e.g. calculating king danger squares or pin rays).
Using the o^(o-2r) trick when calculating moves for individual sliding pieces, using the intel PSHUFB instruction to do byte-swaps on 128-bit registers to calculate diagonal attacks.

use gmpy2 for bitwise???? 1/ten mil of a second to update
V good - based in c
well kept doccumentation

import matplotlib.pyplot as plt
plot graph perfomance?

"""
