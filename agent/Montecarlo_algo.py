from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, CARDINAL_DIRECTIONS, IllegalActionException, GamePhase   

from referee.game import Board

import math

class MCTS_node:
    def __init__(self,board, parent=None, action=None):
        self.board = board #The board state at that node
        self.parent = parent #Parent node
        self.action = action #previous actions
        self.children = [] #children node
        self.wins = 0 #Backpropagation score
        self.visits = 0 #how many times has this node been visited
        self.untried_actions = None #populated on first expansion

    def fully_expanded(self):
        return 0
    
    #def game_over(self):

    def UCB1(self,exploration = 1.41): 
        if self.visits == 0:
            return math.inf #always do the unvisited one first
        return (self.wins / self.visits) + exploration * math.sqrt(math.log(self.parent.visits) / self.visits)


def mcts(agent,board) -> Action :
    return 0 

def select():
    return 0

def expand():
    return 0

def simulate():
    return 0

def backpropogation():
    return 0



def heuristic_func(self,board,agent_color) -> int:
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