# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction

from referee.game import Board

from .placement_phase_heuristic import choose_best_action_during_placement
from .alpha_beta import choose_best_action 


class Agent:
    """
    This class is the "entry point" for your agent, providing an interface to
    respond to various Cascade game events.
    """

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        This constructor method runs when the referee instantiates the agent.
        Any setup and/or precomputation should be done here.
        """
        #Initialise of players
        self._color = color
        self._turn_count = 0
        self._board = Board()
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED (first player)")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")


    def action(self, **referee: dict) -> Action:
        """
        This method is called by the referee each time it is the agent's turn
        to take an action. It must always return an action object.
        """

        # Below we have hardcoded actions to be played depending on whether
        # the agent is playing as BLUE or RED. Obviously this won't work beyond
        # the initial moves of the game, so you should use some game playing
        # technique(s) to determine the best action to take.
        #print(cell.)

        # During placement phase (first 8 turns total, 4 per player)
        if self._turn_count < 4:

            match self._color:
                case PlayerColor.RED:
                    return choose_best_action_during_placement(self._board, 2, self._color)
                case PlayerColor.BLUE:
                    return choose_best_action_during_placement(self._board, 2,self._color)


        # During play phase - return an action
        #Base using min max alpha beta pruning 
        
        match self._color:
            case PlayerColor.RED:
                print("phase", self._board.phase)
                #print("Testing: RED is playing a MOVE action")
                return choose_best_action(self,self._board,depth = 3)
            case PlayerColor.BLUE:
                #print("Testing: BLUE is playing a MOVE action")
                return choose_best_action(self,self._board,depth = 3)
       

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        """
        This method is called by the referee after a player has taken their
        turn. You should use it to update the agent's internal game state.
        """
        if color == self._color:
            self._turn_count += 1

        # There are four possible action types: PLACE, MOVE, EAT, and CASCADE.
        # Below we check which type of action was played and print out the
        # details of the action for demonstration purposes. You should replace
        # this with your own logic to update your agent's internal game state.
        match action:
            case PlaceAction(coord):
                print(f"Testing: {color} played PLACE action at {coord}")
            case MoveAction(coord, direction):
                print(f"Testing: {color} played MOVE action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case EatAction(coord, direction):
                print(f"Testing: {color} played EAT action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case CascadeAction(coord, direction):
                print(f"Testing: {color} played CASCADE action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case _:
                raise ValueError(f"Unknown action type: {action}")
        self._board.apply_action(action)
