from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase, CellState

from referee.game import Board
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

# def is_capture_move(board, move, agent_color):
#     new_board = simulate(board, move)

#     before = count_pieces(board, opponent_color)
#     after = count_pieces(new_board, opponent_color)

#     return after < before

def heuristic_func(self,board,agent_color) -> int:
    """
    1. token count 2. height count 3. eat opp including bonus (eg prioritise larger height) 4. opp eat us 
    5. cascade kill 6. cascadee self loss 7. edge score 8. threathed token 
    9. trapped 10. endgame 11. 

    #later can try adding score for pushing cascade too edge
    """
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED
    
    if board.game_over:
        winner = board.winner_color
        if winner == agent_color:
            return 100000  
        elif winner == opp_color:
            return -100000
        else: #DOUBLE CHECK FOR LATER - FOR TIE CONDITION
            return -5000
        
    agent_total = 0
    opp_total = 0

    agent_stacks = 0
    opp_stacks = 0

    agent_edge = 0
    opp_edge = 0

    agent_trapped = 0
    opp_trapped = 0

    agent_eat = 0
    opp_eat = 0

    agent_eat_bonus = 0
    opp_eat_bonus = 0

    agent_threat = 0
    opp_threat = 0
    
    agent_cascade_kill = 0
    opp_cascade_kill = 0

    agent_cascade_self_loss = 0
    opp_cascade_self_loss = 0

    agent_cascade_push = 0
    opp_cascade_push = 0

    agent_positions = {}
    opp_positions = {}


    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        r,c = coord.r , coord.c
        h = cell.height
        is_agent = (cell.color == agent_color)

        if is_agent:
            agent_positions[(r,c)] = h
            agent_total += h
            agent_stacks += 1
        else:
            opp_positions[(r,c)] = h
            opp_total += h
            opp_stacks += 1

        edge_dist = min(r, 7-r, c,7-c)
        if edge_dist == 0:
            if is_agent:
                agent_edge += 4 * h
            else:
                opp_edge += 4 * h
        elif edge_dist == 1:
            if is_agent:
                agent_edge += 2 * h
            else:
                opp_edge += 2 * h

    for (r,c), h in agent_positions.items():
        moves_count = 0
        threatened = False
        for d in CARDINAL_DIRECTIONS:
            new_r , new_c = r + d.r , c + d.c 
            if not (0 <= new_r <= 7 and 0 <= new_c <= 7 ):
                continue

            if (new_r, new_c) in agent_positions:
                moves_count += 1
            elif (new_r , new_c) in opp_positions:
                opp_h = opp_positions[(new_r, new_c)]
                if h >= opp_h:
                    moves_count += 2
                    agent_eat_bonus += opp_h * 10
                    agent_eat += 1

                if opp_h >= h:
                    threatened = True
            else:
                moves_count += 1
        if moves_count<= 1:
            agent_trapped += 1
        if threatened:
            agent_threat += h
            
        #Cascade calculation
        if h >= 2:
            for d in CARDINAL_DIRECTIONS:
                reach = h
                enemy_position = None
                enemy_height = 0
                for step in range (1, reach +1):
                    new_r = r + (d.r * step)
                    new_c = c + (d.c * step)
                    if not (0 <= new_r <= 7 and 0 <= new_c <= 7):
                        agent_cascade_self_loss += (reach - step + 1)
                        break
                    if (new_r, new_c) in opp_positions:
                        enemy_position = step
                        enemy_height = opp_positions[(new_r,new_c)]
                        break

                if enemy_position is not None:
                    enemy_r = r + d.r * enemy_position
                    enemy_c = c + d.c * enemy_position
                    push_steps = reach - enemy_position
                    final_r = enemy_r + d.r * push_steps
                    final_c = enemy_c + d.c * push_steps

                    if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                        agent_cascade_kill += enemy_height
                        agent_cascade_push += enemy_height + 6
                    else:
                        before_edge = min(enemy_r, 7 - enemy_r, enemy_c, 7 - enemy_c)
                        after_edge = min(final_r, 7 - final_r, final_c, 7 - final_c)
                        if after_edge < before_edge:
                            agent_cascade_push += enemy_height + 3

    for (r,c), h in opp_positions.items():
        moves_count = 0
        threatened = False
        for d in CARDINAL_DIRECTIONS:
            new_r , new_c = r + d.r , c  + d.c 
            if not (0 <= new_r <= 7 and 0 <= new_c <= 7 ):
                continue

            if (new_r, new_c) in opp_positions:
                moves_count += 1
            elif (new_r , new_c) in agent_positions:
                agent_h = agent_positions[(new_r, new_c)]
                if h >= agent_h:
                    moves_count += 2
                    opp_eat_bonus += agent_h * 10
                    opp_eat += 1

                if agent_h >= h:
                    threatened = True
            else:
                moves_count += 1
        if moves_count<= 1:
            opp_trapped += 1
        if threatened:
            opp_threat += h
            
        #Cascade calculation
        if h >= 2:
            for d in CARDINAL_DIRECTIONS:
                reach = h
                enemy_position = None
                enemy_height = 0
                for step in range (1, reach +1):
                    new_r = r + (d.r * step)
                    new_c = c + (d.c * step)
                    if not (0 <= new_r <= 7 and 0 <= new_c <= 7):
                        opp_cascade_self_loss += (reach - step + 1)
                        break
                    if (new_r, new_c) in agent_positions:
                        enemy_position = step
                        enemy_height = agent_positions[(new_r,new_c)]
                        break

                if enemy_position is not None:
                    enemy_r = r + d.r * enemy_position
                    enemy_c = c + d.c * enemy_position
                    push_steps = reach - enemy_position
                    final_r = enemy_r + d.r * push_steps
                    final_c = enemy_c + d.c * push_steps

                    if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                        opp_cascade_kill += enemy_height
                        opp_cascade_push += enemy_height + 6
                    else:
                        before_edge = min(enemy_r, 7 - enemy_r, enemy_c, 7 - enemy_c)
                        after_edge = min(final_r, 7 - final_r, final_c, 7 - final_c)
                        if after_edge < before_edge:
                            opp_cascade_push += enemy_height + 3

    # For endgame preperation
    endgame = 0
    if len(opp_positions) == 1 and len(agent_positions) > 0:
        (opp_r, opp_c), opp_h = next(iter(opp_positions.items()))

        min_dist = math.inf #calculate which of our token is the cloest to the enemy token
        second_min_dist = math.inf
        blocked_sides = 0

        if opp_r == 0:
            blocked_sides += 1
        if opp_r == 7:
            blocked_sides += 1
        if opp_c == 0:
            blocked_sides += 1
        if opp_c == 7:
            blocked_sides += 1

        for d in CARDINAL_DIRECTIONS:
            nr, nc = opp_r + d.r, opp_c + d.c
            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                continue
            if (nr, nc) in agent_positions:
                blocked_sides += 1

        for (r, c), h in agent_positions.items():
            dist = abs(r - opp_r) + abs(c - opp_c)

            if dist < min_dist:
                second_min_dist = min_dist
                min_dist = dist
            elif dist < second_min_dist:
                second_min_dist = dist

            if dist == 1 and h >= opp_h:
                endgame += 80

            if h >= 2:
                for d in CARDINAL_DIRECTIONS:
                    aligned = False
                    if d.r != 0:
                        aligned = (c == opp_c and ((d.r == 1 and opp_r > r) or (d.r == -1 and opp_r < r)))
                    else:
                        aligned = (r == opp_r and ((d.c == 1 and opp_c > c) or (d.c == -1 and opp_c < c)))

                    if not aligned:
                        continue

                    line_dist = abs(r - opp_r) + abs(c - opp_c)
                    if line_dist > h:
                        continue

                    push_steps = h - line_dist
                    final_r = opp_r + d.r * push_steps
                    final_c = opp_c + d.c * push_steps

                    if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                        endgame += 50
                    else:
                        before_edge = min(opp_r, 7 - opp_r, opp_c, 7 - opp_c)
                        after_edge = min(final_r, 7 - final_r, final_c, 7 - final_c)
                        if after_edge < before_edge:
                            endgame += 20

        if min_dist < math.inf:
            endgame += max(0, 8 - min_dist) * 10
        if second_min_dist < math.inf:
            endgame += max(0, 8 - second_min_dist) * 4
        endgame += blocked_sides * 12

    score = 0
    score += 15 * (agent_total - opp_total)
    score += 8 * (agent_stacks - opp_stacks)
    score -= 10 * (agent_edge - opp_edge)
    score -= 8 * (agent_trapped -opp_trapped )
    score += 12 * (agent_eat - opp_eat )
    score += 6 * (agent_eat_bonus- opp_eat_bonus)
    score += 9 * (agent_threat - opp_threat)
    score += 13 * (agent_cascade_kill - opp_cascade_kill)
    score -= 10 * (agent_cascade_self_loss - opp_cascade_self_loss )
    score += 5 * ( agent_cascade_push - opp_cascade_push )
    score += endgame

    return score

