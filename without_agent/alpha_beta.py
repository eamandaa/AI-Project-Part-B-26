from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase, CellState

from referee.game import Board, CellMutation, BoardMutation
import math
from .zobrist_hashing import compute_hash, ScoreFlag
import time 
from referee.game import BOARD_N
import os

WEIGHTS = {
    "material": int(os.getenv("W_MATERIAL", 140)),
    "eat": int(os.getenv("W_EAT", 50)),
    "safe_eat": int(os.getenv("W_SAFE_EAT", 40)),
    "threat": int(os.getenv("W_THREAT", 20)),
    "cascade_kill": int(os.getenv("W_CASCADE_KILL", 20)),
    "cascade_self_loss": int(os.getenv("W_CASCADE_SELF_LOSS", 15)),
    "trapped": int(os.getenv("W_TRAPPED", 6)),
}

def heuristic_func(
    self,
    board: Board,
    agent_color: PlayerColor
) -> int:
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

    agent_trapped = 0
    opp_trapped = 0

    agent_eat = 0
    opp_eat = 0

    agent_threat = 0
    opp_threat = 0
    
    agent_cascade_kill = 0
    opp_cascade_kill = 0

    agent_cascade_penalty = 0
    opp_cascade_penalty = 0

    agent_safe_eat = 0
    opp_safe_eat = 0

    score = 0

    agent_positions = {}
    opp_positions = {}


    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        r,c = coord.r , coord.c
        h = cell.height
        is_agent = (cell.color == agent_color)
        #track total height
        # store the tokens on dictionary to avoid repetitive accessing the board 
        if is_agent:
            agent_positions[(r,c)] = h
            agent_total += h
            agent_stacks += 1

        else:
            opp_positions[(r,c)] = h
            opp_total += h
            opp_stacks += 1


    agent_eat, agent_trapped, agent_threat, agent_safe_eat, agent_cascade_kill, agent_cascade_penalty = check_mobility_and_eat_and_cascade_risk(agent_positions, opp_positions)
    opp_eat, opp_trapped, opp_threat, opp_safe_eat, opp_cascade_kill, opp_cascade_penalty = check_mobility_and_eat_and_cascade_risk(opp_positions, agent_positions)


    # For winning preperation
    endgame = 0

    # to prevent draw, chase and eat more agressively
    if agent_stacks + opp_stacks <= 5:
        endgame += chase_aggresively_reward(agent_positions, opp_positions)

    #Endgame prep
    #Assume that the situation is when one token is avoiding another token while one is trying to eat them and chasing around
    if opp_stacks <= 4 and (agent_total > opp_total ): #condition for end game #try vs each other with +1,2 and none # try with 2
        endgame += endgame_condition_heuristic(agent_positions, opp_positions)

    play_turns = len(board._position_history) #N
    if play_turns >= 220:
        score += 200 * opp_total


    score += WEIGHTS["material"] * (agent_total - opp_total)
    score += WEIGHTS["eat"] * (agent_eat - opp_eat)
    score += WEIGHTS["safe_eat"] * (agent_safe_eat - opp_safe_eat)
    score += WEIGHTS["threat"] * (opp_threat - agent_threat)
    score += WEIGHTS["cascade_kill"] * (agent_cascade_kill - opp_cascade_kill)
    score -= WEIGHTS["cascade_self_loss"] * (agent_cascade_penalty - opp_cascade_penalty)
    score -= WEIGHTS["trapped"] * (agent_trapped - opp_trapped)
    score += endgame
    return score

    # score += 140 * (agent_total - opp_total)
    # score += 50 * (agent_eat - opp_eat)
    # score += 40 * (agent_safe_eat - opp_safe_eat)
    # score += 20 * (opp_threat - agent_threat) 
    # score += 20 * (agent_cascade_kill - opp_cascade_kill)
    # score -= 15 * (agent_cascade_penalty - opp_cascade_penalty)
    # score -= 6 * (agent_trapped - opp_trapped)

    score += endgame 
    return score 
#then try tebalik and vs agent old

def chase_aggresively_reward(
    agent_positions: dict[tuple[int, int], int],
    opp_positions: dict[tuple[int, int], int]
):
    endgame = 0
    best_safe_dist = math.inf

    for (r, c), h in agent_positions.items():
        for (opp_r, opp_c), opp_h in opp_positions.items():

            # only chase if our stack is strictly stronger
            if h >= opp_h:
                dist = abs(r - opp_r) + abs(c - opp_c)
                best_safe_dist = min(best_safe_dist, dist)

    if best_safe_dist < math.inf:
        endgame += max(0, 8 - best_safe_dist) * 35

    return endgame

