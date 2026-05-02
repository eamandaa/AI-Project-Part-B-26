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
        curr_score = min_max_algo(self, False, board, depth, alpha= -math.inf, beta = math.inf) 
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
            if score_flag == ScoreFlag.LOWER_BOUND and stored_value >= beta:
                return stored_value
            if score_flag == ScoreFlag.UPPER_BOUND and stored_value <= alpha:
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
    elif best_score >= beta:
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
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED
    
    # 4 factors: 1. Our total stack height 2. Potential to be eaten 3. Potential for center control
    # 4. Being in the edge  
    # priority: 1. If last token  2. Will see if we can eat our adjacent stacj 3. cascade and ppush it away 4. continue with score func 
    if board.game_over:
        winner = board.winner_color
        if winner == agent_color:
            return 100000  
        elif winner == opp_color:
            return -100000
        else: #DOUBLE CHECK FOR LATER - FOR TIE CONDITION
            return -5000
    
    eat_immediately = False

    #1. height
    agent_total = 0
    opp_total = 0
    # 3. Center Control
    agent_center = 0
    opp_center = 0
    # 4. being in edge
    agent_edge = 0
    opp_edge = 0

    agent_eat_threats = 0
    opp_eat_threats= 0

    agent_cascade_push = 0
    opp_cascade_push = 0

    wasted_cascade_penalty = 0
    agent_capture_bonus = 0

    agent_positions = {} 
    opp_positions = {}    

    for coord, cell in board._state.items():
        if cell.is_empty:
            continue
        if cell.color == opp_color:
            opp_positions[(coord.r, coord.c)] = cell.height
        elif cell.color == agent_color:
            agent_positions[(coord.r, coord.c)] = cell.height

    #if only 1 token of opponent left, need a trap strategy
    if len(opp_positions) == 1:
        opp_r, opp_c = next(iter(opp_positions))
        opp_h = opp_positions[(opp_r, opp_c)]

        # immediate eat check
        for (r, c), h in agent_positions.items():
            dist = abs(r - opp_r) + abs(c - opp_c)
            if dist == 1 and h >= opp_h:
                return 99000

        total_dist = 0
        min_dist = math.inf
        sides_covered = set()
        escape_block_bonus = 0
        cascade_trap_bonus = 0

        if opp_r == 0: sides_covered.add('up')
        if opp_r == 7: sides_covered.add('down')
        if opp_c == 0: sides_covered.add('left')
        if opp_c == 7: sides_covered.add('right')

        # find all squares opp can escape to (adjacent empty squares)
        opp_escape_squares = set()
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = opp_r + dr, opp_c + dc
            if 0 <= nr <= 7 and 0 <= nc <= 7:
                if (nr, nc) not in opp_positions and (nr, nc) not in agent_positions:
                    opp_escape_squares.add((nr, nc))

        for (r, c), h in agent_positions.items():
            dist = abs(r - opp_r) + abs(c - opp_c)
            total_dist += dist
            if dist < min_dist:
                min_dist = dist

            if dist == 1:
                if r < opp_r: sides_covered.add('up')
                if r > opp_r: sides_covered.add('down')
                if c < opp_c: sides_covered.add('left')
                if c > opp_c: sides_covered.add('right')


            # trapping opp
            for (er, ec) in opp_escape_squares:
                esc_dist = abs(r - er) + abs(c - ec)
                if esc_dist == 0:  #  blocking it
                    escape_block_bonus += 5000
                elif esc_dist == 1:  # threatening it
                    escape_block_bonus += 2000

            # cascade opp to corner
            if h >= 2:
                reach = h
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    # Scan path
                    for step in range(1, reach + 1):
                        nr, nc = r + dr * step, c + dc * step
                        if not (0 <= nr <= 7 and 0 <= nc <= 7):
                            break
                        if (nr, nc) == (opp_r, opp_c):
                            # We can cascade into Blue
                            push_r = opp_r + dr * (reach - step)
                            push_c = opp_c + dc * (reach - step)

                            # Pushed off board = win
                            if not (0 <= push_r <= 7 and 0 <= push_c <= 7):
                                cascade_trap_bonus += 30000

                            # Pushed to corner = nearly win
                            elif (push_r in (0,7) and push_c in (0,7)):
                                cascade_trap_bonus += 15000

                            # Pushed to edge = good
                            elif push_r in (0,7) or push_c in (0,7):
                                cascade_trap_bonus += 8000

                            # Pushed toward corner direction = ok
                            else:
                                cascade_trap_bonus += 2000
                            break

        sides_blocked = len(sides_covered)
        corner_bonus = 0
        if sides_blocked >= 3: corner_bonus = 10000
        if sides_blocked == 4: corner_bonus = 50000

        # Fewer escape squares = more trapped
        escape_trapped_bonus = (4 - len(opp_escape_squares)) * 3000

        return (
            50000
            - total_dist * 300
            - min_dist * 800
            + sides_blocked * 3000
            + escape_block_bonus      # block escape routes ← key
            + cascade_trap_bonus      # cascade pushes Blue to corner/off ← key
            + escape_trapped_bonus    # fewer escapes = better
            + corner_bonus
        )

    #Main algo if there are multiple opponent tokens 
    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        is_agent = (cell.color == agent_color)
        
        # reward based on height
        if is_agent:
            agent_total += cell.height
        else:
            opp_total += cell.height 

        # reward based on being centre
        if 3 <= coord.r <= 5 and 3 <= coord.c <= 5:
            if is_agent:
                agent_center += 1
            else:
                opp_center += 1

        # penalise on being edge
        if coord.r == 0 or coord.r == 7 or coord.c == 0 or coord.c == 7:
            if is_agent:
                agent_edge += 1
            else:
                opp_edge += 1
        
        #2. potential to eat
        for direction in CARDINAL_DIRECTIONS:
            try:
                neighbor = coord + direction
            except ValueError:
                continue

            if neighbor not in board._state:
                continue
            neighbor_cell = board._state[neighbor]

            if is_agent and neighbor_cell.color == opp_color:
                if cell.height >= neighbor_cell.height:
                    agent_capture_bonus += neighbor_cell.height * 50 
                    eat_immediately = True


            #unsure good or not currently commented out in the score func
            if is_agent and neighbor_cell.color == opp_color:
                agent_eat_threats += neighbor_cell.height  * 60 
                #if cell.height >= neighbor_cell.height:
                #    eat_immidiately = True
            elif not is_agent and neighbor_cell.color == agent_color:
                opp_eat_threats += cell.height

        #Priority 2 cascade out of the board
        

        if is_agent and cell.height >= 2:
            reach = cell.height

            for d in CARDINAL_DIRECTIONS:
                dr, dc = d.r, d.c

                # scan along direction
                enemy_step = None

                for step in range(1, reach + 1):
                    r = coord.r + dr * step
                    c = coord.c + dc * step

                    if not (0 <= r <= 7 and 0 <= c <= 7):  
                        enemy_in_path = False
                        for step in range(1, reach + 1):
                            r = coord.r + dr * step
                            c = coord.c + dc * step
                            if not (0 <= r <= 7 and 0 <= c <= 7):
                                break
                            if (r, c) in opp_positions:
                                enemy_in_path = True
                                break
                        
                        if not enemy_in_path:
                            # Wasteful cascade  our token falls off , we want to prevent this o penalty
                            wasted_cascade_penalty += cell.height * 30
                    if (r, c) in opp_positions:
                        enemy_step = step
                        break

                if enemy_step is None:
                    continue

                enemy_r = coord.r + dr * enemy_step
                enemy_c = coord.c + dc * enemy_step

                push_steps = reach - enemy_step
                push_r = enemy_r + dr * push_steps
                push_c = enemy_c + dc * push_steps

                pushed_off_board = not (0 <= push_r <= 7 and 0 <= push_c <= 7)

                if is_agent:
                    if pushed_off_board:
                        agent_cascade_push += cell.height * 50
                    else:
                        agent_cascade_push += cell.height * 2
                else:
                    if pushed_off_board:
                        opp_cascade_push += cell.height * 50
                    else:
                        opp_cascade_push += cell.height* 2

    # sounds risky
    if eat_immediately:
        return 90000

    # #make a roken chase another one and not wonder aimlessly
    # focus_bonus = 0
    # for (opp_r, opp_c), opp_h in opp_positions.items():
    #     min_dist = math.inf
    #     for (r, c), h in agent_positions.items():
    #         dist = abs(r - opp_r) + abs(c - opp_c)
    #         if dist < min_dist:
    #             min_dist = dist
    #     # Closer = higher bonus
    #     focus_bonus += max(0, 20 - min_dist) * 200  # max bonus when dist=0

    # # Also penalise tokens that are far from ALL enemies (wandering)
    # wander_penalty = 0
    # for (r, c), h in agent_positions.items():
    #     min_dist_to_opp = math.inf
    #     for (opp_r, opp_c) in opp_positions:
    #         dist = abs(r - opp_r) + abs(c - opp_c)
    #         if dist < min_dist_to_opp:
    #             min_dist_to_opp = dist
    #     if min_dist_to_opp > 5:  # too far from any enemy
    #         wander_penalty += min_dist_to_opp * 50

    # Normal score
    return (
        10 * (agent_total - opp_total)
        #+ 8  * (agent_eat_threats - opp_eat_threats)
        + 1  * (agent_cascade_push - opp_cascade_push)
        + 2  * (agent_center - opp_center)
        - 1  * (agent_edge - opp_edge)
        #+ 5 * agent_block
        + 1 * agent_capture_bonus
        - wasted_cascade_penalty
        # + focus_bonus      # ← reward chasing nearest enemy
        # - wander_penalty
    )

