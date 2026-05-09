"""
The idea of the placement phase
- Use minimax, alpha-beta pruning and heuristic to find the best spot to place

Heuristic:
1. Centre 
- more mobility
- more cascade direction
- less risk of being pushed off from edge (as we are staying away from the edge)

2. Reach enemy but avoid being eaten
- attack potential: how quickly we can get adjacent to enemy stack
- danger: can enemy stack eat us immediately once play starts
penalise heavy on being adjacent to enemy since enemy can eat us immediately

3. Avoid being pushed off board after placement phase
why? 
- opponent can just cascade and pushed off the board
- if there is forced cascade (from both ourselves or enemy), we might just fall off

4. Friendly merge potential
why? build height advantage earlier
things to be aware: all same colours stack being too clustered


Improvement that has been made
- Moving order for sorting the possible placement action
- Precompute the score for distance to centre and distance to edge
- Transposition table with Zobrist hashing and Iterative deepening 
--> avoiding visit the same state with different move
- Having timeout for iterative deepening so we can search deeper 
and effective depth updated so lesser computation before timeout

Potential improvement
1. Check with higher timeout to allow deeper search
- Current depth ends at 3 at this moment 
"""

import time 

from referee.game import Board, Coord, constants, PlayerColor, CARDINAL_DIRECTIONS, Action, PlaceAction, IllegalActionException
from .zobrist_hashing import compute_hash, ScoreFlag

def manhanttan_distance(
    coord_one: Coord,
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)

def compute_distance_heatmap():
    '''
    Save the distance and score in a heatmap and lookup later 
    '''
    heatmap = []
    for r in range(constants.BOARD_N):
        row = []
        for c in range(constants.BOARD_N):
            coord = Coord(r, c)
            combined_score = score_distance_to_centre(coord) + score_distance_to_edges(coord)
            row.append(combined_score)
        heatmap.append(row)

    return heatmap

def score_distance_to_centre(
    curr_coord: Coord
 ) -> int:
    dist_r = 0
    dist_c = 0

    # near to the centre 
    if 3 <= curr_coord.r <= 5:
        dist_r = 5
    # on the edges
    elif curr_coord.r == 0 or curr_coord.r == 7:
        dist_r = 1
    else:
        dist_r = 2
    
    # near to the centre
    if 3 <= curr_coord.c <= 5:
        dist_c = 5
    elif curr_coord.c == 0 or curr_coord.c == 7:
        dist_c = 1
    else:
        dist_c = 2
         
    final_score = dist_r + dist_c

    return final_score


def score_distance_to_edges(
    curr_coord: Coord,
) -> int:
    """
    Consider how close we are to the edges 
    - Mobility
    - Avoid being trapped in an area 
    """

    dist_r = min(curr_coord.r, 7 - curr_coord.r)
    dist_c = min(curr_coord.c, 7 - curr_coord.c)

    distance_from_edge = min(dist_c, dist_r)

    return distance_from_edge * 2

def score_push_off_board_risk(
    curr_coord: Coord,
    friend_coord: list[Coord],
    enemy_coord: list[Coord],
    board: Board
) -> int:
    """
    Evaluate the risk of being pushed off the board by enemy's possible Cascade action
    """
    
    penalty = 0

    # no enemy so we dont need to worry about
    if not enemy_coord:
        return 0
    
    for direction in CARDINAL_DIRECTIONS:
        for steps_behind in range(1,4):
            behind_r = curr_coord.r - direction.r * steps_behind
            behind_c = curr_coord.c - direction.c * steps_behind
            
            # invalid coord
            if not board._is_within_bounds(behind_r, behind_c):
                break
            
            behind = Coord(behind_r, behind_c)
            if behind not in enemy_coord:
                continue

            spaces_to_edge = 0
            chain_penalty = 0
            front = curr_coord

            for i in range(1,4):
                front_r = front.r + direction.r 
                front_c = front.c + direction.c

                # we get pushed off the board
                if not board._is_within_bounds(front_r, front_c):
                    chain_penalty += (4 - spaces_to_edge) * 4
                    break
                
                front = Coord(front.r + direction.r, front.c + direction.c)

                # a higher potential that friendly stack and our stack pushed away from board together
                if front in friend_coord:
                    chain_penalty += 2
                    break
                else:
                    spaces_to_edge += 1

            # weight the penalty based on the distance of the enemy and our stacks 
            penalty += chain_penalty // steps_behind
    
    return penalty