def endgame_condition_heuristic(
    agent_positions: dict[tuple[int, int], int],
    opp_positions: dict[tuple[int, int], int]
):
    endgame = 0
    for (opp_r, opp_c), opp_h in opp_positions.items():

        #End game heuristic
        closest_dist = math.inf
        second_closest_dist = math.inf
        hunters_adjacent = 0
        stronger_hunters_near = 0
        blocked_sides = 0 #trapping enemy by how many is it blocks
        free_sides = 0 #how many sides are free
        imm_eat = 0
        # Count blocked escape squares around enemy
        for d in CARDINAL_DIRECTIONS:
            nr = opp_r + d.r
            nc = opp_c + d.c

            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                blocked_sides += 1 #check if opponent is in the edge 
                continue

            if (nr, nc) in agent_positions:
                blocked_sides += 1 #check if my agent is blocking the opponent
            else:
                free_sides += 1 #if d is empty cell

        # Count hunters and distance pressure
        for (r, c), h in agent_positions.items():
            dist = abs(r - opp_r) + abs(c - opp_c)

            if dist < closest_dist:
                second_closest_dist = closest_dist
                closest_dist = dist
            elif dist < second_closest_dist:
                second_closest_dist = dist

            if dist == 1 and h >= opp_h:
                hunters_adjacent += 1 #potential eat immidiately without movement
                imm_eat += opp_h
            if 1 < dist <= 3 and h >= opp_h:
                stronger_hunters_near += 1 #potential eat but require movement

            if h < opp_h and dist <= 2:
                endgame -= 20 #if we will be eaten instead

            # Endgame cascade alignment, line up and push to cascade
            if h >= 2:
                same_row = (r == opp_r)
                same_col = (c == opp_c)

                if same_row or same_col:
                    dist = abs(r - opp_r) + abs(c - opp_c)

                    # cascade can reach enemy
                    if dist <= h:
                        push_steps = h - dist + 1

                        # check distance from enemy to edge in the push direction
                        if same_col:
                            if opp_r > r:
                                dist_to_edge = 7 - opp_r
                            else:
                                dist_to_edge = opp_r
                        else:  # same_row
                            if opp_c > c:
                                dist_to_edge = 7 - opp_c
                            else:
                                dist_to_edge = opp_c

                        # reward lining up
                        endgame += max(0, 8 - dist) * 15 #10

                        # bigger reward if cascade can push enemy off board
                        if push_steps > dist_to_edge:
                            endgame += 180 * opp_h
                        else:
                            endgame += 15 * opp_h #try 15 next


        if closest_dist < math.inf: #how close is my token to enemy
            endgame += max(0, 8 - closest_dist) * 20 #8 bcs we have 8 row n column

        if second_closest_dist < math.inf: #same for the 2nd token
            endgame += max(0, 8 - second_closest_dist) * 8

        # Reward trapping
        endgame += blocked_sides * 40
        endgame -= free_sides * 15

        # Reward actual capture pressure
        endgame += hunters_adjacent * 100
        endgame += min(stronger_hunters_near,3) * 25 #only max 3 token will chase
        endgame -= 110 * len(opp_positions) #so that it preferes to end the game and not just chasing
        endgame += imm_eat * 300

    return endgame


def check_mobility_and_eat_and_cascade_risk(
    agent_positions: dict[tuple[int, int], int],
    opp_positions: dict[tuple[int, int], int]
):
    agent_eat = 0 # how likely the agent can eat
    agent_trapped = 0 # how many tokens are surrounded by most enemies
    agent_threat = 0 # how likely it is being eaten by enemy
    agent_safe_eat = 0 # can guarentee eat without worrying being eaten back by enemy 
    agent_cascade_kill = 0
    agent_cascade_penalty = 0

    for (r,c), h in agent_positions.items():
        moves_count = 0
        for d in CARDINAL_DIRECTIONS:
            new_r , new_c = r + d.r , c + d.c 
            if not (0 <= new_r <= 7 and 0 <= new_c <= 7 ):
                continue

            if (new_r, new_c) in agent_positions: #merging friendly token
                moves_count += 1

            elif (new_r , new_c) in opp_positions: #check if i can eat opponent or will be eaten by the opponent depending on my height
                opp_h = opp_positions[(new_r, new_c)]
                if h >= opp_h:
                    moves_count += 1
                    agent_eat += opp_h #score for just potential eating

                    if h > opp_h:
                        agent_safe_eat += opp_h

                if opp_h >= h:
                    agent_threat += h #gonna be eaten by enemy

            else:
                moves_count += 1 #move to empty cell

        if moves_count <= 1: 
            agent_trapped += 1 #less than or equals to 1 movement i can make (mobility)

        if h >= 2:
            current_agent_cascade_kill, current_agent_cascade_penalty = check_cascade(r,c,h, opp_positions, agent_positions)
            agent_cascade_kill += current_agent_cascade_kill
            agent_cascade_penalty += current_agent_cascade_penalty


    return agent_eat, agent_trapped, agent_threat, agent_safe_eat, agent_cascade_kill, agent_cascade_penalty