def manhanttan_distance(
    coord_one: Coord,
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)

def _evaluate_eat(
    opponents_stacks:dict[tuple[int, int], int],
    curr_coord: Coord,
    curr_cell_state: CellState,
) -> int:
    """
    Evaluate how likely the agent could eat the opponents, and 
    how likely we are being eaten by opponents
    """

    eat_score = 0
    curr_cell_height = curr_cell_state.height

    for (opponent_r, opponent_c), opponent_height in opponents_stacks.items():
        distance = manhanttan_distance(curr_coord, Coord(opponent_r, opponent_c))

        # unlikely to happen, but just for safe guard
        if distance == 0:
            continue
        
        # skip stacks that are too far away
        if distance > 4:
            continue

        current_eat_score = 0
        
        height_difference = abs(curr_cell_height - opponent_height)

        if curr_cell_height >= opponent_height:
            current_eat_score += height_difference
        else:
            current_eat_score -= height_difference

        # more important 
        if distance <= 2:
            weight = 2
        # could be a threat/potential eat
        elif distance <= 4:
            weight = 1

        eat_score += current_eat_score * weight

    return eat_score

def evaluate_cascade_off_board(
    opponents_stacks:dict[tuple[int, int], int],
    curr_coord: Coord,
    curr_cell_state: CellState,
    board: Board
)-> int:
    """
    On the given position, how likely you are being pushed off the board
    and how likely you can push the enemy off the board
    """
    cascade_score = 0
    curr_cell_height = curr_cell_state.height

    distance_curr_cord_r_to_edge = min(curr_coord.r, BOARD_N - curr_coord.r)
    distance_curr_cord_c_to_edge = min(curr_coord.c, BOARD_N - curr_coord.c)
    min_distance_curr_cord = min(distance_curr_cord_c_to_edge, distance_curr_cord_r_to_edge)

    for (opponent_r, opponent_c), opponent_height in opponents_stacks.items():

        # cascade can only happen in same row or same column
        if opponent_r != curr_coord.r and opponent_c != curr_coord.c:
            continue
        
        distance_opponent_r_to_edge = min(opponent_r, BOARD_N - opponent_r)
        distance_opponent_c_to_edge = min(opponent_c, BOARD_N - opponent_c)

        min_distance_opponent = min(distance_opponent_c_to_edge, distance_opponent_r_to_edge)

    return 0