def score_eat(
    curr_empty_coord : Coord,
    enemy_coords: list[Coord],
) -> int :
    """
    Consider whether the current stack in a safe position to attack 
    """

    if not enemy_coords:
        return 0
    
    # find the minimum distance between 
    min_dist = float('inf')
    for enemy in enemy_coords:
        curr_dist = manhanttan_distance(enemy, curr_empty_coord)

        # illegal action to put next to enemy
        if curr_dist == 1:
            continue

        if curr_dist < min_dist:
            min_dist = curr_dist

        # smallest possible distance 
        if min_dist == 2:
            break

    if min_dist == 2:
        return 5
    elif min_dist == 3:
        return 3
    else:
        return 0
    
def score_friendly_merge(
    curr_coord: Coord,
    friend_coords: list[Coord],
) -> int:
    """
    Update the score based on the number of potential merge
    """
    
    if not friend_coords:
        return 0
    
    score = 0
    adjacent_count = 0

    for coord in friend_coords:
        if coord == curr_coord:
            continue

        dist = manhanttan_distance(coord, curr_coord)
        if dist == 1:
            adjacent_count += 1
        elif dist == 2:
            score += 2  
        elif dist == 3:
            score += 1  

    # having a neighbour is fine 
    if adjacent_count == 1:
        score += 2
    #avoid clusters 
    elif adjacent_count == 2:
        score -= 2
    elif adjacent_count >=3 : 
        score -= 6
        
    return score

def evaluate_board(
    board:Board,
    my_colour: PlayerColor,
    distance_heatmap : list[list[int]]
) -> int:
    """
    Calculate the gap between my stacks and enemy's stacks
    """

    categories = {
        "my_stack" : [],
        "enemy_stack" : [],
    }

    for curr_coord, curr_cell_state in board._state.items():
        if not curr_cell_state.is_stack:
            continue
        elif curr_cell_state.color == my_colour:
            categories['my_stack'].append(curr_coord)
        elif curr_cell_state.color != my_colour:
            categories['enemy_stack'].append(curr_coord)

    score = 0

    for my_coord in categories['my_stack']:
        # distance from centre to current coordinate
        # distance = manhanttan_distance(my_coord, coord_centre)
        # score += (10 - distance)

        score += distance_heatmap[my_coord.r][my_coord.c]
        score -= score_push_off_board_risk(my_coord, categories['my_stack'], categories['enemy_stack'], board)
        score += score_eat(my_coord, categories['enemy_stack'])
        score += score_friendly_merge(my_coord, categories['my_stack'])

    for enemy_coord in categories['enemy_stack']:
        # distance = manhanttan_distance(enemy_coord, coord_centre)
        # score -= (10 - distance)
        
        score -= distance_heatmap[enemy_coord.r][enemy_coord.c]
        score += score_push_off_board_risk(enemy_coord, categories['enemy_stack'], categories['my_stack'], board)
        score -= score_eat(enemy_coord, categories['my_stack'])
        score -= score_friendly_merge(enemy_coord, categories['enemy_stack'])

    return score

def choose_best_action_during_placement_with_move_order(
    board: Board,
    depth: int,
    agent_colour: PlayerColor,
    empty_cells: list[Coord],
    distance_heatmap: list[list[int]],
    transposition_table: dict
) -> Action:
    """
    main entry point 
    Evaluate each possible action based on the score then return 
    the action with highest score 
    """
    
    best_action = None
    best_score = float("-inf")

    possible_actions = all_legal_actions_during_pacement(board, empty_cells, 1)

    for action in possible_actions:
        board.apply_action(action)
        maximizing = (board.turn_color == agent_colour)
        curr_score = min_max_algo(
            maximizing, 
            board, 
            depth-1, 
            alpha= float("-inf"), 
            beta = float("inf"), 
            my_colour=agent_colour,
            empty_cells=empty_cells,
            distance_heatmap=distance_heatmap,
            transposition_table = transposition_table
        ) 
        board.undo_action()

        if curr_score > best_score:
            best_score = curr_score
            best_action = action
             
    return best_action