def check_cascade(
    r: int, 
    c: int, 
    h: int,
    opp_positions: dict[tuple[int, int], int],
    agent_positions: dict[tuple[int, int], int],
):
    agent_cascade_penalty = 0
    agent_cascade_kill = 0 

    for d in CARDINAL_DIRECTIONS:
        reach = h
        for step in range (1, reach +1):
            new_r = r + (d.r * step)
            new_c = c + (d.c * step)
            if not (0 <= new_r <= 7 and 0 <= new_c <= 7):
                agent_cascade_penalty += (reach - step + 1) #to check if i loss my own agent if i cascade
                break

            push_steps = reach - step + 1
            final_r = new_r + d.r * push_steps
            final_c = new_c + d.c * push_steps

            if (new_r, new_c) in opp_positions:
                
                enemy_height = opp_positions[(new_r,new_c)]
                if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                    agent_cascade_kill += enemy_height
                
            elif (new_r, new_c) in agent_positions:
                own_height = agent_positions[(new_r, new_c)]

                if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                    agent_cascade_penalty += own_height #losing our own agent
                else:
                    before_edge = min(new_r, 7 - new_r, new_c, 7 - new_c)
                    after_edge = min(final_r, 7 - final_r, final_c, 7 - final_c)
                    if after_edge < before_edge:
                        agent_cascade_penalty += 1 #push ourselves TOWARDS THE EDGES

    return agent_cascade_kill, agent_cascade_penalty

def all_legal_actions(
    self,
    board: Board
) -> list[Action]:
    """
    Generate all possible valid actions during Play phase 
    """
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
    print(f"nodes expanded = {self._nodes_expanded}")
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

            # penalise heavy on threefold repetition
            if count_repetition:
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
    self._nodes_expanded += 1 
    
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

def action_order_score(
    board: Board, 
    action: Action
) -> int:
    coord = action.coord
    d = action.direction
    if isinstance(action, EatAction):
        target = Coord(coord.r + d.r, coord.c + d.c)

        victim = board._state[target]
        attacker = board._state[coord]

        return 10000 + (attacker.height - victim.height) * 100 + victim.height * 10 

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

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase   

from referee.game import Board
import math

def choose_best_action(self,board,depth) -> Action: #The big picture of min max
    best_action = None
    best_score = -math.inf
    possible_actions = all_legal_actions(self,board)
    for each_action in possible_actions:
        board.apply_action(each_action)
        maximizing = False
        curr_score = min_max_algo(self, maximizing, board, depth-1, alpha= -math.inf, beta = math.inf) 
        board.undo_action()

        if curr_score > best_score:
            best_score = curr_score
            best_action = each_action
             
    print(f"nodes expanded = {self._nodes_expanded}")
    return best_action

def min_max_algo(self, maximizing, board, depth, alpha, beta) -> int: #Each depth of min max
    """
    Determine the next action using min_max algo
    """
    #Move, eat and cascade
    #Red always goes first -> Max
    self._nodes_expanded += 1 
    if board.game_over or (not board._has_legal_actions()) or depth == 0:
        return heuristic_func(self,board,self._color)
    
    possible_actions = all_legal_actions(self,board)
    if maximizing == True:
        best_score = -math.inf
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(self,False, board, depth - 1,alpha,beta)
            board.undo_action()
            best_score = max(best_score, new_score)
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_score
    
    elif maximizing == False:
        best_score = math.inf
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(self,True, board, depth - 1,alpha,beta)
            board.undo_action()
            best_score = min(best_score, new_score)
            beta = min(beta, best_score)
            if alpha >= beta:
                break

        return best_score

    return 0
