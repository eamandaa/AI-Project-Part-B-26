from referee.game import BOARD_N, Board
from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase, CellState

def minimax_evluation_function(
    board: Board,
    agent_colour: PlayerColor
):
    if agent_colour == PlayerColor.RED:
        opp_colour = PlayerColor.BLUE
    else:
        opp_colour = PlayerColor.RED

    my_positions = {} 
    opp_positions = {}

    # consider material balance (total height)
    my_total_height = 0
    opp_total_height = 0

    for coord, cell in board._state.items():
        if cell.is_empty:
            continue
        if cell.color == opp_colour:
            opp_positions[(coord.r, coord.c)] = cell.height
            opp_total_height += cell.height
        elif cell.color == agent_colour:
            my_positions[(coord.r, coord.c)] = cell.height
            my_total_height += cell.height
    
    my_score = 0
    opponent_score = 0

    for my_coord, my_height in my_positions.items():
        my_score += evaluate_eat(opp_positions, my_coord, my_height)
        my_score += evaluate_cascade_board(opp_positions, my_positions, my_coord, my_height, board)
    
    my_score += 3 * my_total_height

    for enemy_coord, enemy_height in opp_positions.items():
        opponent_score += evaluate_eat(my_positions, enemy_coord, enemy_height)
        opponent_score += evaluate_cascade_board(my_positions, opp_positions, enemy_coord, enemy_height, board)
    
    opponent_score += 3 * opp_total_height

    return my_score - opponent_score

def manhanttan_distance(
    coord_one: Coord,
    coord_two: Coord
) -> int:
    """Calculate the distance of the coordinates using Manhattan distance"""
    return abs(coord_one.r - coord_two.r) + abs(coord_one.c - coord_two.c)

def evaluate_eat(
    opponents_stacks:dict[tuple[int, int], int],
    curr_coord: tuple[int, int],
    curr_cell_height: int,
) -> float:
    """
    Evaluate how likely the agent could eat the opponents with distance consideration
    """

    eat_score = 0

    for (opponent_r, opponent_c), opponent_height in opponents_stacks.items():
        distance = manhanttan_distance(Coord(curr_coord), Coord(opponent_r, opponent_c))

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

        # # more important 
        # if distance <= 2:
        #     weight = 2
        # # could be a potential eat
        # elif distance <= 4:
        #     weight = 1

        eat_score += current_eat_score * (1 / distance)

    return eat_score

def evaluate_cascade_board(
    opponents_stacks:dict[tuple[int, int], int],
    my_stacks:dict[tuple[int, int], int],
    curr_coord: tuple[int, int],
    curr_cell_height: int,
    board: Board
)-> float:
    """
    On the given position, how likely you are being pushed off the board
    and how likely you can push the enemy off the board
    after cascade, we evaluate how likely we can eat or cascade again
    """
    best_score = float("-inf")

    # can't perform any cascade due to rules (cascade needs to be at least height 2)
    if curr_cell_height < 2:
        return 0
    
    curr_coord_r, curr_coord_c = curr_coord
    
    for direction in CARDINAL_DIRECTIONS:
        enemy_total_lost = 0
        my_total_lost = 0
        curr_score = 0

        updated_opponents = dict(opponents_stacks)
        updated_my = dict(my_stacks)

        for i in range(1, curr_cell_height + 1):
            coord_r = curr_coord_r + direction.r * i
            coord_c = curr_coord_c + direction.c * i

            certainty = 1 / i
            # out of bound
            # we lost tokens if we cascade at this direction
            if not board._is_within_bounds(coord_r, coord_c):
                curr_score -= (curr_cell_height - i + 1) * certainty
                break

            if (coord_r, coord_c) in updated_opponents or (coord_r, coord_c) in updated_my:
                push_lost = simulate_cascade_push_tokens(
                    coord_r, coord_c, direction, board, updated_opponents, updated_my
                    )
                enemy_total_lost += push_lost['enemy_lost'] * certainty
                my_total_lost += push_lost['my_lost'] * certainty
            
        curr_score += (enemy_total_lost - my_total_lost)

        for (my_r, my_c), my_height in updated_my.items():
            # check the affected coordinates only 
            if (my_r, my_c) not in my_stacks or my_stacks[(my_r, my_c)] != my_height:
                for adj_dir in CARDINAL_DIRECTIONS:
                    adj_r = my_r + adj_dir.r
                    adj_c = my_c + adj_dir.c 

                    if not board._is_within_bounds(adj_r, adj_c):
                        continue
                    
                    # my stack after cascade is pushed to enemy that it can potential eat / being eaten by enemy 
                    if (adj_r, adj_c) in updated_opponents:
                        enemy_height = updated_opponents[(adj_r, adj_c)]

                        height_diff = abs(enemy_height - my_height)
                        if my_height >= enemy_height:
                            curr_score += (1 + height_diff)
                        else:
                            curr_score -= (1 + height_diff) 

                # is my stack is closer to perform cascade on an enemy?
                if my_height >= 2:
                    for cascade_direction in CARDINAL_DIRECTIONS:
                        for j in range(1, my_height + 1):
                            target_r = my_r + cascade_direction.r * j
                            target_c = my_c + cascade_direction.c * j

                            if not board._is_within_bounds(target_r, target_c):
                                break

                            if (target_r, target_c) in updated_opponents:
                                next_r = target_r + cascade_direction.r
                                next_c = target_c + cascade_direction.c

                                # has successfully push enemy off the board
                                if not board._is_within_bounds(next_r, next_c):
                                    curr_score += updated_opponents[(target_r, target_c)] * (1/ j)
                                    break

                                break
        if curr_score > best_score:
            best_score = curr_score
    
    return best_score

def simulate_cascade_push_tokens(
    coord_r: int, 
    coord_c: int, 
    direction: Direction,
    board: Board,
    updated_opponents: dict[tuple[int, int], int],
    updated_my: dict[tuple[int, int], int]
) -> dict[str, int]:
    
    """
    Simulate a stack at the coord being pushed one step in direction.
    Update the opponents and my stacks, tell us how much tokens have lost on both side 
    """
    dest_r = coord_r + direction.r
    dest_c = coord_c + direction.c

    lost = {
        "enemy_lost" : 0,
        "my_lost" : 0
    }

    if not board._is_within_bounds(dest_r, dest_c):
        # Pushed off board - eliminated
        if (coord_r, coord_c) in updated_opponents:
            lost["enemy_lost"] = updated_opponents.get((coord_r, coord_c))
            del updated_opponents[(coord_r, coord_c)]

        if (coord_r, coord_c) in updated_my:
            lost["my_lost"] = updated_my.get((coord_r, coord_c))
            del updated_my[(coord_r, coord_c)]

        return lost
    
    # Recursively push the stack at destination if there is something there
    if (dest_r, dest_c) in updated_opponents or (dest_r, dest_c) in updated_my:
        push_lost = simulate_cascade_push_tokens(
            dest_r, dest_c, direction, board, updated_opponents, updated_my
        )

        lost["enemy_lost"] += push_lost["enemy_lost"]
        lost['my_lost'] += push_lost['my_lost']

    # update the pushed location with the height of the original stack 
    if (coord_r, coord_c) in updated_opponents:
        updated_opponents[(dest_r, dest_c)] = updated_opponents[(coord_r, coord_c)]
        del updated_opponents[(coord_r, coord_c)]
    if (coord_r, coord_c) in updated_my:
        updated_my[(dest_r, dest_c)] = updated_my[(coord_r, coord_c)]
        del updated_my[(coord_r, coord_c)]

    return lost

