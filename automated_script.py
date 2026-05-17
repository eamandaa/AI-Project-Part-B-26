import argparse
import subprocess
import re
from statistics import mean

TURN_PATTERN = re.compile(r"\* referee : (?:RED|BLUE) to play \(turn (\d+)\)")
RESULT_PATTERN = re.compile(r"\* referee @ result:\s*(.*)", re.IGNORECASE)
NODE_PATTERN = re.compile(r"nodes expanded\s*=\s*(\d+)", re.IGNORECASE)


def extract_turn_count(output: str) -> int | None:
    matches = TURN_PATTERN.findall(output)
    if not matches:
        return None
    return int(matches[-1])


def extract_result_line(output: str) -> str:
    match = RESULT_PATTERN.search(output)
    if match:
        return match.group(1).strip()
    return "unknown"


def extract_nodes_expanded(output: str) -> list[int]:
    return [int(x) for x in NODE_PATTERN.findall(output)]


def run_game(agent_one: str, agent_two: str) -> str:
    result = subprocess.run(
        ["python", "-m", "referee", agent_one, agent_two],
        capture_output=True,
        text=True,
    )
    return result.stdout + "\n" + result.stderr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_one")
    parser.add_argument("agent_two")
    parser.add_argument("--games", type=int, default=4)
    args = parser.parse_args()

    num_win_player_one = 0
    num_win_player_two = 0
    num_draw = 0
    unknown = 0

    turn_counts: list[int] = []
    total_nodes_per_game: list[int] = []
    avg_nodes_per_move_per_game: list[float] = []

    for i in range(args.games):
        output = run_game(args.agent_one, args.agent_two)

        result = extract_result_line(output)
        turn_count = extract_turn_count(output)
        node_counts = extract_nodes_expanded(output)

        total_nodes = sum(node_counts)
        avg_nodes_per_move = total_nodes / len(node_counts) if node_counts else 0.0

        if turn_count is not None:
            turn_counts.append(turn_count)

        total_nodes_per_game.append(total_nodes)
        avg_nodes_per_move_per_game.append(avg_nodes_per_move)

        result_lower = result.lower()
        if "draw" in result_lower:
            num_draw += 1
        elif "player 1" in result_lower:
            num_win_player_one += 1
        elif "player 2" in result_lower:
            num_win_player_two += 1
        else:
            unknown += 1

        turn_text = str(turn_count) if turn_count is not None else "unknown"
        print(
            f"Game {i + 1}: {result} | "
            f"turns = {turn_text} | "
            f"total nodes = {total_nodes} | "
            f"avg nodes/move = {avg_nodes_per_move:.2f}"
        )

    avg_turns = mean(turn_counts) if turn_counts else 0.0
    avg_total_nodes = mean(total_nodes_per_game) if total_nodes_per_game else 0.0
    avg_nodes_per_move_overall = mean(avg_nodes_per_move_per_game) if avg_nodes_per_move_per_game else 0.0

    print("\n--- RESULTS ---")
    print(
        f"Player 1 {args.agent_one} = {num_win_player_one}, "
        f"win rate = {num_win_player_one / args.games * 100:.2f}%"
    )
    print(
        f"Player 2 {args.agent_two} = {num_win_player_two}, "
        f"win rate = {num_win_player_two / args.games * 100:.2f}%"
    )
    print(f"Draws: {num_draw}, draw rate = {num_draw / args.games * 100:.2f}%")
    print(f"Unknown: {unknown}")

    print("\n TURN STATS ")
    print(f"Turns per game: {turn_counts}")
    print(f"Average turns: {avg_turns:.2f}")

    print("\n NODE STATS ")
    print(f"Total nodes per game: {total_nodes_per_game}")
    print(f"Average total nodes per game: {avg_total_nodes:.2f}")
    print(f"Average nodes per move: {avg_nodes_per_move_overall:.2f}")


if __name__ == "__main__":
    main()