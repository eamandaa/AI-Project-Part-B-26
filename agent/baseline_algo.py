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
        #print("coord:", coord, "cell:", cell)

    return 0

def heuristic_func(self,board,agent_color) -> int:
    """
    7 factors: 1. Our total stack height 2. Movement advantage 3. How likely opp eat ours
    4. Opportunities to eat opponent 5. Potential for cascade 6. Potential for center control
    7. Being in the edge  
    """
    
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED
    #1. height
    agent_total = 0
    opp_total = 0
    # 6. Center Control
    agent_center = 0
    opp_center = 0
    # 7. being in edge
    agent_edge = 0
    opp_edge = 0

    agent_eat_threats = 0
    opp_eat_threats= 0

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
                
        for direction in CARDINAL_DIRECTIONS:
            try:
                neighbor = coord + direction
            except ValueError:
                continue
            if neighbor in board._state:
                neighbor_cell = board._state[neighbor]
                if not neighbor_cell.is_empty:
                    if is_agent and neighbor_cell.color == opp_color:
                        # potential eat
                        agent_eat_threats += cell.height
                    elif not is_agent and neighbor_cell.color == agent_color:
                        opp_eat_threats += cell.height
    
    eat_threat_score = agent_eat_threats - opp_eat_threats
    height_score = agent_total - opp_total
    center_score = agent_center - opp_center
    edge_score = agent_edge - opp_edge

    """
    # 2. Movement advantage
    original_turn = board._turn_color

    board._turn_color = agent_color
    agent_actions = all_legal_actions(self, board)

    board._turn_color = opp_color
    opp_actions = all_legal_actions(self, board)

    board._turn_color = original_turn

    movement_advantage = len(agent_actions) - len(opp_actions)

    #3. & 4. Eating opp
    agent_eats = sum(1 for action in agent_actions if isinstance(action, EatAction))
    opp_eats = sum(1 for action in opp_actions if isinstance(action, EatAction))
    capture_threat_advantage = agent_eats - opp_eats

    #5. Cascade
    agent_cascades = sum(1 for action in agent_actions if isinstance(action, CascadeAction))
    opp_cascades = sum(1 for action in opp_actions if isinstance(action, CascadeAction))
    cascade_potential_advantage = agent_cascades - opp_cascades


    vulnerable_stack_penalty = opp_eats
    """
    
    

    score = (
        10 * height_score
        #+ 4 * movement_advantage
        #+ 8 * capture_threat_advantage
        #- 7 * vulnerable_stack_penalty
        #+ 6 * cascade_potential_advantage
        + 4 * eat_threat_score
        + 2 * center_score
        - 1 * edge_score
    )

    return score



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