def all_legal_actions_during_pacement(
    board: Board,
    empty_cells: list[Coord],
    turn_count: int,
) -> list[Action]:
    """
    Find all possible Placement action that doesn't violate the 
    game rule
    """
    place_actions = {}

    current_colour = board.turn_color

    for coord in empty_cells:
        if not board[coord].is_empty:
            continue

        if turn_count != 0:
            # after first round can't place next to enemy
            if board._is_adjacent_to_opponent(coord):
                continue
            place = PlaceAction(coord)
        else:
            place = PlaceAction(coord)
        # try:
        #     cell = board.apply_action(place)
        # except IllegalActionException:
        #     continue

        # try:
        place_score = score_moving_order(board, coord, current_colour)
        place_actions[place] = place_score
        # finally:
        #     board.undo_action()  

    sorted_placement_score = sorted(place_actions.items(),key = lambda x : x[1], reverse = True)
    return [action for action, _ in sorted_placement_score]

def min_max_algo(
    maximizing: bool, 
    board: Board, 
    depth: int, 
    alpha: float, 
    beta: float,
    my_colour: PlayerColor,
    empty_cells: list[Coord],
    distance_heatmap: list[list[int]],
    transposition_table: dict
) -> int: 
    """
    Determine the next action using min_max algo
    """
    # Create hash
    hash_key = compute_hash(board)
    tt_move = None

    # check whether already visit this board state before 
    if hash_key in transposition_table:
        stored_depth, stored_value, score_flag, stored_best_move = transposition_table[hash_key]
        if stored_depth >= depth:
            if score_flag == ScoreFlag.EXACT:
                return stored_value
            if score_flag == ScoreFlag.LOWER_BOUND:
                alpha = max(alpha, stored_value)
            if score_flag == ScoreFlag.UPPER_BOUND: 
                beta = min(beta, stored_value)
            if alpha >= beta:
                return stored_value
        tt_move = stored_best_move

    # leaf node / terminal node 
    if board.turn_count == constants.PLACEMENT_TURNS or not board._has_legal_actions() or depth == 0:
        value = evaluate_board(board,my_colour, distance_heatmap)
        transposition_table[hash_key] = (depth, value, ScoreFlag.EXACT, None)
        return value
    
    # generate move 
    possible_actions = all_legal_actions_during_pacement(board, empty_cells)

    # let tt be the first one, as it is prove better than heuristic guess
    if tt_move is not None and tt_move in possible_actions:
        possible_actions.remove(tt_move)
        possible_actions.insert(0, tt_move)

    alpha_original = alpha
    beta_original = beta
    best_move = None

    if maximizing:
        best_score = float('-inf')
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(False, board, depth - 1,alpha,beta, my_colour, empty_cells, distance_heatmap, transposition_table)
            board.undo_action()
            if new_score > best_score:
                best_score = new_score
                best_move = each_action
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    
    else:
        best_score = float('inf')
    
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(True, board, depth - 1,alpha,beta, my_colour, empty_cells, distance_heatmap, transposition_table)
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

    transposition_table[hash_key] = (depth, best_score, score_flag, best_move)
    return best_score

def score_moving_order(
    board: Board,
    curr_coord: Coord, 
    my_colour: PlayerColor
) -> int:
    """
    Consider the locality of the tokens to decide the order of movement
    """
    score = 0

    for i in range (1,4):
        for direction in CARDINAL_DIRECTIONS:
            coord_r = curr_coord.r + (i * direction.r)
            coord_c = curr_coord.c + (i * direction.c)

            # penalise if higher potential to fall
            if not board._is_within_bounds(coord_r, coord_c):
                score -= 8 // i
                continue

            coord = Coord(coord_r, coord_c)

            cell_state = board.__getitem__(coord)

            # degree of movement 
            if cell_state.is_empty:
                score += 2 // i

            # can eat and weight it by distance
            elif board[coord].color != my_colour :
                score += 10 // i

                # can cascade to push the enemy off the board 
                if not board._is_within_bounds(coord_r + 3 * direction.r, coord_c + 3 * direction.c):
                    score += 8 //i

            # can merge with friendly stack   
            elif board[coord].color == my_colour:
                score += 4 // i

    return score
            
