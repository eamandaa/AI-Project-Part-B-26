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


import math
import time

# Assumes these already exist from the template/referee:
# Board, PlayerColor, Coord
# MoveAction, EatAction, CascadeAction
# CARDINAL_DIRECTIONS


# ============================================================
# BASIC POSITION EXTRACTION
# ============================================================

def get_positions(board, agent_color):
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED

    agent_positions = {}
    opp_positions = {}

    agent_total = 0
    opp_total = 0
    agent_largest = 0
    opp_largest = 0

    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        r, c = coord.r, coord.c
        h = cell.height

        if cell.color == agent_color:
            agent_positions[(r, c)] = h
            agent_total += h
            agent_largest = max(agent_largest, h)
        else:
            opp_positions[(r, c)] = h
            opp_total += h
            opp_largest = max(opp_largest, h)

    return (
        agent_positions,
        opp_positions,
        agent_total,
        opp_total,
        agent_largest,
        opp_largest,
    )


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ============================================================
# 1. MATERIAL + STACK STRUCTURE
# ============================================================

def material_score(agent_positions, opp_positions):
    agent_total = sum(agent_positions.values())
    opp_total = sum(opp_positions.values())

    agent_largest = max(agent_positions.values()) if agent_positions else 0
    opp_largest = max(opp_positions.values()) if opp_positions else 0

    agent_stacks = len(agent_positions)
    opp_stacks = len(opp_positions)

    score = 0

    # Material matters, but not too much.
    score += 45 * (agent_total - opp_total)

    # Preserve useful big stacks.
    score += 18 * (agent_largest - opp_largest)

    # Having more stacks can help survival/spread,
    # but too many weak stacks can also be bad.
    score += 4 * (agent_stacks - opp_stacks)

    return score


# ============================================================
# 2. SPREAD / SLIPPERY MOVEMENT
# ============================================================

def spread_score(positions):
    """
    BLUE-like behaviour:
    Do not clump everything together.
    Spread moderately so opponent has to chase.
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
                score += 3 * small_h

            elif dist == 1:
                score -= 4 * small_h

            elif dist >= 7:
                # Too far apart can become useless,
                # but still not as bad as clumping.
                score -= 1 * small_h

    return score


# ============================================================
# 3. ESCAPE / SAFETY
# ============================================================

def escape_score(my_positions, enemy_positions):
    """
    Strong BLUE behaviour:
    If enemy is equal/stronger and close, run away.
    """
    score = 0

    for (r, c), h in my_positions.items():
        closest_danger = math.inf

        for (er, ec), eh in enemy_positions.items():
            if eh >= h:
                dist = abs(r - er) + abs(c - ec)
                closest_danger = min(closest_danger, dist)

        if closest_danger == 1:
            score -= 120 * h
        elif closest_danger == 2:
            score -= 45 * h
        elif closest_danger == 3:
            score -= 12 * h
        elif closest_danger < math.inf:
            score += 5 * h

    return score


def empty_move_danger_score(my_positions, enemy_positions):
    """
    Penalise positions where our piece is directly beside
    equal/stronger enemy.
    """
    score = 0

    for (r, c), h in my_positions.items():
        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if (nr, nc) in enemy_positions:
                enemy_h = enemy_positions[(nr, nc)]

                if enemy_h >= h:
                    score -= 100 * h
                elif h > enemy_h:
                    score += 30 * enemy_h

    return score


# ============================================================
# 4. SAFE EAT / TACTICAL EAT
# ============================================================

def eat_score(my_positions, enemy_positions):
    """
    Eat when it is safe/profitable, not blindly.
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
                # Any legal eat is useful.
                score += 70 * enemy_h

                # Strictly stronger eat is safer.
                if h > enemy_h:
                    score += 45 * enemy_h
                else:
                    # Equal-height eat can be okay, but less safe.
                    score += 10 * enemy_h

            else:
                # Enemy can eat us.
                score -= 90 * h

    return score


# ============================================================
# 5. HUNTER PRESSURE
# ============================================================

def hunter_pressure(my_positions, enemy_positions):
    """
    Move strong stacks toward targets they can actually eat.
    Do not chase impossible targets.
    """
    score = 0

    for (r, c), h in my_positions.items():
        best_dist = math.inf
        best_target_h = 0

        for (er, ec), eh in enemy_positions.items():
            if h >= eh:
                dist = abs(r - er) + abs(c - ec)

                if dist < best_dist:
                    best_dist = dist
                    best_target_h = eh

        if best_dist < math.inf:
            score += max(0, 8 - best_dist) * 10 * best_target_h

            if best_dist == 1:
                score += 120 * best_target_h
            elif best_dist == 2:
                score += 40 * best_target_h

    return score


# ============================================================
# 6. CLEANUP PRESSURE
# ============================================================

def cleanup_score(agent_positions, opp_positions):
    """
    If winning on material, stop letting opponent survive with many small stacks.
    """
    agent_total = sum(agent_positions.values())
    opp_total = sum(opp_positions.values())

    if agent_total >= opp_total:
        return -25 * len(opp_positions)

    return 0


# ============================================================
# 7. BUILD / MERGE MODE
# ============================================================

