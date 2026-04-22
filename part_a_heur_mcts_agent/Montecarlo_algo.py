from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase   

from referee.game import Board

import math
import time

class MCTS_node:
    def __init__(self, parent=None, action=None):
        self.parent = parent #Parent node
        self.action = action #previous actions
        self.children = [] #children node
        self.wins = 0 #Backpropagation score
        self.visits = 0 #how many times has this node been visited
        self.untried_actions = None #populated on first expansion

    def fully_expanded(self):
        flag_var = self.untried_actions is not None and len(self.untried_actions) == 0
        return flag_var
    
    def is_ended(self,board):
        return board.game_over or not board._has_legal_actions()

    def UCB1(self,exploration = 1.41): 
        if self.visits == 0:
            return math.inf #always do the unvisited one first
        return (self.wins / self.visits) + exploration * math.sqrt(math.log(self.parent.visits) / self.visits)


def mcts(agent,board) -> Action :
    root = MCTS_node()
    start = time.time()
    time_limit = 3

    while time.time() - start < time_limit:
        # 1. Do selection
        node, path = select(root,board)

        #2. Expand
        if node.is_ended(board) == False:
            node = expand(node,agent,board,path)
        
        # 3. Simulate
        score = simulate(agent,board)

        #4. backpropagation
        backpropogation(node,score,board,path)

    actions = all_legal_actions(agent, board)
    
    # Fallback if root never expanded
    if not root.children:
        actions = all_legal_actions(board._turn_color, board)
        return actions[0] if actions else None
    
    best = None
    best_visits = -math.inf

    for child in root.children:
        if child.visits > best_visits:
            best_visits = child.visits
            best = child

    return best.action

def select(node,board):
    path = []
    while node.is_ended(board) == False and node.fully_expanded():
        best_child = None
        best_score = -math.inf

        for child in node.children:
            score = child.UCB1()
            if score > best_score:
                best_score = score
                best_child = child

        node = best_child
        board.apply_action(node.action)
        path.append(node)

    return node, path

def expand(node,agent,board,path):
    if node.untried_actions == None:
        node.untried_actions = all_legal_actions(board._turn_color,board)

    if node.untried_actions:
        each_action = node.untried_actions.pop()
        board.apply_action(each_action)
        child = MCTS_node(parent=node, action=each_action)
        node.children.append(child)
        path.append(child)
        return child
    return node  

def simulate(agent,board):
    return heuristic_func(board, agent._color)

def backpropogation(node,score,board,path):
    for _ in range(len(path)):
        board.undo_action()
    while node is not None:
        node.wins += score
        node.visits += 1
        node = node.parent

    return 0


def heuristic_func(board, agent_color) -> float:
    if agent_color == PlayerColor.RED:
        opp_color = PlayerColor.BLUE
    else:
        opp_color = PlayerColor.RED

    # Terminal check first
    if board.game_over:
        winner = board.winner_color
        if winner == agent_color:
            return 100000
        elif winner == opp_color:
            return -100000
        else:
            return -5000

    # Cost for agent to eat opponent
    agent_cost = heuristic(board._state)  # previous heuristic
    
    # Cost for opponent to eat agent 
    flipped = {}
    for coord, cell in board._state.items():
        if not cell.is_empty:
            # swap colors 
            flipped[coord] = cell

    opp_cost = heuristic(flipped)

    if agent_cost == math.inf:
        agent_score = -50000   # we can never eat them = very bad
    else:
        agent_score = -agent_cost * 100  # lower cost = better for us

    if opp_cost == math.inf:
        opp_score = 50000      # they can never eat us = very good
    else:
        opp_score = opp_cost * 100  # higher opp cost = better for us

    return agent_score + opp_score

