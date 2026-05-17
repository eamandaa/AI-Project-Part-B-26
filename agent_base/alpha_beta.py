from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase, CellState

from referee.game import Board, CellMutation, BoardMutation
import math
from .zobrist_hashing import compute_hash, ScoreFlag
import time 
from referee.game import BOARD_N
import math

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




#Heuristic func that split tokens into smaller one,
#  run away from red and only eat when possible, so does not really chase the enemy token


def heuristic_func(self, board, agent_color) -> int:
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
        else:
            return -5000

    agent_positions = {}
    opp_positions = {}

    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        pos = (coord.r, coord.c)

        if cell.color == agent_color:
            agent_positions[pos] = cell.height
        else:
            opp_positions[pos] = cell.height

    if not agent_positions:
        return -100000

    if not opp_positions:
        return 100000

    agent_total = sum(agent_positions.values())
    opp_total = sum(opp_positions.values())

    agent_largest = max(agent_positions.values())
    opp_largest = max(opp_positions.values())

    score = 0

    score += 32 * (agent_total - opp_total)
    score += 12 * (agent_largest - opp_largest)

    # spread out token
    score += 9 * spread_score(agent_positions)
    score -= 7 * spread_score(opp_positions)

    score += 2 * escape_score(agent_positions, opp_positions)
    score -= 2 * escape_score(opp_positions, agent_positions)

    score += 2 * open_space_score(agent_positions, opp_positions)
    score -= 1 * open_space_score(opp_positions, agent_positions)

    # eat score
    score += 3 * safe_eat_score(agent_positions, opp_positions)
    score -= 2 * safe_eat_score(opp_positions, agent_positions)

    # chase abit to our enemy token that is bigger than us
    score += 7 * edible_hunter_score(agent_positions, opp_positions)
    score -= 5 * edible_hunter_score(opp_positions, agent_positions)

    # surviving score
    score += survival_stack_score(agent_positions, opp_positions)
    score -= survival_stack_score(opp_positions, agent_positions)

    # cascade score
    score += cascade_pressure_score(agent_positions, opp_positions)
    score -= cascade_pressure_score(opp_positions, agent_positions)

    # merge with our own token if opponent is bigger
    score += build_if_weaker_score(agent_positions, opp_positions)

    # endgame situation
    score += top_blue_endgame_score(agent_positions, opp_positions)

    return score


def spread_score(positions: dict[tuple[int, int], int]) -> int:
    """
    Give score when it spreads away
    """
    items = list(positions.items())
    score = 0

    for i in range(len(items)):
        (r1, c1), h1 = items[i]

        for j in range(i + 1, len(items)):
            (r2, c2), h2 = items[j]

            dist = abs(r1 - r2) + abs(c1 - c2)
            small_h = min(h1, h2)

            if 2 <= dist <= 5:
                score += 4 * small_h
            elif dist == 1:
                score -= 6 * small_h
            elif dist >= 7:
                score -= 1 * small_h

    return score




def escape_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    if it gets close to an enemy, minus the score
    """
    score = 0

    for (r, c), h in my_positions.items():
        closest_danger_dist = math.inf
        closest_danger_h = 0

        for (er, ec), eh in enemy_positions.items():
            if eh >= h:
                dist = abs(r - er) + abs(c - ec)

                if dist < closest_danger_dist:
                    closest_danger_dist = dist
                    closest_danger_h = eh

        if closest_danger_dist == 1:
            score -= 220 * h
            score -= 35 * closest_danger_h

        elif closest_danger_dist == 2:
            score -= 90 * h
            score -= 20 * closest_danger_h

        elif closest_danger_dist == 3:
            score -= 30 * h

        elif closest_danger_dist < math.inf:
            score += 18 * h

    return score





def open_space_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    if there is more space to go, give more score
    """
    score = 0

    for (r, c), h in my_positions.items():
        free_sides = 0 
        blocked_sides = 0

        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                blocked_sides += 1
                continue

            if (nr, nc) in my_positions or (nr, nc) in enemy_positions:
                blocked_sides += 1
            else:
                free_sides += 1

        score += 25 * free_sides
        score -= 18 * blocked_sides


        if h <= 2:
            score += 15 * free_sides

        # dont go to edge
        edge_dist = min(r, 7 - r, c, 7 - c)
        if edge_dist == 0:
            score -= 45 * h
        elif edge_dist == 1:
            score -= 18 * h

    return score