def build_mode_score(my_positions, enemy_positions):
    """
    If enemy has a bigger stack, merge/build instead of chasing.
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

            # Reward making bigger stack.
            score += 35 * new_h

            # Big bonus if merge can match/beat enemy biggest.
            if new_h >= enemy_largest:
                score += 250

            # But do not merge beside stronger/equal enemy.
            for adj_d in CARDINAL_DIRECTIONS:
                ar = nr + adj_d.r
                ac = nc + adj_d.c

                if (ar, ac) in enemy_positions:
                    enemy_h = enemy_positions[(ar, ac)]

                    if enemy_h >= new_h:
                        score -= 160 * new_h

    return score


# ============================================================
# 8. EDGE / TRAP SCORE
# ============================================================

def edge_score(my_positions, enemy_positions):
    """
    Being near edge is risky if enemy can cascade/push us.
    But forcing enemy to edge is good.
    """
    score = 0

    for (r, c), h in my_positions.items():
        edge_dist = min(r, 7 - r, c, 7 - c)

        if edge_dist == 0:
            score -= 18 * h
        elif edge_dist == 1:
            score -= 7 * h

    for (r, c), h in enemy_positions.items():
        edge_dist = min(r, 7 - r, c, 7 - c)

        if edge_dist == 0:
            score += 15 * h
        elif edge_dist == 1:
            score += 6 * h

    return score


def trapped_score(my_positions, enemy_positions):
    """
    Reward trapping enemies; avoid being trapped.
    """
    score = 0

    for (r, c), h in my_positions.items():
        free = 0

        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                continue

            if (nr, nc) not in my_positions and (nr, nc) not in enemy_positions:
                free += 1

        if free <= 1:
            score -= 35 * h

    for (r, c), h in enemy_positions.items():
        free = 0

        for d in CARDINAL_DIRECTIONS:
            nr = r + d.r
            nc = c + d.c

            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                continue

            if (nr, nc) not in my_positions and (nr, nc) not in enemy_positions:
                free += 1

        if free <= 1:
            score += 30 * h

    return score


# ============================================================
# 9. CASCADE SCORE
# ============================================================

def cascade_score(my_positions, enemy_positions):
    """
    Reward useful cascades:
    - kill enemy off board
    - push enemy closer to edge
    - hit multiple enemies

    Penalise:
    - self-loss
    - big stack exploding for no benefit
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

            score += 130 * cascade_kill
            score += 35 * cascade_push
            score += 10 * cascade_hit
            score -= 90 * self_loss

            # Do not explode big stack for no real value.
            if h >= 5 and cascade_kill == 0 and cascade_push == 0:
                score -= 120

    return score


# ============================================================
# 10. ENDGAME SCORE
# ============================================================

def endgame_score(agent_positions, opp_positions):
    """
    Endgame:
    - eat now
    - clean small stacks
    - chase only edible targets
    - trap
    - build if opponent has bigger stack
    """
    if not agent_positions or not opp_positions:
        return 0

    agent_total = sum(agent_positions.values())
    opp_total = sum(opp_positions.values())

    agent_largest = max(agent_positions.values())
    opp_largest = max(opp_positions.values())

    endgame = 0

    is_endgame = len(opp_positions) <= 4 or (len(agent_positions) + len(opp_positions) <= 6)

    if not is_endgame:
        return 0

    # If ahead, reduce opponent stacks.
    if agent_total >= opp_total:
        endgame -= 60 * len(opp_positions)

    # If behind in largest stack, build.
    if opp_largest > agent_largest:
        endgame += build_mode_score(agent_positions, opp_positions)

    for (orow, ocol), oh in opp_positions.items():
        closest = math.inf
        second = math.inf
        immediate_eat = 0
        near_hunter = 0
        blocked = 0
        free = 0

        for d in CARDINAL_DIRECTIONS:
            nr = orow + d.r
            nc = ocol + d.c

            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                blocked += 1
            elif (nr, nc) in agent_positions:
                blocked += 1
            else:
                free += 1

        for (r, c), h in agent_positions.items():
            dist = abs(r - orow) + abs(c - ocol)

            if dist < closest:
                second = closest
                closest = dist
            elif dist < second:
                second = dist

            if h >= oh:
                if dist == 1:
                    immediate_eat += oh
                elif dist <= 3:
                    near_hunter += oh

            # danger: our smaller stack close to bigger enemy
            if h < oh and dist <= 2:
                endgame -= 35 * h

        # Actual eat pressure should be much stronger than chasing.
        endgame += 350 * immediate_eat
        endgame += 35 * near_hunter

        # Chasing reward is deliberately small.
        if closest < math.inf:
            endgame += max(0, 8 - closest) * 6

        if second < math.inf:
            endgame += max(0, 8 - second) * 2

        # Trap but do not overrate it.
        endgame += 25 * blocked
        endgame -= 10 * free

    return endgame


# ============================================================
# MAIN HEURISTIC FUNCTION
# ============================================================

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

    (
        agent_positions,
        opp_positions,
        agent_total,
        opp_total,
        agent_largest,
        opp_largest,
    ) = get_positions(board, agent_color)

    if not agent_positions:
        return -100000

    if not opp_positions:
        return 100000

    score = 0

    # Core
    score += material_score(agent_positions, opp_positions)

    # BLUE-like slippery behaviour
    score += 5 * (spread_score(agent_positions) - spread_score(opp_positions))
    score += 1 * (escape_score(agent_positions, opp_positions) - escape_score(opp_positions, agent_positions))

    # Tactics
    score += 1 * (eat_score(agent_positions, opp_positions) - eat_score(opp_positions, agent_positions))
    score += 7 * (hunter_pressure(agent_positions, opp_positions) - hunter_pressure(opp_positions, agent_positions))

    # Position/survival
    score += edge_score(agent_positions, opp_positions)
    score += trapped_score(agent_positions, opp_positions)

    # Cascade
    score += cascade_score(agent_positions, opp_positions)
    score -= cascade_score(opp_positions, agent_positions)

    # Cleanup and build
    score += cleanup_score(agent_positions, opp_positions)
    score += build_mode_score(agent_positions, opp_positions)

    # Endgame
    score += endgame_score(agent_positions, opp_positions)

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