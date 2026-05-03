import argparse
import subprocess
import re

def parse_result(output: str):
    """
    Extracts winner from referee output
    """

    match = re.search(r"result:\s*(.*)", output.lower())
    if not match:
        return "unknown"
    
    result = match.group(1).strip()

    if "draw" in result:
        return "draw"
    
    return result

def run_game(agent_one, agent_two):
    result = subprocess.run(
        ["python", "-m", "referee", agent_one, agent_two],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    return parse_result(result.stdout)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_one")
    parser.add_argument("agent_two")

    args = parser.parse_args()

    num_win_player_one = 0
    num_win_player_two = 0
    num_draw = 0
    unknown = 0

    total_round_game = 2

    for i in range(total_round_game):
        result = run_game(args.agent_one, args.agent_two)

        print(f"Game {i + 1} : {result}")

        if "draw" in result:
            num_draw += 1
        elif "player 1" in result:
            num_win_player_one += 1
        elif "player 2" in result:
            num_win_player_two += 1
        else:
            unknown += 1

    print("\n\n--- RESULTS ---")
    print(f"{args.agent_one} = {num_win_player_one}, win rate = {num_win_player_one / total_round_game * 100:.2f}%")
    print(f"{args.agent_two} = {num_win_player_two}, win rate = {num_win_player_two / total_round_game * 100:.2f}%")
    print(f"Draws: {num_draw}, draw rate = {num_draw / total_round_game * 100:.2f}%")
    print(f"Unknown: {unknown}, error happens if unknown has value! ")


if __name__ == "__main__":
    main()