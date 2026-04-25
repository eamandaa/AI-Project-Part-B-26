# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction

from referee.game import Board
from .zobrist_hashing import initialise_zobrist_hashing_table,generate_random_num

from .placement_phase_heuristic import choose_best_action_during_placement
from .moving_order_heuristic import choose_best_action_during_placement_with_move_order, compute_distance_heatmap, iterative_deepening
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
        self._cells = self._find_cells(self._board, color)
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED (first player)")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")
        
        # precompute heatmap based on distance (centre and edges)
        self._distance_heatmap = compute_distance_heatmap()
        self._tranposition_table = {}

        self.referee = referee

    def _find_cells(
        self, 
        board: Board, 
        my_colour: PlayerColor
    ) -> dict[int, list[Coord] | None]:

        cells = {
            "my_cell": [],
            "enemy_cell": [],
            "empty_cell": []
        }

        for coord, cell in board._state.items():
            if cell.is_empty:
                cells['empty_cell'].append(coord)
            elif cell.color == my_colour:
                cells['my_cell'].append(coord)
            else:
                cells['enemy_cell'].append(coord)

        return cells


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
                    # action = choose_best_action_during_placement_with_move_order(
                    #     self._board, 
                    #     3, 
                    #     self._color,
                    #     self._cells['empty_cell'],
                    #     self._distance_heatmap,
                    #     self._tranposition_table
                    # )
                    action =iterative_deepening(
                        self._board, 
                        self._color,
                        self._cells['empty_cell'],
                        self._distance_heatmap,
                        self._tranposition_table
                    )
                    if referee["time_remaining"] is not None:
                        print(f"time remaining for RED = {referee["time_remaining"]}")
                    if referee['space_remaining'] is not None:
                        print(f"space remaining for RED = {referee["space_remaining"]}")
                    return action
                case PlayerColor.BLUE:
                    action =iterative_deepening(
                        self._board, 
                        self._color,
                        self._cells['empty_cell'],
                        self._distance_heatmap,
                        self._tranposition_table
                    )
                    if referee["time_remaining"] is not None:
                        print(f"time remaining for BLUE = {referee["time_remaining"]}")
                    if referee['space_remaining'] is not None:
                        print(f"space remaining for BLUE = {referee["space_remaining"]}")
                    return action


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
        self._cells = self._find_cells(self._board, self._color)

   