def iterative_deepening_place(
    board: Board,
    agent_colour: PlayerColor,
    empty_cells: list[Coord],
    distance_heatmap: list[list[int]],
    transposition_table: dict,
    turn_count: int,
    max_depth: int = 8,
    time_limit: float = 2.5
) -> Action:
    best_action = None
    start = time.time()

    for depth in range(1, max_depth + 1):
        score, action = minimax_root(
            board, depth, agent_colour, empty_cells,
            distance_heatmap, transposition_table, turn_count, start_time=start, 
            time_limit=time_limit
        )
        
        if action is None or time.time() - start > time_limit:
            print(f"Timed out at depth {depth}, using depth {depth-1} result")
            break
        best_action = action

    return best_action

def minimax_root(
    board: Board,
    depth: int,
    agent_colour: PlayerColor,
    empty_cells: list[Coord],
    distance_heatmap: list[list[int]],
    transposition_table: dict,
    turn_count: int, 
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

    possible_actions = all_legal_actions_during_pacement(board, empty_cells, turn_count)

    hash_key = compute_hash(board)

    tt_move = None
    if hash_key in transposition_table:
        _, _, _, stored_best_move = transposition_table[hash_key]
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
                    maximizing, 
                    board, 
                    depth-1, 
                    alpha, 
                    beta, 
                    my_colour=agent_colour,
                    empty_cells=empty_cells,
                    distance_heatmap=distance_heatmap,
                    transposition_table = transposition_table,
                    turn_count = turn_count + 1,
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

    # Timeout before searching the whole level 
    except TimeoutError:
        return None, None 
             
    return best_score, best_action

def min_max_algo_with_time(
    maximizing: bool, 
    board: Board, 
    depth: int, 
    alpha: float, 
    beta: float,
    my_colour: PlayerColor,
    empty_cells: list[Coord],
    distance_heatmap: list[list[int]],
    transposition_table: dict,
    turn_count: int, 
    start_time,
    time_limit: float,
) -> int: 
    """
    Determine the next action using min_max algo
    """

    if (time.time() - start_time) > time_limit:
        raise TimeoutError()
    
    # Create hash
    hash_key = compute_hash(board)
    tt_move = None

    # check whether already visit this board state before 
    if hash_key in transposition_table:
        stored_depth, stored_value, score_flag, stored_best_move = transposition_table[hash_key]
        if stored_depth >= depth:
            if score_flag == ScoreFlag.EXACT:
                return stored_value
            if score_flag == ScoreFlag.LOWER_BOUND:
                alpha = max(alpha, stored_value)
            if score_flag == ScoreFlag.UPPER_BOUND: 
                beta = min(beta, stored_value)
            if alpha >= beta:
                return stored_value
        tt_move = stored_best_move

    # leaf node / terminal node 
    if board.turn_count == constants.PLACEMENT_TURNS or not board._has_legal_actions() or depth == 0:
        value = evaluate_board(board,my_colour, distance_heatmap)
        transposition_table[hash_key] = (depth, value, ScoreFlag.EXACT, None)
        return value
    
    # generate move 
    possible_actions = all_legal_actions_during_pacement(board,empty_cells, turn_count=turn_count)

    # let tt be the first one, as it is prove better than heuristic guess
    if tt_move is not None and tt_move in possible_actions:
        possible_actions.remove(tt_move)
        possible_actions.insert(0, tt_move)

    alpha_original = alpha
    beta_original = beta
    best_move = None

    if maximizing:
        best_score = float('-inf')
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            maximizing_next = (board.turn_color == my_colour)
            try:
                new_score = min_max_algo_with_time(
                    maximizing_next, 
                    board, 
                    depth - 1,
                    alpha,
                    beta, 
                    my_colour, 
                    empty_cells, 
                    distance_heatmap, 
                    transposition_table, 
                    turn_count + 1, 
                    start_time, 
                    time_limit)
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
        best_score = float('inf')
    
        for each_action in possible_actions:
            board.apply_action(each_action)
            maximizing_next = (board.turn_color == my_colour)
            try:
                new_score = min_max_algo_with_time(
                    maximizing_next, 
                    board, 
                    depth - 1,
                    alpha,
                    beta, 
                    my_colour, 
                    empty_cells, 
                    distance_heatmap, 
                    transposition_table, 
                    turn_count + 1,
                    start_time, 
                    time_limit)
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

    transposition_table[hash_key] = (depth, best_score, score_flag, best_move)
    return best_score           
            