def safe_eat_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    eat only when it is safe
    """
    score = 0

    for (r, c), h in my_positions.items():
        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if (nr, nc) not in enemy_positions:
                continue

            enemy_h = enemy_positions[(nr, nc)]

            if h >= enemy_h:
                value = 0

                # Basic eat reward
                value += 130 * enemy_h

                # Strictly stronger eat is much better
                if h > enemy_h:
                    value += 90 * enemy_h
                else:
                    value += 20 * enemy_h

                # Check if eating lands beside another equal/stronger enemy
                exposed = False

                for adj_d in CARDINAL_DIRECTIONS:
                    ar = nr + adj_d.r
                    ac = nc + adj_d.c

                    if (ar, ac) in enemy_positions and (ar, ac) != (nr, nc):
                        other_h = enemy_positions[(ar, ac)]

                        if other_h >= h:
                            exposed = True
                            value -= 160 * h

                if not exposed:
                    value += 100

                score += value

            else:
                # can be eaten
                score -= 150 * h

    return score




def edible_hunter_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    dont chase bigger pieces, only when it is smaller than us
    """
    score = 0

    for (r, c), h in my_positions.items():
        best_dist = math.inf
        best_target_h = 0
        closest_stronger = math.inf

        for (er, ec), eh in enemy_positions.items():
            dist = abs(r - er) + abs(c - ec)

            if h >= eh:
                if dist < best_dist:
                    best_dist = dist
                    best_target_h = eh
            else:
                closest_stronger = min(closest_stronger, dist)

        if best_dist < math.inf:
            score += max(0, 8 - best_dist) * 12 * best_target_h

            if best_dist == 1:
                score += 250 * best_target_h
            elif best_dist == 2:
                score += 90 * best_target_h
            elif best_dist == 3:
                score += 35 * best_target_h

        # Run from stronger target
        if closest_stronger == 1:
            score -= 220 * h
        elif closest_stronger == 2:
            score -= 90 * h
        elif closest_stronger == 3:
            score -= 30 * h

    return score



def survival_stack_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    keep small pieces
    """
    score = 0

    for (r, c), h in my_positions.items():
        nearest_enemy = math.inf
        nearest_stronger = math.inf
        free_sides = 0

        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if 0 <= nr <= 7 and 0 <= nc <= 7:
                if (nr, nc) not in my_positions and (nr, nc) not in enemy_positions:
                    free_sides += 1

        for (er, ec), eh in enemy_positions.items():
            dist = abs(r - er) + abs(c - ec)
            nearest_enemy = min(nearest_enemy, dist)

            if eh >= h:
                nearest_stronger = min(nearest_stronger, dist)

        # Small pieces should be slippery and not adjacent.
        if h <= 2:
            score += 30 * free_sides

            if nearest_stronger == 1:
                score -= 180 * h
            elif nearest_stronger == 2:
                score -= 70 * h

            if nearest_enemy >= 3:
                score += 20

        # Big pieces can hold ground but still need mobility.
        else:
            score += 12 * free_sides

            if nearest_stronger == 1:
                score -= 110 * h

    return score


# ============================================================
# 7. CASCADE PRESSURE SCORE
# ============================================================

def cascade_pressure_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    Use cascade for kill, push, escape, disruption.
    Avoid exploding big stacks for no reason.
    """
    score = 0

    for (r, c), h in my_positions.items():
        if h < 2:
            continue

        for d in CARDINAL_DIRECTIONS:
            cascade_kill = 0
            cascade_push = 0
            cascade_hit = 0
            self_loss = 0

            for step in range(1, h + 1):
                nr = r + d.r * step
                nc = c + d.c * step

                if not (0 <= nr <= 7 and 0 <= nc <= 7):
                    self_loss += h - step + 1
                    break

                push_steps = h - step + 1
                final_r = nr + d.r * push_steps
                final_c = nc + d.c * push_steps

                if (nr, nc) in enemy_positions:
                    enemy_h = enemy_positions[(nr, nc)]
                    cascade_hit += enemy_h

                    if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                        cascade_kill += enemy_h
                    else:
                        before_edge = min(nr, 7 - nr, nc, 7 - nc)
                        after_edge = min(final_r, 7 - final_r, final_c, 7 - final_c)

                        if after_edge < before_edge:
                            cascade_push += enemy_h

                elif (nr, nc) in my_positions:
                    own_h = my_positions[(nr, nc)]

                    if not (0 <= final_r <= 7 and 0 <= final_c <= 7):
                        self_loss += own_h

            score += 160 * cascade_kill
            score += 45 * cascade_push
            score += 12 * cascade_hit
            score -= 120 * self_loss

            # Avoid useless big-stack explosion.
            if h >= 5 and cascade_kill == 0 and cascade_push == 0:
                score -= 180

    return score


