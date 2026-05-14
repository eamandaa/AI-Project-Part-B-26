from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase, CellState

from referee.game import Board, CellMutation, BoardMutation
import math
from .zobrist_hashing import compute_hash, ScoreFlag
import time 
from referee.game import BOARD_N

def choose_best_action(self,board,depth) -> Action: #The big picture of min max
    best_action = None
    best_score = -math.inf
    possible_actions = all_legal_actions(self,board)

    # for each_action in possible_actions:
    #     if isinstance(each_action, EatAction):
    #         return each_action

    for each_action in possible_actions:
        board.apply_action(each_action)
        #maximizing = False
        curr_score = min_max_algo(self, False, board, depth - 1, alpha= -math.inf, beta = math.inf) #try depth -1 or no
        board.undo_action()

        if curr_score > best_score:
            best_score = curr_score
            best_action = each_action
              
    return best_action

def min_max_algo(
    self, 
    maximizing: bool, 
    board: Board, 
    depth: int, 
    alpha: float, 
    beta:float,
) -> int: #Each depth of min max
    """
    Determine the next action using min_max algo
    """

    hash_key = compute_hash(board)
    tt_move = None

    # check whether already visit this board state before 
    if hash_key in self._tranposition_table:
        stored_depth, stored_value, score_flag, stored_best_move = self._tranposition_table[hash_key]
        if stored_depth >= depth:
            if score_flag == ScoreFlag.EXACT:
                return stored_value
            if score_flag == ScoreFlag.LOWER_BOUND: 
                alpha =  max(alpha,stored_value)
            if score_flag == ScoreFlag.UPPER_BOUND:
                beta = min(beta,stored_value)
        if alpha >= beta:
            return stored_value
        
        tt_move = stored_best_move

    #Move, eat and cascade
    #Red always goes first -> Max
    if board.game_over or (not board._has_legal_actions()) or depth == 0:
        value =  heuristic_func(self,board,self._color)
        self._tranposition_table[hash_key] = (depth, value, ScoreFlag.EXACT, None)
        return value
    
    possible_actions = all_legal_actions(self,board)

    if tt_move is not None and tt_move in possible_actions:
        possible_actions.remove(tt_move)
        possible_actions.insert(0, tt_move)
    
    alpha_original = alpha
    beta_original = beta
    best_move = None
    
    if maximizing == True:
        best_score = -math.inf
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            
            new_score = min_max_algo(self,False, board, depth - 1,alpha,beta)
            board.undo_action()
            #print("DEPTH", depth, "ROOT ACTION", each_action, "SCORE", new_score)
            if new_score > best_score:
                best_score = new_score
                best_move = each_action
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    
    else:
        best_score = math.inf
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(self,True, board, depth - 1,alpha,beta)
            board.undo_action()
            if new_score < best_score:
                best_score = new_score
                best_move = each_action
            beta = min(beta, best_score)
            if alpha >= beta:
                break 

    if best_score <= alpha_original:
        score_flag = ScoreFlag.UPPER_BOUND
    elif best_score >= beta_original:
        score_flag = ScoreFlag.LOWER_BOUND
    else:
        score_flag = ScoreFlag.EXACT

    self._tranposition_table[hash_key] = (depth, best_score, score_flag, best_move)
    return best_score




def calculate_potential_risk_after_action(
    r: int,
    c: int,
    h: int, 
    opponent_position: dict[tuple[int, int], int],
) -> tuple[int, int]:
    """
    Check all direction within the same row and same column to check is there 
    any threat to be pushed off the board or being eaten after performing an action
    """
    cascade_risk = 0
    eat_threat = 0
    eat_score = 0
    for direction in CARDINAL_DIRECTIONS:
        step = 1

        while True:
            new_r = r + direction.r * step
            new_c = c + direction.c * step

            if not (0 <= new_r <= 7 and 0 <= new_c <= 7):
                break

            if (new_r, new_c) in opponent_position:
                opponent_height = opponent_position[(new_r, new_c)]

                # enemy just next to us
                if step == 1:
                    # enemy can eat us 
                    if opponent_height >= h:
                        eat_threat += h
                        break
                    # just check higher cuz next move is enemy
                    elif h > opponent_height:
                        eat_score += opponent_height
                        break

                # Can this enemy's cascade actually reach the new position
                if step <= opponent_height and opponent_height > 1:
                    # get pushed 1 cell further in the direction
                    push_steps = opponent_height - step + 1
                    pushed_r = r - direction.r * push_steps
                    pushed_c = c - direction.c * push_steps
                    # get pushed out off bound already
                    if not (0 <= pushed_r <= 7 and 0 <= pushed_c <= 7):
                        cascade_risk += h
                    break

            step += 1

    return cascade_risk, eat_threat, eat_score

