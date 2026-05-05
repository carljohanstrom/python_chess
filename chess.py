#!/usr/bin/env python3

import copy
import sys
import os

# Restrict temporary file usage to a 'tmp' directory inside the repository.
# All helper functions that need to write temp files should use REPO_TMP.
REPO_ROOT = os.path.dirname(__file__)
REPO_TMP = os.path.join(REPO_ROOT, 'tmp')
try:
    os.makedirs(REPO_TMP, exist_ok=True)
except Exception:
    # If creation fails, fall back to in-memory behavior; avoid using system /tmp
    REPO_TMP = None


def repo_temp_path(filename):
    """Return a safe path inside the repository tmp directory or raise ValueError.
    Prevents accidental writes outside the repo.
    """
    if REPO_TMP is None:
        raise ValueError('Repository tmp directory not available')
    # normalize and ensure the result is inside REPO_TMP
    candidate = os.path.normpath(os.path.join(REPO_TMP, filename))
    if not candidate.startswith(os.path.normpath(REPO_TMP) + os.sep):
        raise ValueError('Attempt to access path outside repository tmp')
    return candidate


def save_text_to_repo_tmp(filename, text):
    path = repo_temp_path(filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def read_text_from_repo_tmp(filename):
    path = repo_temp_path(filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()



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
        # Deep-copy the board and Piece objects so simulations don't mutate original pieces
        nb = Board()
        nb.board = []
        for row in self.board:
            newrow = []
            for cell in row:
                if cell is None:
                    newrow.append(None)
                else:
                    np = Piece(cell.name, cell.color)
                    np.unmoved = cell.unmoved
                    newrow.append(np)
            nb.board.append(newrow)
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
        # Determine if square (row,col) is attacked by any piece of by_color.
        # Handle pawn attacks separately (they attack diagonally, not forward).
        knight_dirs = [(1, 2), (1, -2), (2, 1), (2, -1), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
        king_dirs = [(1, 1), (-1, -1), (1, -1), (-1, 1), (0, 1), (1, 0), (0, -1), (-1, 0)]
        for (piece, r, c) in self.all_pieces(by_color):
            if piece.name == 'pawn':
                dy = -1 if piece.color == 'white' else 1
                for dx in (-1, 1):
                    if (r + dy, c + dx) == (row, col):
                        return True
            elif piece.name == 'knight':
                for d in knight_dirs:
                    if (r + d[0], c + d[1]) == (row, col):
                        return True
            elif piece.name == 'king':
                for d in king_dirs:
                    if (r + d[0], c + d[1]) == (row, col):
                        return True
            else:
                # sliding pieces: bishop, rook, queen
                for d in piece.directions:
                    for step in range(1, piece.range + 1):
                        rr = r + d[0] * step
                        cc = c + d[1] * step
                        if rr < 0 or rr > 7 or cc < 0 or cc > 7:
                            break
                        if (rr, cc) == (row, col):
                            return True
                        if self.board[rr][cc] is not None:
                            # blocked by any piece
                            break
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
        # Castling: add potential king two-square moves as raw moves (legal filtering later)
        if piece.name == 'king' and piece.unmoved:
            r = row
            # king-side: check for a rook to the right with clear path
            for c in range(col+1, 8):
                rcell = self.board[r][c]
                if rcell is None:
                    continue
                if isinstance(rcell, Piece) and rcell.name == 'rook' and rcell.unmoved:
                    # ensure squares between are empty
                    if all(self.board[r][cc] is None for cc in range(col+1, c)):
                        moves.append((r, col+2))
                    break
                else:
                    break
            # queen-side: to the left
            for c in range(col-1, -1, -1):
                rcell = self.board[r][c]
                if rcell is None:
                    continue
                if isinstance(rcell, Piece) and rcell.name == 'rook' and rcell.unmoved:
                    if all(self.board[r][cc] is None for cc in range(c+1, col)):
                        moves.append((r, col-2))
                    break
                else:
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
        # Distinguish between "cannot move there" and "move leaves king in check"
        raw_moves = board._raw_moves_for_piece(from_row, from_col)
        if (to_row, to_col) not in raw_moves:
            piece = board.piece_at_pos(from_row, from_col)
            # Provide diagnostics to help understand why move isn't a raw move
            print(f"Illegal move. Cannot go there.")
            print(f"Piece at from: {piece} at {to_alfanum((from_row,from_col))} \nRaw moves: {raw_moves}")
            # more diagnostics: startrank, unmoved flag, range
            try:
                print(f"piece.startrank={piece.startrank}, piece.unmoved={piece.unmoved}, piece.range={piece.range}, from_row={from_row}")
            except Exception:
                pass
            # show occupancy of immediate forward squares for pawn
            if piece.name=='pawn':
                if piece.color=='white':
                    fr1 = board.piece_at_pos(from_row-1, from_col) if from_row-1>=0 else None
                    fr2 = board.piece_at_pos(from_row-2, from_col) if from_row-2>=0 else None
                else:
                    fr1 = board.piece_at_pos(from_row+1, from_col) if from_row+1<=7 else None
                    fr2 = board.piece_at_pos(from_row+2, from_col) if from_row+2<=7 else None
                print('Forward square 1 occupancy:', fr1)
                print('Forward square 2 occupancy:', fr2)
            return False
        # It is a raw move but illegal because it leaves the king in check. Show attackers after the move.
        nb = board.copy()
        nb.make_move(move)
        opp = 'white' if player == 'black' else 'black'
        kingpos = nb.find_king(player)
        attackers = []
        for (p, r, c) in nb.all_pieces(opp):
            if kingpos in nb._raw_moves_for_piece(r, c):
                attackers.append((p.name, r, c))
        if attackers:
            s = ", ".join([f"{name}@{to_alfanum((r,c))}" for (name, r, c) in attackers])
            print(f"Illegal move. Move would leave king in check from: {s}")
        else:
            print("Illegal move. Move would leave king in check.")
        return False
    return True


def to_alfanum(t):
    return chr(t[1] + 97) + str(8 - t[0])


def algebraic_to_coord(sq):
    # sq like 'e4'
    if len(sq) != 2:
        return None
    f, r = sq[0], sq[1]
    if f not in 'abcdefgh' or r not in '12345678':
        return None
    return (56 - ord(r), ord(f) - 97)


def parse_move(nnnn, board=None, color=None):
    # Accept long form like e2e4
    if len(nnnn) == 4 and all(ch.isalnum() for ch in nnnn):
        if nnnn[0] not in ("abcdefgh") or nnnn[1] not in ("12345678") or nnnn[2] not in ("abcdefgh") or nnnn[3] not in ("12345678"):
            return None
        return ((56 - ord(nnnn[1]), ord(nnnn[0]) - 97), (56 - ord(nnnn[3]), ord(nnnn[2]) - 97))
    # Fallback: try SAN if board and color provided
    if board is not None and color is not None:
        return san_to_move(board, nnnn, color)
    return None


def san_to_move(board, san, color):
    s = san.strip()
    if not s:
        return None
    s = s.replace('+', '').replace('#', '')
    s = s.replace('x', '')
    s = s.replace('=', '')
    s = s.replace('-', '')
    s = s.replace('*', '')
    s = s.lower()
    # Castling
    if s in ('o o', 'oo', 'o-o', '0-0', 'o o o', 'ooo', 'o-o-o', '0-0-0'):
        # find king and see castling targets in _raw_moves_for_piece
        king = board.find_king(color)
        if king is None:
            return None
        row, col = king
        raw = board._raw_moves_for_piece(row, col)
        for t in raw:
            if abs(t[1] - col) >= 2:
                return ((row, col), t)
        return None
    # Promotion notation like e8q handled by destination and later promotion
    # Pawn moves: like e4 or exd5 handled (we stripped x already)
    # Piece moves: prefix uppercase letter in SAN; in lowered s piece letter becomes lower
    piece_letter = None
    if s[0] in ('k','q','r','b','n'):
        piece_letter = s[0]
        dest = s[-2:]
        disamb = s[1:-2]
    else:
        # pawn move
        piece_letter = 'p'
        dest = s[-2:]
        disamb = s[:-2]
    to = algebraic_to_coord(dest)
    if to is None:
        return None
    # map piece letter to full name
    letter_map = {'n':'knight','b':'bishop','r':'rook','q':'queen','k':'king','p':'pawn'}
    target_name = letter_map.get(piece_letter, None)
    candidates = []
    for (p, r, c) in board.all_pieces(color):
        if p.name != target_name:
            continue
        raw = board._raw_moves_for_piece(r, c)
        if to in raw:
            candidates.append(((r,c), to))
    if not candidates:
        return None
    # apply disambiguation if present (file or rank)
    if disamb:
        filt = []
        for mv in candidates:
            (fr, fc), _ = mv
            filec = chr(fc + 97)
            rankc = str(8 - fr)
            if disamb == filec or disamb == rankc or disamb == (filec+rankc):
                filt.append(mv)
        if filt:
            candidates = filt
    # If multiple candidates remain, prefer one that is legal (doesn't leave king in check)
    for mv in candidates:
        if not board.would_leave_king_in_check(mv, color):
            return mv
    # else return first candidate
    return candidates[0]


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
        next_ply_board = b.copy()
        # copy en-passant state for accurate simulation (copy already does this)
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
    move_log = []

    # PLAY
    while not checkmate:
        board.printout(playercolor)
        print("Value for playercolor:", board.value(playercolor))
        move = None
        mover = turn
        if turn == playercolor:
            # player input loop: support commands q/quit, l/log/moves
            while True:
                user_input_raw = input("Move? ").strip()
                if user_input_raw == '':
                    continue
                ui = user_input_raw.lower()
                ui_alpha = ''.join(ch for ch in ui if ch.isalpha())
                if ui_alpha in ('q', 'quit'):
                    print('Quitting.')
                    sys.exit(0)
                if ui_alpha in ('l', 'log', 'moves'):
                    print('Moves so far:')
                    if not move_log:
                        print('(no moves yet)')
                    for m in move_log:
                        print(m)
                    continue
                # sanitize and parse standard move like 'd2d4' or 'd2 d4' or 'd2 to d4'
                ui = ui.replace('to', '').replace('-', '')
                usr = ''.join(ch for ch in ui if ch.isalnum())
                move = parse_move(usr, board, playercolor)
                if move is None:
                    print('Invalid move format. Use e.g. e2e4 or commands q/log')
                    continue
                if not is_legal(move, board, playercolor):
                    # is_legal prints reason
                    continue
                break
            moved_info = board.make_move(move)
            # log player move
            move_log.append(f"{playercolor}: {to_alfanum(move[0])}{to_alfanum(move[1])}")
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
            # log computer move
            move_log.append(f"{computercolor}: {to_alfanum(move[0])}{to_alfanum(move[1])}")
            # auto-promotion to queen for computer
            if moved_info:
                moved_piece, (tr, tc) = moved_info
                if moved_piece.name == 'pawn' and (tr == 0 or tr == 7):
                    board.board[tr][tc] = Piece('queen', moved_piece.color)

        # After move, check if opponent is in check
        opponent = 'white' if mover == 'black' else 'black'
        # compute opponent legal moves to decide if it's check or checkmate (avoid printing check when it's checkmate)
        opp_legal_moves = board.all_moves_for_all_pieces(opponent)
        if board.is_in_check(opponent):
            if opp_legal_moves:
                print(opponent.upper(), "is in CHECK!")
            # else: suppress check message; checkmate handling below will report

        # switch turns
        turn = 'white' if turn == 'black' else 'black'

        # check for checkmate/stalemate for the side to move
        legal_moves = opp_legal_moves if turn == opponent else board.all_moves_for_all_pieces(turn)
        if not legal_moves:
            if board.is_in_check(turn):
                print("CHECKMATE!", ('White' if turn == 'white' else 'Black'), 'is checkmated')
                checkmate = True
            else:
                print("Stalemate. Draw!")
                break
    if checkmate:
        print("\nFinal position at checkmate:")
        board.printout(playercolor)
        print('Game over')
