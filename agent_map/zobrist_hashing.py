import random
from referee.game import constants, Coord, PlayerColor, Board, Action
from enum import Enum

random.seed(42)

class ScoreFlag(Enum):
    EXACT = 1
    LOWER_BOUND = 2
    UPPER_BOUND = 3

class TranpositionTable:
    hash_key: int
    search_depth: int
    evaluation_score: int
    score_flag: ScoreFlag
    best_move: Action



def get_zobrist_table():
    zobrist_table = initialise_zobrist_hashing_table()
    return zobrist_table

def generate_random_num():
    """
    Reference: https://www.geeksforgeeks.org/dsa/minimax-algorithm-in-game-theory-set-5-zobrist-hashing/
    """
    return random.randint(0, (1 << 64) - 1)

def initialise_zobrist_hashing_table(
)-> list[list[list[list[int]]]]:

    """
    Initialise the hash table using zobrist hashing method
    4D-array : [row[col[colour[height]]]]
    """

    max_height = (constants.PLACEMENT_TURNS // 2) * constants.INITIAL_STACK_HEIGHT

    hash_table = []
    for _ in range(constants.BOARD_N):
        row = []
        for _ in range(constants.BOARD_N):
            col = []
            # for each player colour
            for _ in range(constants.NUM_PLAYERS):
                height = []
                for _ in range(max_height):
                    random_num = generate_random_num()
                    height.append(random_num)
                col.append(height)
            row.append(col)
        hash_table.append(row)

    return hash_table 

ZOBRSIT_TABLE = initialise_zobrist_hashing_table()
TURN_KEY = generate_random_num()

def compute_hash(
    board: Board,
) -> int:
    h = 0

    for curr_coord in board._state:
        if (board._cell_empty(curr_coord)):
            continue

        cell_state = board.__getitem__(curr_coord)

        if cell_state.color == PlayerColor.RED:
            colour = 0
        else:
            colour = 1

        height = cell_state.height - 1
        h ^= ZOBRSIT_TABLE[curr_coord.r][curr_coord.c][colour][height]

    if board._turn_color == PlayerColor.RED:
        h ^= TURN_KEY

    return h