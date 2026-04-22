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

from referee.game import Board, Coord, constants, PlayerColor, CARDINAL_DIRECTIONS

def manhanttan_distance(
    coord_one: Coord,
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)

def find_empty_centre_of_board(
    empty_coord: list[Coord],
    enemy_coord: list[Coord],
    board: Board, 
) -> dict[Coord, int]:
    """
    Find the closest coordinates that is close to centre of the board
    """

    centre = constants.BOARD_N // 2
    coord_centre = Coord(centre, centre)

    empty_cell_dist = {}
    for curr_coord in empty_coord:
        skip = False

        for direction in CARDINAL_DIRECTIONS:

            # check adjacent to enemy (game rule in placement)
            adjacent_coord = Coord(curr_coord.r + direction.r, curr_coord.c + direction.c)
            if adjacent_coord in enemy_coord:
                skip = True
                break

            #
            behind = Coord(curr_coord.r - direction.r, curr_coord.c - direction.c)
            if behind in enemy_coord:
                check = curr_coord
                for _ in range(3):
                    check = Coord(check.r + direction.r, check.c + direction.c)

                    if not board._within_bounds(check):
                        skip = True
                        break
            
            if skip:
                break

        if skip:
            continue

        curr_dist = manhanttan_distance(curr_coord, coord_centre)
        # the further the distance, the more likely we don't want 
        empty_cell_dist[curr_coord] = curr_dist 

    # sort the dictonary based on distance 
    sorted_empty_cell_dist = dict(sorted(empty_cell_dist.items(), key = lambda item: item[1]))
            
    return sorted_empty_cell_dist

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
        if min_dist == 1:
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
    elif min_dist == 4:
        return 1
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

    for coord in friend_coords:
        if coord == curr_coord:
            continue

        dist = manhanttan_distance(coord, curr_coord)

        if dist == 1:
            score += 3
        elif dist == 2:
            score += 1
        
    return score

def evaluate_board(
    board:Board,
    my_colour: PlayerColor
) -> int:
    """
    Main entry point for getting score for minimax approach
    Considering
    - turn order 
    - distance of empty coords with center 
    """

    categories = {
        "my_stack" : [],
        "enemy_stack" : [],
        "empty" : []
    }

    # enemy_colour = PlayerColor.BLUE
    # if my_colour == PlayerColor.BLUE:
    #     enemey_colour = PlayerColor.RED

    for curr_coord, curr_cell_state in board._state.items():
        if curr_cell_state.is_empty():
            categories["empty"].append(curr_coord)
        else:
            if curr_cell_state.color == my_colour:
                categories["my_stack"].append(curr_coord)
            else:
                categories['enemy_stack'].append(curr_coord)

    # sort the empty coordinate based on the distance from centre
    empty_cell_with_distance = find_empty_centre_of_board(
        board, 
        categories['empty'], 
        categories['enemy_stack'])
    
    high_potential_coord = list(empty_cell_with_distance.keys())[:20]

    # we want it to be in range 0 to 10 unless it is hard penalty
    best_score = float('-inf')
    best_coord = None

    for coord in high_potential_coord:
        score = (
            score_eat(coord,categories['enemy_stack'])
            + score_friendly_merge(coord, categories['my_stack'])
        )

        if score > best_score:
            best_score = score
            best_coord = coord
    
    return best_coord, best_score



    


    

    

    