""""
    #In case of game over
    if board.game_over:
        winner = board.winner_color
        if winner == agent_color:
            return 100000
        elif winner == opp_color:
            return -100000
        else:
            return -5000
        
    #1. height
    agent_total = 0
    opp_total = 0
    # 3. Center Control
    agent_center = 0
    opp_center = 0
    # 4. being in edge
    agent_edge = 0
    opp_edge = 0

    agent_eat_threats = 0
    opp_eat_threats= 0

    agent_cascade_push = 0
    opp_cascade_push = 0

    for coord, cell in board._state.items():
        is_agent = (cell.color == agent_color)
        if cell.is_empty:
            continue
        if cell.color == agent_color:
            agent_total += cell.height
        else:
            opp_total += cell.height 

        if 3 <= coord.r <= 5 and 3 <= coord.c <= 5:
            if cell.color == agent_color:
                agent_center += 1
            else:
                opp_center += 1

        if coord.r == 0 or coord.r == 7 or coord.c == 0 or coord.c == 7:
            if cell.color == agent_color:
                agent_edge += 1
            else:
                opp_edge += 1

        #2. potential to eat
        for direction in CARDINAL_DIRECTIONS:
            try: 
                neighbor = coord + direction 
            except ValueError: 
                continue

            neighbor_cell = board._state[neighbor]

            if neighbor_cell.is_empty:
                continue

            if is_agent and neighbor_cell.color == opp_color:
                agent_eat_threats += neighbor_cell.height  

            elif (not is_agent) and neighbor_cell.color == agent_color:
                opp_eat_threats += neighbor_cell.height
    
    
        #Heuristic taking account of cascade and push
        if is_agent and cell.height >= 2:
                reach = cell.height
                # check if enemy is in same row or col within cascade reach
                dr = abs(coord.r - neighbor.r)
                dc = abs(coord.c - neighbor.c)
                if neighbor_cell.color == opp_color:
                    if dr == 0 and dc <= reach:  # same row, can cascade
                        # bonus if push sends them toward edge
                        push_col = neighbor.c + (reach - dc)
                        if push_col >= 7 or push_col <= 0:
                            agent_cascade_push += cell.height * 2  # big bonus near edge
                        else:
                            agent_cascade_push += cell.height
                    if dc == 0 and dr <= reach:  # same col, can cascade
                        push_row = neighbor.r + (reach - dr)
                        if push_row >= 7 or push_row <= 0:
                            agent_cascade_push += cell.height * 2
                        else:
                            agent_cascade_push += cell.height

        elif not is_agent and neighbor_cell.color == agent_color:#Count for opponent
            if cell.height >= 2:
                reach = cell.height
                dr = abs(coord.r - neighbor.r)
                dc = abs(coord.c - neighbor.c)
                if dr == 0 and dc <= reach:
                    push_col = neighbor.c + (reach - dc)
                    if push_col >= 7 or push_col <= 0:
                        opp_cascade_push += cell.height * 2
                    else:
                        opp_cascade_push += cell.height
                if dc == 0 and dr <= reach:
                    push_row = neighbor.r + (reach - dr)
                    if push_row >= 7 or push_row <= 0:
                        opp_cascade_push += cell.height * 2
                    else:
                        opp_cascade_push += cell.height
    
    height_score = agent_total - opp_total
    center_score = agent_center - opp_center
    edge_score = agent_edge - opp_edge
    eat_threat_score = agent_eat_threats - opp_eat_threats
    cascade_score = agent_cascade_push - opp_cascade_push

    score = (
        10 * height_score
        + 8 * eat_threat_score
        + 6 * cascade_score
        + 2 * center_score
        - 1 * edge_score
    )
    
    return score
"""
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