def manhanttan_distance(
    coord_one: Coord, 
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)

def all_legal_actions(self,board) -> list[Action]:
    start  = time.time()
    eat_actions = []
    cascade_actions = []
    move_actions = []
    
    for current_coord, cell in board._state.items(): 
        # empty cell 
        if cell.is_empty:
            continue
        # enemy coord
        if cell.color != board.turn_color:
            continue
        
        # intialisation of the current coord
        current_cell_state = board[current_coord]
        current_r , current_c = current_coord.r, current_coord.c
        current_color, current_height = current_cell_state.color, current_cell_state.height
        for direction in CARDINAL_DIRECTIONS:
            
            # Cascade action
            if current_height >= 2:
                cascade_actions.append(CascadeAction(current_coord, direction))

            new_r = current_r + direction.r
            new_c = current_c + direction.c

            if not board._is_within_bounds(new_r, new_c):
                continue

            # neighbour coord 
            new_coord = Coord(new_r, new_c)
            neighbour = board[new_coord]

            if neighbour is None or neighbour.color is None:
                move_actions.append(MoveAction(current_coord, direction))
            elif neighbour.color == current_color:
                move_actions.append(MoveAction(current_coord, direction))
            elif neighbour.height <= current_height:
                eat_actions.append(EatAction(current_coord, direction))

    actions = eat_actions + cascade_actions + move_actions
    actions.sort(key=lambda a: (-action_order_score(board, a), str(a)))
    # print(f"Generating possible action with condition check is {time.time() - start}")
    return actions

def iterative_deepening_play(
    self,
    board: Board,
    agent_colour: PlayerColor,
    max_depth: int = 5,
    time_limit: float = 2.5
) -> Action:
    best_action = None
    start = time.time()
 
    for depth in range(1, max_depth + 1):
        score, action = minimax_root(self,
            board = board, depth=depth, agent_colour = agent_colour, start_time=start, 
            time_limit=time_limit
        )

        if action is None or time.time() - start > time_limit:
            print(f"Timed out at depth {depth}, using depth {depth-1} result for new agent")
            break
        
        best_action = action

    return best_action

def minimax_root(
    self,
    board: Board,
    depth: int,
    agent_colour: PlayerColor,
    start_time: float,
    time_limit: float
) -> tuple[float, Action | None]:
    """
    Evaluate each possible action based on the score then return 
    the action with highest score 
    """
    
    best_action = None
    best_score = float("-inf")
    alpha = float("-inf")
    beta = float("inf")

    possible_actions = all_legal_actions(self,board)
    # print("TURN:", board.turn_color)
    # for a in possible_actions:
    #     print(a)

    hash_key = compute_hash(board)


    tt_move = None
    if hash_key in self._tranposition_table:
        _, _, _, stored_best_move = self._tranposition_table[hash_key]
        tt_move = stored_best_move
    
    if tt_move and tt_move in possible_actions:
        possible_actions.remove(tt_move)
        possible_actions.insert(0, tt_move)

    try:
        for action in possible_actions:
            board.apply_action(action)
            maximizing = (board.turn_color == agent_colour)
            try:
                curr_score = min_max_algo_with_time(
                    self,
                    # changed this part 
                    maximizing, 
                    board, 
                    depth-1, 
                    alpha, 
                    beta, 
                    agent_colour,
                    start_time=start_time,
                    time_limit=time_limit
                ) 
                current_hash = board._board_hash()
                count_repetition = board._position_history.count(current_hash) >= 3
            except TimeoutError:
                board.undo_action()
                raise
            
            board.undo_action()
            if count_repetition:
                print("deduct score\n sxff \n \sdv \n xew \n")
                curr_score -= 150000

            if curr_score > best_score:
                best_score = curr_score
                best_action = action
            alpha = max(alpha, best_score)

    except TimeoutError:
        return None, None
             
    return best_score, best_action