def manhanttan_distance(
    coord_one: Coord,
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)


def all_legal_actions(self,board) -> list[Action]:
    eat_actions = []
    cascade_actions = []
    move_actions = []
    for coord, cell in board._state.items():
        if cell.is_empty:
            continue
        if cell.color != board.turn_color:
            continue
        for each_dir in CARDINAL_DIRECTIONS:

            #Eat
            try:
                eat = EatAction(coord, each_dir)
                board._resolve_eat_action(eat)
                eat_actions.append(eat)
            except IllegalActionException:
                pass

            #Cascade
            try:
                cascade = CascadeAction(coord,each_dir)
                board._resolve_cascade_action(cascade)
                cascade_actions.append(cascade)

            except IllegalActionException:
                pass

            #Move
            try:
                move = MoveAction(coord, each_dir)
                board._resolve_move_action(move)
                move_actions.append(move)
            except IllegalActionException:
                pass
    return eat_actions + cascade_actions + move_actions



def iterative_deepening_play(
    self,
    board: Board,
    max_depth: int = 8,
    time_limit: float = 2.5
) -> Action:
    best_action = None
    start = time.time()

    for depth in range(1, max_depth + 1):
        score, action = minimax_root(self,
            board = board, depth=depth, start_time=start, 
            time_limit=time_limit
        )

        if action is not None:
            best_action = action
        
        if time.time() - start > time_limit:
            print(f"Timed out at depth {depth}, using depth {depth-1} result")
            break

    return best_action

def minimax_root(
    self,
    board: Board,
    depth: int,
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
            # maximizing = (board.turn_color == agent_colour)
            try:
                curr_score = min_max_algo_with_time(
                    self,
                    False, 
                    board, 
                    depth-1, 
                    alpha, 
                    beta, 
                    start_time=start_time,
                    time_limit=time_limit
                ) 
            except TimeoutError:
                board.undo_action()
                raise
            
            board.undo_action()

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
    beta:float,
    start_time,
    time_limit: float
) -> int:
    if (time.time() - start_time) > time_limit:
        raise TimeoutError()
    
    return min_max_algo(self, maximizing, board, depth, alpha, beta)