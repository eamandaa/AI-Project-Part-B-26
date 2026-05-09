from referee.game import PlayerColor, Coord, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, Direction, CARDINAL_DIRECTIONS
from referee.game import Board

import random 
random.seed(10)

def all_legal_actions_during_place(
    board: Board,
    turn_count: int,
) -> Action:
    """
    Find all possible Placement action that doesn't violate the 
    game rule and pick an action by random 
    """
    place_actions = []

    for coord, _ in board._state.items():
        if not board[coord].is_empty:
            continue

        if turn_count != 0:
            # after first round can't place next to enemy
            if board._is_adjacent_to_opponent(coord):
                continue
            place = PlaceAction(coord)
        else:
            place = PlaceAction(coord)
    
        place_actions.append(place)

    chosen_place = random.choice(place_actions)
    return chosen_place

def all_legal_actions_during_play(
    board: Board
) -> Action:
    """
    Generate all possible actions during Play phase that doesn't
    violate the rules and pick an action by random 
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
    chosen_action = random.choice(actions)
    return chosen_action