def heuristic(
    board
) -> float: 
    """
    Heuristic function for the A* algorithm with consideration of 
    merging two red tokens  in same row/column
    """

    RED = PlayerColor.RED
    BLUE = PlayerColor.BLUE
    inf = math.inf

    # list and dictionary of what we need 
    red_rs = []
    red_cs = []
    red_hs= []

    blue_rs = []
    blue_cs = []
    blue_hs = []

    row_top = {}
    col_top = {}
    total_red_height = 0

    #Filling in the dict and array
    for coord, cell in board.items():
        color = cell.color
        h = cell.height

        if color == RED:
            red_rs.append(coord.r)
            red_cs.append(coord.c)
            red_hs.append(h)
            total_red_height += h
        elif color == BLUE:
            blue_rs.append(coord.r)
            blue_cs.append(coord.c)
            blue_hs.append(h)

    if not blue_hs:
        return 0
    if not red_hs:
        return inf
    
    for i in range(len(red_rs)):
        sort_height_row_column(row_top, red_rs[i], red_hs[i])
        sort_height_row_column(col_top, red_cs[i], red_hs[i])

    #Finding the perfect pairs. Will try to find in the same row or col, whichever gives the biggest height
    partner = compute_rowcol_partners(red_rs, red_cs, red_hs, row_top, col_top)

    #Compute best merge pairs heights without sorting
    n_red = len(red_hs)
    worst = 0

    for bi in range(len(blue_hs)):
        blue_row, blue_col, blue_height = blue_rs[bi], blue_cs[bi], blue_hs[bi]
        best_for_blue = inf

        for i in range(n_red):
            dr = abs(blue_row - red_rs[i])
            dc = abs(blue_col - red_cs[i])
            d = dr + dc

            h0 = red_hs[i]
            p = partner[i]  # use row/col partner

            #Calculating the cost for direct movement
            best_for_blue , stop_heu = direct_action_cost(d,blue_height,dr,dc,h0,best_for_blue)
            if stop_heu:
                break

            # Calculating cost for eat & cascade after merging
            if p > 0:
                h1 = h0 + p
                if d >= 1 and h1 >= blue_height:
                    eat1 = d + 1
                    if eat1 < best_for_blue: #eat
                        best_for_blue = eat1

                reach = h1 if h1 >= 2 else 2
                cost_row = dr + (dc - reach if dc > reach else 0) + 1
                cost_col = dc + (dr - reach if dr > reach else 0) + 1
                cas1 = 1 + (cost_row if cost_row < cost_col else cost_col) #cascade
                if cas1 < best_for_blue:
                    best_for_blue = cas1

        #If we cant find red to eat (red h=1, only 1 red), assign blue to inf
        if best_for_blue == inf:
            if total_red_height >= 2:
                best_for_blue = 1
            else:
                return inf

        if best_for_blue > worst:
            worst = best_for_blue

    return worst

def sort_height_row_column(
    dict, 
    key, 
    height
): 
    """
    Find each token to pair with tallest height if there isn't 
    another red tokens in the same row or column
    """
    
    first_pair, sec_pair = dict.get(key, (-1, -1))
    if height >= first_pair:
        dict[key] = (height, first_pair)
    elif height > sec_pair:
        dict[key] = (first_pair, height)

def direct_action_cost( 
    man_dist: int,
    blue_height: int,
    row_dist: int,
    col_dist: int,
    red_height: int,
    best_for_blue : int,
) -> tuple[int, bool]:
    """
    Calculate the cost of a red token performing eat and cascade directly
    """

    # Direct EAT 
    if man_dist >= 1 and red_height >= blue_height and man_dist < best_for_blue:
        best_for_blue = man_dist
        if best_for_blue == 1:
            return best_for_blue, True

    # Direct CASCADE 
    if red_height >= 2: 
        reach = red_height
        cost_row = row_dist + (col_dist - reach if col_dist > reach else 0) + 1
        cost_col = col_dist + (row_dist - reach if row_dist > reach else 0) + 1
        if cost_row < cost_col: 
            cascade_cost = cost_row 
        else:
            cascade_cost = cost_col

        if cascade_cost < best_for_blue:
            best_for_blue = cascade_cost
            if best_for_blue == 1:
                return best_for_blue, True
            
    return best_for_blue, False

def compute_rowcol_partners( 
    red_rs: list[int],
    red_cs: list[int],
    red_hs: list[int],
    row_top: dict[int, tuple[int, int]],
    col_top: dict[int, tuple[int, int]],
) -> list[int]:
    """
    For each red i returns the best partner height from same row or same col.
    """
    
    n = len(red_hs)
    partner = [0] * n
    for i in range(n):
        r = red_rs[i]
        c = red_cs[i]
        h = red_hs[i]

        #Putting the reds in the row and column dictionary
        row_pair1, row_pair2 = row_top.get(r, (-1, -1))
        col_pair1, col_pair2 = col_top.get(c, (-1, -1))

        row_partner = row_pair2 if h == row_pair1 else row_pair1
        col_partner = col_pair2 if h == col_pair1 else col_pair1

        p = row_partner if row_partner > col_partner else col_partner
        partner[i] = p if p > 0 else 0

    return partner

"""
def heuristic_func(board,agent_color) -> int:
    
    7 factors: 1. Our total stack height 2. Potential to be eaten 3. Potential for center control
    4. Being in the edge  
    
    
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
                    if is_agent and neighbor_cell.color == opp_color:
                        agent_eat_threats += cell.height
                    elif not is_agent and neighbor_cell.color == agent_color:
                        opp_eat_threats += cell.height
    
    
    height_score = agent_total - opp_total
    center_score = agent_center - opp_center
    edge_score = agent_edge - opp_edge
    eat_threat_score = agent_eat_threats - opp_eat_threats
    
    score = (
        10 * height_score
        + 4 * eat_threat_score
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