"""
def all_legal_actions(self,board) -> list[Action]:
    action_list = []
    cascade_actions = []
    move_actions = []
    for current_coord, cell in board._state.items():
        if cell.is_empty:
            continue
        if cell.color != board.turn_color:
            continue
        for direction in CARDINAL_DIRECTIONS:
            current_r , current_c = current_coord.r, current_coord.c
            current_color, current_height = cell.color, cell.height
       
            if direction == Direction.Up:    
                if current_r == 0: 
                    continue
                new_coord = Coord(current_r - 1, current_c)
            elif direction == Direction.Down: 
                if current_r == 7: 
                    continue
                new_coord = Coord(current_r + 1, current_c)
            elif direction == Direction.Left: 
                if current_c == 0: 
                    continue
                new_coord = Coord(current_r, current_c - 1)
            else:                            
                if current_c == 7: continue
                new_coord = Coord(current_r, current_c + 1)
            
            

            neighbour = board._state.get(new_coord)
            #EAT
            if neighbour is not None and not neighbour.is_empty:
                if neighbour.color != current_color:
                    if current_height >= neighbour.height:
                        action_list.append(EatAction(current_coord, direction))

    
            # MOVE 
   
            if neighbour is None or neighbour.is_empty or neighbour.color == current_color:
                action_list.append(MoveAction(current_coord, direction))

            # CASCADE 
            if current_height >= 2:
                action_list.append(CascadeAction(current_coord, direction))


    return action_list
"""

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