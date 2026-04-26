from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase   

from referee.game import Board
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
        curr_score = min_max_algo(self, False, board, depth, alpha= -math.inf, beta = math.inf) 
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

        #print(f"DEBUG: depth {depth}, best score={best_score}")
        return best_score

    return 0

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

    agent_block = 0 #not in use
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

            if neighbor not in board._state:
                continue
            neighbor_cell = board._state[neighbor]

            if is_agent and neighbor_cell.color == opp_color:
                if cell.height >= neighbor_cell.height:
                    agent_capture_bonus += neighbor_cell.height * 50 
                    eat_immediately = True

            if not neighbor_cell.is_empty and neighbor_cell.color == agent_color:
                agent_block += 2

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
                        break
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


    if eat_immediately:
        return 90000

    # Normal score
    return (
        10 * (agent_total - opp_total)
        #+ 8  * (agent_eat_threats - opp_eat_threats)
        + 1  * (agent_cascade_push - opp_cascade_push)
        + 2  * (agent_center - opp_center)
        - 1  * (agent_edge - opp_edge)
        #+ 5 * agent_block
        + 500 * agent_capture_bonus
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
