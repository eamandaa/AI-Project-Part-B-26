from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase   

from referee.game import Board
import math


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

    return actions

def heuristic_func(board,agent_color) -> int:
    """
    7 factors: 1. Our total stack height 2. Potential to be eaten 3. Potential for center control
    4. Being in the edge  
    """
    
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED

    #In case of game over
    if board.game_over:
        winner = board.winner_color
        if winner == agent_color:
            return 100000
        elif winner == opp_color:
            return -100000
        else:
            return -5000
        
    agent_positions = {}
    enemy_positions = {}

    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        h = cell.height
        is_agent = (cell.color == agent_color)
        #track total height, number of tokens, and largest token height i have and the opponent
        if is_agent:
            agent_positions[coord] = h
        else:
            enemy_positions[coord] = h
           

        
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

    agent_cascade_kill = 0
    opp_cascade_kill = 0

    agent_cascade_self_loss = 0
    opp_cascade_self_loss = 0

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
            if neighbor in board._state:
                neighbor_cell = board._state[neighbor]
                if not neighbor_cell.is_empty:
                    # considering height
                    # if it is higher than we reward it to get closer, else we run away
                    if is_agent and neighbor_cell.color == opp_color:
                        if neighbor_cell.height < cell.height:
                            agent_eat_threats += cell.height
                        else:
                            agent_eat_threats -= cell.height
                    # for enemy to eat 
                    elif not is_agent and neighbor_cell.color == agent_color:
                        if cell.height < neighbor_cell.height:
                            opp_eat_threats += cell.height
                        else:
                            opp_eat_threats -= cell.height

        if cell.height >= 2:
            r, c = coord.r, coord.c

            for dir in CARDINAL_DIRECTIONS:

                for step in range(1, cell.height + 1):
                    new_r = r + dir.r*step
                    new_c = c + dir.c*step

                    # ray left the board — source stack falls off
                    if not (0 <= new_r <= 7 and 0 <= new_c <= 7):
                        lost = cell.height - step + 1
                        if is_agent:
                            agent_cascade_self_loss += lost
                        else:
                            opp_cascade_self_loss += lost
                        break

                    push_steps = cell.height - step + 1
                    final_r = new_r + dir.r * push_steps
                    final_c = new_c + dir.c * push_steps
                    lands_off = not (0 <= final_r <= 7 and 0 <= final_c <= 7)

                    hit_coord = Coord(new_r, new_c)

                    if hit_coord in (enemy_positions if is_agent else agent_positions):
                        # hitting an enemy piece
                        enemy_h = (enemy_positions if is_agent else agent_positions)[hit_coord]
                        if lands_off:
                            if is_agent:
                                agent_cascade_kill += enemy_h
                            else:
                                opp_cascade_kill += enemy_h

                    elif hit_coord in (agent_positions if is_agent else enemy_positions):
                        # hitting our own piece
                        own_h = (agent_positions if is_agent else enemy_positions)[hit_coord]
                        if lands_off:
                            if is_agent:
                                agent_cascade_self_loss += own_h
                            else:
                                opp_cascade_self_loss += own_h

    
    
    height_score = agent_total - opp_total
    center_score = agent_center - opp_center
    edge_score = agent_edge - opp_edge
    eat_threat_score = agent_eat_threats - opp_eat_threats
    cascade_kill = agent_cascade_kill - opp_cascade_kill
    cascade_self_loss = agent_cascade_self_loss - opp_cascade_self_loss
    
    score = (
        2 * height_score
        + 5 * eat_threat_score
        + 4 * cascade_kill
        - 2 * cascade_self_loss
        + 1 * center_score
        - 1 * edge_score
    )

    return score

def choose_best_action_during_play(
    board: Board,
) -> Action:
    """
    Evaluate each possible action based on the score then return 
    the action with highest score 
    """
    
    best_action = None
    best_score = float("-inf")

    possible_actions = all_legal_actions_during_play(board)
    agent_colour = board.turn_color

    for action in possible_actions:
        board.apply_action(action)
        curr_score = heuristic_func(board, agent_colour)
        board.undo_action()

        if curr_score > best_score:
            best_score = curr_score
            best_action = action
             
    return best_action