# ============================================================
# 8. BUILD IF WEAKER
# ============================================================

def build_if_weaker_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    If enemy has biggest stack, merge/build instead of hopeless chasing.
    """
    if not my_positions or not enemy_positions:
        return 0

    my_largest = max(my_positions.values())
    enemy_largest = max(enemy_positions.values())

    if my_largest >= enemy_largest:
        return 0

    score = 0

    for (r, c), h in my_positions.items():
        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if (nr, nc) not in my_positions:
                continue

            new_h = h + my_positions[(nr, nc)]

            score += 45 * new_h

            if new_h >= enemy_largest:
                score += 300

            # Good if new merged stack can eat nearby target.
            for (er, ec), eh in enemy_positions.items():
                dist = abs(nr - er) + abs(nc - ec)

                if new_h >= eh and dist <= 2:
                    score += 80 * eh

            # Bad if merge becomes edible.
            for adj_d in CARDINAL_DIRECTIONS:
                ar = nr + adj_d.r
                ac = nc + adj_d.c

                if (ar, ac) in enemy_positions:
                    enemy_h = enemy_positions[(ar, ac)]

                    if enemy_h >= new_h:
                        score -= 180 * new_h

    return score


# ============================================================
# 9. TOP BLUE ENDGAME
# ============================================================

def top_blue_endgame_score(
    my_positions: dict[tuple[int, int], int],
    enemy_positions: dict[tuple[int, int], int]
) -> int:
    """
    Endgame:
    - if ahead: clean safely
    - if weaker: run/build
    - make opponent chase
    """
    if not my_positions or not enemy_positions:
        return 0

    my_total = sum(my_positions.values())
    enemy_total = sum(enemy_positions.values())

    my_largest = max(my_positions.values())
    enemy_largest = max(enemy_positions.values())

    total_stacks = len(my_positions) + len(enemy_positions)

    if total_stacks > 7 and len(enemy_positions) > 4:
        return 0

    score = 0

    # If ahead, reduce enemy stacks.
    if my_total >= enemy_total:
        score -= 80 * len(enemy_positions)

    # If enemy biggest is bigger, do not chase blindly.
    if enemy_largest > my_largest:
        score += build_if_weaker_score(my_positions, enemy_positions)

        # Reward staying away from the bigger stack.
        for (r, c), h in my_positions.items():
            for (er, ec), eh in enemy_positions.items():
                if eh == enemy_largest and eh > h:
                    dist = abs(r - er) + abs(c - ec)

                    if dist <= 1:
                        score -= 220 * h
                    elif dist == 2:
                        score -= 80 * h
                    elif dist >= 4:
                        score += 35 * h

    # Immediate safe eat is huge.
    for (r, c), h in my_positions.items():
        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if (nr, nc) in enemy_positions:
                enemy_h = enemy_positions[(nr, nc)]

                if h >= enemy_h:
                    score += 350 * enemy_h

                    if h > enemy_h:
                        score += 150 * enemy_h

    # Keep escape routes in endgame.
    score += 2 * open_space_score(my_positions, enemy_positions)

    return score

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
        #return 10000 + (victim.height / attacker.height) * 100
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