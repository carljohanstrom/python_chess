#!/usr/bin/env python
import copy
import sys


class Piece :
    def __init__(self, name=None, color=None) :
        self.color = color
        self.value = 0
        self.name = name
        self.unmoved = True
        if name == "pawn" :
            self.value = 1
            self.color = color
            if color=="white" :
                self.directions = [(-1,0)]
            else :
                self.directions = [(1,0)]
            self.range = 1 # this range is extended to 2 programatically when pawn has not yet been moved
        elif name == "knight" :
            self.value = 3
            self.color = color
            self.directions = [(1,2),(1,-2),(2,1),(2,-1),(-1,2),(-1,-2),(-2,1),(-2,-1)]
            self.range = 1
        elif name == "bishop" :
            self.value = 3
            self.color = color
            self.directions = [(1,1),(-1,-1),(1,-1),(-1,1)]
            self.range = 7
        elif name == "rook" :
            self.value = 5
            self.color = color
            self.directions = [(0,1),(1,0),(0,-1),(-1,0)]
            self.range = 7
        elif name == "queen" :
            self.value = 9
            self.colot = color
            self.directions = [(1,1),(-1,-1),(1,-1),(-1,1),(0,1),(1,0),(0,-1),(-1,0)]
            self.range = 7
        elif name == "king" :
            self.value = 1000
            self.colot = color
            self.directions = [(1,1),(-1,-1),(1,-1),(-1,1),(0,1),(1,0),(0,-1),(-1,0)]
            self.range = 1

    def __str__(self) :
        return self.color + " " + self.name


class Board :
    def __init__(self, old_board = []) :
        self.board = old_board

    def standard_setup(self) :
        pieces = ["rook","knight","bishop","queen","king","bishop","knight","rook"]
        pawns = ["pawn"] * 8
        self.board.append([Piece(p, "black") for p in pieces])
        self.board.append([Piece(p, "black") for p in pawns])
        for row in [2,3,4,5] :
            self.board.append([None for _ in range(8)])
        self.board.append([Piece(p, "white") for p in pawns])
        self.board.append([Piece(p, "white") for p in pieces])

    def piece_at_pos(self, row, col) :
        return self.board[row][col]

    def make_move(self, move) :
        # move is expected to contain two tuples, like (y,x),(y,x)
        if move==None : 
            return
        from_row, from_col = move[0]
        to_row, to_col = move[1]
        piece = self.board[from_row][from_col]
        self.board[from_row][from_col] = None
        piece.unmoved = False
        self.board[to_row][to_col] = piece
        #TBD: castling
        #TBD: passant
        #TBD: pawn promotion

    def moves_for_piece(self, row, col) :
        piece = self.board[row][col]
        reps = piece.range
        if piece.name == "pawn" and piece.unmoved :
            reps = 2
        moves = []
        for d in piece.directions :
            for p in range(1,reps+1) :
                y, x = d[0]*p+row, d[1]*p+col
                if y<0 or y>7 or x<0 or x>7 : 
                    break
                if piece.name == "pawn" and p == 1 : # only for pawn, but not for intial two step move forward
                    if x<7 and self.board[y][x+1] != None and self.board[y][x+1].color != piece.color :
                        moves.append((y,x+1))
                    if x>0 and self.board[y][x-1] != None and self.board[y][x-1].color != piece.color :
                        moves.append((y,x-1))
                    # TBD: implement passant
                if self.board[y][x]==None : 
                    moves.append((y,x))
                    continue
                if self.board[y][x].color == piece.color :
                    break
                if self.board[y][x].color != piece.color and piece.name != "pawn" : 
                    moves.append((y,x))
                    break
        return moves    
        #TBD: castling
        #TBD: passant

    def all_pieces(self, color) :
        pieces = []
        for row in range(8) :
            for col in range(8) :
                piece = self.board[row][col]
                if piece == None :
                    continue
                if piece.color == color :
                    pieces.append((piece,row,col))
        return pieces

    def all_moves_for_all_pieces(self, color) :
        all_moves = []
        for (piece, row, col) in self.all_pieces(color) :
            moves = self.moves_for_piece(row, col)
            for m in moves :
                all_moves.append( (piece, (row,col), m) )
        return all_moves

    def value(self, calculate_for_color) :
        score = 0
        for row in range(8) :
            for col in range(8) :
                piece = self.board[row][col]
                if piece != None :
                    if piece.color == calculate_for_color :
                        score += piece.value
                        score += .05*row if piece.color == "black" else 0.05*(7-row)
                    else :                    
                        score -= piece.value
                        score -= .05*row if piece.color == "black" else 0.05*(7-row)
        return score
        # TBD: could optimize this a lot by keeping track of the score and just adjusting by how much each move modifies the score

    def printout(self, side) :
        print("       "+"      ".join(list("abcdefgh")[::(-1 if side=="black" else 1)]))
        for y,row in enumerate(self.board[::(-1 if side=="black" else 1)]) :
            y = y if side=="black" else 7-y 
            print ("   "+"+------+------+------+------+------+------+------+------+")
            line = ""
            for z in [1,2] :
                if z==1 :
                    line = (" "+str(y+1)+" | ")
                else :
                    line = "   | "
                for piece in row[::(-1 if side=="black" else 1)] : 
                    if piece == None :
                        line += "    "
                    else :
                        lettercode = piece.name[0:4] if z==2 else "    "
                        if piece.color == "black" :
                            line += "\033[7m"+lettercode+"\033[m"
                        else :
                            line += lettercode
                    line += " | "
                if z==1 :
                    line += (str(y+1))
                print(line)
        print ("   "+"+------+------+------+------+------+------+------+------+")
        print("       "+"      ".join(list("abcdefgh")[::(-1 if side=="black" else 1)]))



