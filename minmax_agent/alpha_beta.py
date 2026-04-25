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
             
    return best_action

def min_max_algo(self, maximizing, board, depth, alpha, beta) -> int: #Each depth of min max
    """
    Determine the next action using min_max algo
    """
    #Move, eat and cascade
    #Red always goes first -> Max
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

def heuristic_func(self,board,agent_color) -> int:
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED
    
    # 7 factors: 1. Our total stack height 2. Potential to be eaten 3. Potential for center control
    # 4. Being in the edge  
    # priority: 1. Will see if we can eat our adjacent stacj 2. cascade and ppush it away 3. continue with score func 
    
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED

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

    #Flags for priority
    eat_immidiately = False
    cascade_immidiately = False

    agent_positions = {} 
    opp_positions = {}    

    for coord, cell in board._state.items():
        if cell.is_empty:
            continue
        if cell.color == opp_color:
            opp_positions[(coord.r, coord.c)] = cell.height
        elif cell.color == agent_color:
            agent_positions[(coord.r, coord.c)] = cell.height

    agent_stack_count = len(agent_positions)
    opp_stack_count = len(opp_positions)

    # ── ENDGAME MODE ──────────────────────────────────────
    if opp_stack_count == 1:
        opp_r, opp_c = next(iter(opp_positions))
        opp_h = opp_positions[(opp_r, opp_c)]

        total_dist = 0
        min_dist = math.inf
        closest_h = 0
        sides_covered = set()

        for (r, c), h in agent_positions.items():
            dist = abs(r - opp_r) + abs(c - opp_c)
            total_dist += dist

            if dist < min_dist:
                min_dist = dist
                closest_h = h

            if dist == 1:
                if r < opp_r: sides_covered.add('up')
                if r > opp_r: sides_covered.add('down')
                if c < opp_c: sides_covered.add('left')
                if c > opp_c: sides_covered.add('right')

        sides_blocked = len(sides_covered)

        # Adjacent and tall enough can eat immediately
        if min_dist == 1 and closest_h >= opp_h:
            return 99000

        return (
            50000
            - total_dist * 500
            - min_dist * 1000
            + sides_blocked * 3000
        )


    for coord, cell in board._state.items():
        if cell.is_empty:
            continue

        is_agent = (cell.color == agent_color)
        
        if is_agent:
            agent_total += cell.height
        else:
            opp_total += cell.height 

        if 3 <= coord.r <= 5 and 3 <= coord.c <= 5:
            if is_agent:
                agent_center += 1
            else:
                opp_center += 1

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
            if neighbor in board._state:
                neighbor_cell = board._state[neighbor]
            if neighbor_cell.is_empty:
                continue

            if is_agent and neighbor_cell.color == opp_color:
                agent_eat_threats += cell.height
                if cell.height >= neighbor_cell.height:
                    eat_immidiately = True
                elif not is_agent and neighbor_cell.color == agent_color:
                 opp_eat_threats += cell.height

                #Priority 2

                if is_agent and cell.height >= 2:
                    reach = cell.height

                    for cas_dir in CARDINAL_DIRECTIONS:
                        new_row = coord.r + cas_dir.r * reach
                        new_col = coord.c + cas_dir.c * reach

                        is_safe = 0 <= new_row <= 7 and 0 <= new_col <= 7
                        if not is_safe:
                            continue

                        opp_in_path = None
                        for step in range(1, reach + 1):
                            check_r = coord.r + direction.r * step
                            check_c = coord.c + direction.c * step
                            if (check_r, check_c) in opp_positions:
                                opp_in_path = step
                                break

                        if opp_in_path is None:
                            continue

                        enemy_r = coord.r + cas_dir.r * opp_in_path
                        enemy_c = coord.c + cas_dir.c * opp_in_path
                        push_steps = reach - opp_in_path
                        push_r = enemy_r + cas_dir.r * push_steps
                        push_c = enemy_c + cas_dir.c * push_steps

                        kicked_off = not (0 <= push_r <= 7 and 0 <= push_c <= 7)

                        if kicked_off:
                            agent_cascade_push += cell.height * 10
                            cascade_immidiately  = True
                        elif new_row in (0, 7) or new_col in (0, 7):
                            agent_cascade_push += cell.height * 2
                            cascade_immidiately  = False
                        else:
                            agent_cascade_push += cell.height
                            cascade_immidiately  = False


    if eat_immidiately:
        return 90000

    if cascade_immidiately  == True:
        return 80000 * cascade_immidiately 

    # Normal score
    return (
        10 * (agent_total - opp_total)
        + 4  * (agent_eat_threats - opp_eat_threats)
        + 6  * agent_cascade_push
        + 2  * (agent_center - opp_center)
        - 1  * (agent_edge - opp_edge)
    )



    """

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
