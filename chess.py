#!/usr/bin/env python3

import copy
import sys


class Piece:
    def __init__(self, name=None, color=None):
        self.name = name
        self.color = color
        self.value = 0
        self.startrank = -1
        self.unmoved = True
        if name == "pawn":
            self.value = 1
            if color == "white":
                self.directions = [(-1, 0)]
                self.startrank = 6
            else:
                self.directions = [(1, 0)]
                self.startrank = 1
            self.range = 1
        elif name == "knight":
            self.value = 3
            self.directions = [(1, 2), (1, -2), (2, 1), (2, -1), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
            self.range = 1
        elif name == "bishop":
            self.value = 3
            self.directions = [(1, 1), (-1, -1), (1, -1), (-1, 1)]
            self.range = 7
        elif name == "rook":
            self.value = 5
            self.directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
            self.range = 7
        elif name == "queen":
            self.value = 9
            self.color = color
            self.directions = [(1, 1), (-1, -1), (1, -1), (-1, 1), (0, 1), (1, 0), (0, -1), (-1, 0)]
            self.range = 7
        elif name == "king":
            self.value = 1000
            self.color = color
            self.directions = [(1, 1), (-1, -1), (1, -1), (-1, 1), (0, 1), (1, 0), (0, -1), (-1, 0)]
            self.range = 1

    def __str__(self):
        return f"{self.color} {self.name}"


class Board:
    def __init__(self, a_board=None):
        if a_board is None:
            self.board = []
        else:
            # copy rows but keep piece objects (shallow copy of pieces)
            self.board = [list(row) for row in a_board]
        self.en_passant_target = None  # square where en-passant capture can land
        self.en_passant_victim = None  # coordinate of pawn that can be captured en-passant

    def standard_setup(self):
        pieces = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"]
        pawns = ["pawn"] * 8
        self.board = []
        self.board.append([Piece(p, "black") for p in pieces])
        self.board.append([Piece(p, "black") for p in pawns])
        for _ in range(4):
            self.board.append([None] * 8)
        self.board.append([Piece(p, "white") for p in pawns])
        self.board.append([Piece(p, "white") for p in pieces])

    def piece_at_pos(self, row, col):
        return self.board[row][col]

    def copy(self):
        nb = Board(self.board)
        nb.en_passant_target = self.en_passant_target
        nb.en_passant_victim = self.en_passant_victim
        return nb

    def find_king(self, color):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p is not None and p.name == 'king' and p.color == color:
                    return (r, c)
        return None

    def is_square_attacked(self, row, col, by_color):
        # any opponent piece that has (row,col) among its moves attacks that square
        for (piece, r, c) in self.all_pieces(by_color):
            # generate moves for piece without filtering for leaving king in check
            opts = self._raw_moves_for_piece(r, c)
            if (row, col) in opts:
                return True
        return False

    def is_in_check(self, color):
        kingpos = self.find_king(color)
        if kingpos is None:
            return False
        opp = 'white' if color == 'black' else 'black'
        return self.is_square_attacked(kingpos[0], kingpos[1], opp)

    def would_leave_king_in_check(self, move, color):
        nb = self.copy()
        nb.make_move(move)
        return nb.is_in_check(color)

    def make_move(self, move):
        """
        Executes a move and returns (moved_piece, (to_row,to_col)) or None.
        Handles en-passant and castling (basic rules), sets en_passant target for double-step pawns.
        Castling disallowed if king is in/through/out into check.
        """
        if move is None:
            self.en_passant_target = None
            self.en_passant_victim = None
            return None
        (from_row, from_col), (to_row, to_col) = move
        piece = self.board[from_row][from_col]
        if piece is None:
            self.en_passant_target = None
            self.en_passant_victim = None
            return None

        # --- Castling detection and validation ---
        if piece.name == "king" and abs(to_col - from_col) >= 2 and piece.unmoved:
            # cannot castle if currently in check
            if self.is_in_check(piece.color):
                return None
            # king-side
            if to_col > from_col:
                # find rook to the right
                rook_col = None
                for c in range(7, from_col, -1):
                    r = self.board[from_row][c]
                    if isinstance(r, Piece) and r.name == "rook":
                        rook_col = c
                        rook = r
                        break
                if rook_col is not None and rook.unmoved:
                    # squares between must be empty
                    between = [self.board[from_row][c] for c in range(from_col + 1, rook_col)]
                    if all(x is None for x in between):
                        # squares king passes through
                        pass_squares = [(from_row, from_col + 1), (from_row, from_col + 2)]
                        opp = 'white' if piece.color == 'black' else 'black'
                        if any(self.is_square_attacked(r, c, opp) for (r, c) in pass_squares):
                            return None
                        # perform castling
                        self.board[to_row][to_col] = piece
                        self.board[from_row][from_col] = None
                        self.board[from_row][to_col - 1] = rook
                        self.board[from_row][rook_col] = None
                        piece.unmoved = False
                        rook.unmoved = False
                        self.en_passant_target = None
                        self.en_passant_victim = None
                        return (piece, (to_row, to_col))
            else:
                # queen-side
                rook_col = None
                for c in range(0, from_col):
                    r = self.board[from_row][c]
                    if isinstance(r, Piece) and r.name == "rook":
                        rook_col = c
                        rook = r
                        break
                if rook_col is not None and rook.unmoved:
                    between = [self.board[from_row][c] for c in range(rook_col + 1, from_col)]
                    if all(x is None for x in between):
                        pass_squares = [(from_row, from_col - 1), (from_row, from_col - 2)]
                        opp = 'white' if piece.color == 'black' else 'black'
                        if any(self.is_square_attacked(r, c, opp) for (r, c) in pass_squares):
                            return None
                        self.board[to_row][to_col] = piece
                        self.board[from_row][from_col] = None
                        self.board[from_row][to_col + 1] = rook
                        self.board[from_row][rook_col] = None
                        piece.unmoved = False
                        rook.unmoved = False
                        self.en_passant_target = None
                        self.en_passant_victim = None
                        return (piece, (to_row, to_col))

        # --- En-passant capture detection ---
        if piece.name == "pawn" and self.en_passant_target is not None and (to_row, to_col) == self.en_passant_target and self.board[to_row][to_col] is None:
            vr, vc = self.en_passant_victim
            self.board[vr][vc] = None

        # --- Normal move: set en-passant target for double-step pawns ---
        if piece.name == "pawn" and abs(to_row - from_row) == 2:
            passed_row = (from_row + to_row) // 2
            self.en_passant_target = (passed_row, from_col)
            self.en_passant_victim = (to_row, from_col)
        else:
            self.en_passant_target = None
            self.en_passant_victim = None

        piece.unmoved = False
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        return (piece, (to_row, to_col))

    def _raw_moves_for_piece(self, row, col):
        # same as previous moves_for_piece but without legality filtering
        piece = self.board[row][col]
        if piece is None:
            return []
        reps = piece.range
        if piece.name == "pawn" and row == piece.startrank and piece.unmoved:
            reps = 2
        moves = []
        for d in piece.directions:
            for p in range(1, reps + 1):
                y, x = d[0] * p + row, d[1] * p + col
                if y < 0 or y > 7 or x < 0 or x > 7:
                    break
                if piece.name == "pawn" and p == 1:
                    # captures (normal)
                    if x - 1 >= 0:
                        if self.board[y][x - 1] is not None and self.board[y][x - 1].color != piece.color:
                            moves.append((y, x - 1))
                        if self.en_passant_target == (y, x - 1):
                            moves.append((y, x - 1))
                    if x + 1 <= 7:
                        if self.board[y][x + 1] is not None and self.board[y][x + 1].color != piece.color:
                            moves.append((y, x + 1))
                        if self.en_passant_target == (y, x + 1):
                            moves.append((y, x + 1))
                if self.board[y][x] is None:
                    moves.append((y, x))
                    continue
                if self.board[y][x].color == piece.color:
                    break
                if self.board[y][x].color != piece.color and piece.name != "pawn":
                    moves.append((y, x))
                    break
        return moves

    def moves_for_piece(self, row, col):
        # returns legal moves (do not leave own king in check)
        raw = self._raw_moves_for_piece(row, col)
        piece = self.board[row][col]
        if piece is None:
            return []
        legal = []
        for to in raw:
            mv = ((row, col), to)
            if not self.would_leave_king_in_check(mv, piece.color):
                legal.append(to)
        return legal

    def all_pieces(self, color):
        pieces = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece is None:
                    continue
                if piece.color == color:
                    pieces.append((piece, row, col))
        return pieces

    def all_moves_for_all_pieces(self, color):
        all_moves = []
        for (piece, row, col) in self.all_pieces(color):
            moves = self.moves_for_piece(row, col)
            for m in moves:
                all_moves.append((piece, (row, col), m))
        return all_moves

    def value(self, calculate_for_color):
        score = 0
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece is not None:
                    if piece.color == calculate_for_color:
                        score += piece.value
                        score += 0.05 * row if piece.color == "black" else 0.05 * (7 - row)
                    else:
                        score -= piece.value
                        score -= 0.05 * row if piece.color == "black" else 0.05 * (7 - row)
        return score

    def printout(self, side):
        print("       " + "      ".join(list("abcdefgh")[::(-1 if side == "black" else 1)]))
        for y, row in enumerate(self.board[::(-1 if side == "black" else 1)]):
            y = y if side == "black" else 7 - y
            print("   " + "+------+------+------+------+------+------+------+------+")
            for z in [1, 2]:
                line = (" " + str(y + 1) + " | ") if z == 1 else "   | "
                for piece in row[::(-1 if side == "black" else 1)]:
                    if piece is None:
                        line += "    "
                    else:
                        lettercode = piece.name[0:4] if z == 2 else "    "
                        if piece.color == "black":
                            line += "\033[7m" + lettercode + "\033[m"
                        else:
                            line += lettercode
                    line += " | "
                if z == 1:
                    line += (str(y + 1))
                print(line)
        print("   " + "+------+------+------+------+------+------+------+------+")
        print("       " + "      ".join(list("abcdefgh")[::(-1 if side == "black" else 1)]))


# FUNCTIONS

def is_legal(move, board, player):
    if move is None:
        return False
    from_row, from_col = move[0]
    to_row, to_col = move[1]
    piece_to_move = board.piece_at_pos(from_row, from_col)
    if piece_to_move is None:
        print("Illegal move. No playing piece in that square.")
        return False
    if piece_to_move.color != player:
        print("Illegal move. Cannot move opponents piece.")
        return False
    to_square = board.piece_at_pos(to_row, to_col)
    if to_square is not None and to_square.color == player:
        print("Illegal move. You already have a piece there.")
        return False
    allowed_moves = board.moves_for_piece(from_row, from_col)
    if (to_row, to_col) not in allowed_moves:
        print("Illegal move. Cannot go there or move leaves king in check.")
        return False
    return True


def to_alfanum(t):
    return chr(t[1] + 97) + str(8 - t[0])


def parse_move(nnnn):
    if len(nnnn) != 4:
        return None
    if nnnn[0] not in ("abcdefgh") or nnnn[1] not in ("12345678") or nnnn[2] not in ("abcdefgh") or nnnn[3] not in ("12345678"):
        return None
    return ((56 - ord(nnnn[1]), ord(nnnn[0]) - 97), (56 - ord(nnnn[3]), ord(nnnn[2]) - 97))


def minmax(b, t, max_ply, ply):
    maximizing = (ply % 2 != 0)
    opt_value = float(0)
    if maximizing:
        opt_value = float("-inf")
    else:
        opt_value = float("+inf")
    opt_move = None

    if ply >= max_ply:
        return None, b.value(t)

    ply += 1
    move_list = b.all_moves_for_all_pieces(t)
    t = "white" if t == "black" else "black"
    for mv in move_list:
        next_ply_board = Board(b.board)
        # copy en-passant state for accurate simulation
        next_ply_board.en_passant_target = b.en_passant_target
        next_ply_board.en_passant_victim = b.en_passant_victim
        next_ply_board.make_move((mv[1], mv[2]))
        om, ov = minmax(next_ply_board, t, max_ply, ply)
        if maximizing:
            if ov > opt_value:
                opt_move, opt_value = mv, ov
        else:
            if ov < opt_value:
                opt_move, opt_value = mv, ov
    return opt_move, opt_value


if __name__ == "__main__":
    # SETUP
    playercolor = "white"
    while playercolor not in ("black", "white"):
        playercolor = input("Play black or white? ").lower()
    computercolor = "black" if playercolor == "white" else "white"
    ply_depth = 3
    checkmate = False
    turn = "white"

    board = Board()
    board.standard_setup()

    # PLAY
    while not checkmate:
        board.printout(playercolor)
        print("Value for playercolor:", board.value(playercolor))
        move = None
        mover = turn
        if turn == playercolor:
            while not is_legal(move, board, playercolor):
                user_input = input("Move? ").lower().replace('to', '')
                user_input = ''.join(ch for ch in user_input if ch.isalnum())
                move = parse_move(user_input)
            moved_info = board.make_move(move)
            # promotion for player
            if moved_info:
                moved_piece, (tr, tc) = moved_info
                if moved_piece.name == 'pawn' and (tr == 0 or tr == 7):
                    choice = ''
                    while choice not in ('q', 'r', 'b', 'n'):
                        choice = input("Promote pawn to (q)ueen/(r)ook/(b)ishop/(n)ight? ").lower()
                    mapping = {'q': 'queen', 'r': 'rook', 'b': 'bishop', 'n': 'knight'}
                    board.board[tr][tc] = Piece(mapping[choice], moved_piece.color)
        else:
            print("Computer is thinking...")
            mv, calc_value = minmax(board, computercolor, ply_depth, 0)
            if mv is None:
                print("No moves found")
                break
            print("Makes", to_alfanum(mv[1]) + to_alfanum(mv[2]), "move with", mv[0])
            move = (mv[1], mv[2])
            moved_info = board.make_move(move)
            # auto-promotion to queen for computer
            if moved_info:
                moved_piece, (tr, tc) = moved_info
                if moved_piece.name == 'pawn' and (tr == 0 or tr == 7):
                    board.board[tr][tc] = Piece('queen', moved_piece.color)

        # After move, check if opponent is in check
        opponent = 'white' if mover == 'black' else 'black'
        if board.is_in_check(opponent):
            print(opponent.upper(), "is in CHECK!")

        # switch turns
        turn = 'white' if turn == 'black' else 'black'

        # check for checkmate/stalemate for the side to move
        legal_moves = board.all_moves_for_all_pieces(turn)
        if not legal_moves:
            if board.is_in_check(turn):
                print("CHECKMATE!", ('White' if turn == 'white' else 'Black'), 'is checkmated')
                checkmate = True
            else:
                print("Stalemate. Draw!")
                break
    if checkmate:
        print('Game over')