# FUNCTIONS

def is_legal(move, board, player) :
    if move == None :
        return False
    from_row, from_col = move[0]
    to_row, to_col = move[1]
    piece_to_move = board.piece_at_pos(from_row, from_col)
    if piece_to_move==None :
        print("Illegal move. No playing piece in that square.")
        return False
    if piece_to_move.color != player : 
        print("Illegal move. Cannot move opponents piece.")
        return False
    to_square = board.piece_at_pos(to_row, to_col)
    if to_square != None and to_square.color == player : 
        print("Illegal move. You already have a piece there.")
        return False
    allowed_moves = board.moves_for_piece(from_row, from_col)
    if (to_row,to_col) not in allowed_moves :
        print("Illegal move. Cannot go there.")
        return False
    return True
    #TBD: castling
    #TBD: passant


def to_alfanum(t) :
    return chr(t[1]+65)+str(8-t[0])


def parse_move(nnnn) :
    if len(nnnn)!=4 :
        return None
    if nnnn[0] not in ('abcdefgh') or nnnn[1] not in ('12345678')or nnnn[2] not in ('abcdefgh')or nnnn[3] not in ('12345678'): 
        return None
    return ((56-ord(nnnn[1]),ord(nnnn[0])-97) , (56-ord(nnnn[3]),ord(nnnn[2])-97)) #from (row,col) to (row,col)
    #TBD: pawn promotion --> 'q'|'r'|'b'|'n'
    #TBD: castling


def minmax(b, t, max_ply, ply) :  
    maximizing = (ply%2!=0)
    opt_value = float(0)
    if maximizing :
        opt_value = float('-inf')
    else :
        opt_value = float('+inf')
    opt_move = None 

    if ply >= max_ply :
        return None, b.value(t)

    else :
        ply+=1    
        move_list = b.all_moves_for_all_pieces(t)
        t = "white" if t=="black" else "black"
        for mv in move_list :
            next_ply_board = Board(copy.deepcopy(b.board)) # TBD: optimize: only need to copy whole array, not Piece objects
            next_ply_board.make_move( (mv[1],mv[2]) )
            om,ov = minmax(next_ply_board, t, max_ply, ply) # Recursion here
            if maximizing : 
                if ov > opt_value :
                    opt_move, opt_value = mv, ov
            else :
                if ov < opt_value :
                    opt_move, opt_value = mv, ov
        return opt_move, opt_value


# MAIN

# SETUP
playercolor = ""
while playercolor!="black" and playercolor!="white" : 
    playercolor = input("Play black or white? ").lower()
computercolor = "black" if playercolor == "white" else "white"
ply_depth = 3
checkmate = False
turn = "white"
move = None

board = Board()
board.standard_setup()

# PLAY
while not checkmate :
    board.printout(playercolor)
    print("Value for playercolor:",board.value(playercolor))
    move = None
    if turn == playercolor :
        while not is_legal(move, board, playercolor) :
            user_input = input("Move? ").lower().strip('- ,.:;>/to_')
            move = parse_move(user_input)
    else :
        print("Computer is thinking...")
        move, calc_value = minmax(board, computercolor, ply_depth, 0)
        print("Makes", to_alfanum(move[1])+to_alfanum(move[2]), "move with", move[0])
        move = move[1],move[2]
    board.make_move(move)
    turn = "white" if turn=="black" else "black"
print("CHECKMATE!")






# "row" -> "rank" 
# "col" -> "file"
