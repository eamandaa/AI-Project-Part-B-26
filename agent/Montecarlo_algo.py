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

    # while time.time() - start < time_limit:
    #     node, path = select(root, board)
    #     print(f"after select: path={len(path)}, children={len(node.children)}, untried={node.untried_actions}")

    #     if not node.is_ended(board):
    #         node = expand(node, agent, board, path)
    #         print(f"after expand: path={len(path)}, root children={len(root.children)}")

    #     score = simulate(agent, board)
    #     print(f"after simulate: score={score}")

    #     backpropogation(node, score, board, path)
    #     print(f"after backprop: root visits={root.visits}")
        
    #     break 

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
            if neighbor in board._state:
                neighbor_cell = board._state[neighbor]
                if not neighbor_cell.is_empty:
                    if is_agent and neighbor_cell.color == opp_color and neighbor_cell.height <= cell.height:
                        agent_eat_threats += cell.height
                    elif not is_agent and neighbor_cell.color == agent_color and neighbor_cell.height >= cell.height:
                        opp_eat_threats += cell.height
    
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

        elif not is_agent and neighbor_cell.color == agent_color:
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
        + 4 * eat_threat_score
        + 6 * cascade_score
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