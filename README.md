# python_chess
A Simple chess game written in Python as a one-day exercise. Very slow right now. But next version will contain improvements. There is also some rules that are not yet implemented, such as castling, passant, pawn promotion, check, and checkmate.

##TBD
- [X] Push to remote Github repo
- [ ] Use better variables: "row" -> "rank" and "col" -> "file"
- [ ] There is something funny going on if max ply_depth is set to 4. (3 is ok)
- [ ] Improve variable containg a move so it is less confusing
- [X] Profiling measurements where to start optimizations. culprit=deepcopy
- [X] Optimize for speed: faster copy of board
- [ ] Optimize for speed: scorekeeping (instead of recalculation)
- [ ] Optimize for speed: pruning for really bad branches
- [ ] Optimize for speed: break when all pieces have been found
- [ ] Optimize for speed: Keep a separate list of pieces
- [ ] Optimize for speed: do not use strings as ids
- [ ] Implement a function to set the difficult level (i.e. max ply_depth)
- [ ] Implement check
- [ ] Implement checkmate warning
- [ ] Implement illegal moves parsing when in checkmate
- [ ] Implement castling
- [ ] Implement pawn promotion (maybe to tower to avoid stale mate)
- [ ] Implement en passant
- [ ] Implement stalemate
- [ ] Implement quit
- [ ] Implement draw (offered by computer)
- [ ] Implement draw (offered by player)
- [ ] Implement resign (computer)
- [ ] Implement resign (player)
- [ ] Make option to run as process (against each other)