def min_max_algo_with_time(
    self,
    maximizing: bool, 
    board: Board,
    depth: int,
    alpha: float, 
    beta: float, 
    agent_colour: PlayerColor,
    start_time,
    time_limit: float
) -> int:
    
    if (time.time() - start_time) > time_limit:
        raise TimeoutError()
    
    # Create hash
    hash_key = compute_hash(board)
    tt_move = None

    # check whether already visit this board state before 
    if hash_key in self._tranposition_table:
        stored_depth, stored_value, score_flag, stored_best_move = self._tranposition_table[hash_key]
        if stored_depth >= depth:
            if score_flag == ScoreFlag.EXACT:
                return stored_value
            if score_flag == ScoreFlag.LOWER_BOUND: 
                alpha =  max(alpha,stored_value)
            if score_flag == ScoreFlag.UPPER_BOUND:
                beta = min(beta,stored_value)
        if alpha >= beta:
            return stored_value
        
        tt_move = stored_best_move

    #Move, eat and cascade
    #Red always goes first -> Max
    if board.game_over or (not board._has_legal_actions()) or depth == 0:
        value =  heuristic_func(self,board,self._color)
        self._tranposition_table[hash_key] = (depth, value, ScoreFlag.EXACT, None)
        return value
    
    possible_actions = all_legal_actions(self,board)

    if tt_move is not None and tt_move in possible_actions:
        possible_actions.remove(tt_move)
        possible_actions.insert(0, tt_move)
    
    alpha_original = alpha
    beta_original = beta
    best_move = None
    
    if maximizing == True:
        best_score = -math.inf
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            maximizing_next = (board.turn_color == agent_colour)
            try: 
                new_score = min_max_algo_with_time(self, maximizing_next, board, depth - 1, alpha,
                                                   beta,agent_colour, start_time, time_limit)
            except TimeoutError:
                board.undo_action()
                raise
            board.undo_action()
            #print("DEPTH", depth, "ROOT ACTION", each_action, "SCORE", new_score)
            if new_score > best_score:
                best_score = new_score
                best_move = each_action
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    
    else:
        best_score = math.inf
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            maximizing_next = (board.turn_color == agent_colour)
            try: 
                new_score = min_max_algo_with_time(self, maximizing_next, board, depth - 1, alpha,
                                                   beta,agent_colour, start_time, time_limit)
            except TimeoutError:
                board.undo_action()
                raise
            board.undo_action()
            if new_score < best_score:
                best_score = new_score
                best_move = each_action
            beta = min(beta, best_score)
            if alpha >= beta:
                break 

    if best_score >= beta_original:
        score_flag = ScoreFlag.LOWER_BOUND
    elif best_score <= alpha_original:
        score_flag = ScoreFlag.UPPER_BOUND
    else:
        score_flag = ScoreFlag.EXACT

    self._tranposition_table[hash_key] = (depth, best_score, score_flag, best_move)
    return best_score

def action_order_score(board, action):
    coord = action.coord
    d = action.direction
    if isinstance(action, EatAction):
        target = Coord(coord.r + d.r, coord.c + d.c)

        victim = board._state[target]
        attacker = board._state[coord]

        # if not victim.is_empty and not attacker.is_empty:
        return 10000 + (attacker.height - victim.height) * 100 + victim.height * 10 #added this

        #return 10000

    if isinstance(action, CascadeAction):
        h = board._state[coord].height

        if d.r == 1:
            dist_to_edge = 7 - coord.r
        elif d.r == -1:
            dist_to_edge = coord.r
        elif d.c == 1:
            dist_to_edge = 7 - coord.c
        else:
            dist_to_edge = coord.c

        lost_tokens = max(0, h - dist_to_edge)

        return 1000 + h * 10 - lost_tokens * 500

    if isinstance(action, MoveAction):
        target = Coord(coord.r + d.r, coord.c + d.c)

        # if merge is available
        if not board._state[target].is_empty:
            return 10 * (board._state[target].height + board._state[coord].height)

    return 0