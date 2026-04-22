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


Potential idea to improve
- consider symmetry of the board state
"""


from referee.game import Board, Coord, constants, PlayerColor, CARDINAL_DIRECTIONS, Action, PlaceAction, IllegalActionException

def manhanttan_distance(
    coord_one: Coord,
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)

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
            
            behind = Coord(behind_c, behind_r)
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
    
def score_mobility(
    curr_coord: Coord,
    board: Board,
) -> int:
    """
    Give a score based on empty cell
    Merge already handle seperately
    """
    score = 0

    for direction in CARDINAL_DIRECTIONS:
        coord_r = curr_coord.r + direction.r
        coord_c = curr_coord.c + direction.c

        if not board._is_within_bounds(coord_r, coord_c):
            continue

        coord = Coord(coord_r, coord_c)

        if board[coord].is_empty:
            score += 2
    
    return score

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
    my_colour: PlayerColor
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

    centre = constants.BOARD_N // 2
    coord_centre = Coord(centre, centre)

    for my_coord in categories['my_stack']:
        # distance from centre to current coordinate
        # distance = manhanttan_distance(my_coord, coord_centre)
        # score += (10 - distance)

        score += score_distance_to_centre(my_coord)
        score += score_mobility(my_coord, board)
        score += score_distance_to_edges(my_coord)
        score -= score_push_off_board_risk(my_coord, categories['my_stack'], categories['enemy_stack'], board)
        score += score_eat(my_coord, categories['enemy_stack'])
        score += score_friendly_merge(my_coord, categories['my_stack'])

    for enemy_coord in categories['enemy_stack']:
        # distance = manhanttan_distance(enemy_coord, coord_centre)
        # score -= (10 - distance)

        score -= score_distance_to_centre(enemy_coord)
        score -= score_mobility(enemy_coord, board)
        score -= score_distance_to_edges(enemy_coord)
        score += score_push_off_board_risk(enemy_coord, categories['enemy_stack'], categories['my_stack'], board)
        score -= score_eat(enemy_coord, categories['my_stack'])
        score -= score_friendly_merge(enemy_coord, categories['enemy_stack'])

    return score

def choose_best_action_during_placement(
    board: Board,
    depth: int,
    agent_colour: PlayerColor,
) -> Action:
    """
    Evaluate each possible action based on the score then return 
    the action with highest score 
    """
    
    best_action = None
    best_score = float("-inf")

    possible_actions = all_legal_actions_during_pacement(board)

    for action in possible_actions:
        board.apply_action(action)
        maximizing = (board.turn_color == agent_colour)
        curr_score = min_max_algo(maximizing, board, depth-1, alpha= float("-inf"), beta = float("inf"), my_colour=agent_colour) 
        board.undo_action()

        if curr_score > best_score:
            best_score = curr_score
            best_action = action
             
    return best_action

def all_legal_actions_during_pacement(
    board: Board,
) -> list[Action]:
    """
    Find all possible Placement action that doesn't violate the 
    game rule
    """
    place_actions = []

    for coord, cell in board._state.items():
        if not cell.is_empty:
            continue
        
        try:
            place = PlaceAction(coord)
            board._resolve_place_action(place)
            place_actions.append(place)
        except IllegalActionException:
            pass

    return place_actions

def min_max_algo(
    maximizing: bool, 
    board: Board, 
    depth: int, 
    alpha: float, 
    beta: float,
    my_colour: PlayerColor,
) -> int: 
    """
    Determine the next action using min_max algo
    """
    #Move, eat and cascade
    #Red always goes first -> Max

    if board.turn_count == constants.PLACEMENT_TURNS or not board._has_legal_actions() or depth == 0:
        return evaluate_board(board,my_colour)
    
    possible_actions = all_legal_actions_during_pacement(board)

    if maximizing:
        best_score = float('-inf')
        
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(False, board, depth - 1,alpha,beta, my_colour)
            board.undo_action()
            best_score = max(best_score, new_score)
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_score
    
    elif maximizing == False:
        best_score = float('inf')
    
        for each_action in possible_actions:
            board.apply_action(each_action)
            new_score = min_max_algo(True, board, depth - 1,alpha,beta, my_colour)
            board.undo_action()
            best_score = min(best_score, new_score)
            beta = min(beta, best_score)
            if alpha >= beta:
                break

        return best_score
    return 0
