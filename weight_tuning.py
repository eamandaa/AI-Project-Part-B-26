import itertools
import os
import subprocess
import csv
import re
from datetime import datetime


GAMES_PER_SETTING = 1

# Change this to the command you normally use to run the game
# If your normal command is different, edit this line
BASE_COMMAND = [
    "python",
    "-m",
    "referee",
    "agent",
    "agent_base",
]

# Weight ranges to test.
# Keep this small first, otherwise it will take too long
WEIGHT_GRID = {
    "W_MATERIAL": [110, 120, 130, 140],
    "W_EAT": [40, 50, 60],
    "W_SAFE_EAT": [30, 40, 50],
    "W_THREAT": [18, 22, 26],
    "W_CASCADE_KILL": [16, 20, 24],
    "W_CASCADE_SELF_LOSS": [12, 15, 18],
    "W_TRAPPED": [4, 6, 8],
}




def run_one_game(weights: dict[str, int], game_number: int) -> dict:
    env = os.environ.copy()

    for key, value in weights.items():
        env[key] = str(value)

    try:
        result = subprocess.run(
            BASE_COMMAND,
            capture_output=True,
            text=True,
            env=env,
            timeout=220,
        )

        output = result.stdout + "\n" + result.stderr

    except subprocess.TimeoutExpired:
        return {
            "winner": "TIMEOUT_SCRIPT",
            "reason": "script timeout",
            "turns": None,
            "raw": "",
        }

    winner = parse_winner(output)
    turns = parse_last_turn(output)

    return {
        "winner": winner,
        "reason": "ok",
        "turns": turns,
        "raw": output[-3000:],  # keep only last part for debugging
    }


def parse_winner(output: str) -> str:
    lowered = output.lower()

    # Most important for your referee output
    if "winner is red" in lowered:
        return "RED"

    if "winner is blue" in lowered:
        return "BLUE"

    # Other possible formats
    if "winner: red" in lowered or "winner = red" in lowered:
        return "RED"

    if "winner: blue" in lowered or "winner = blue" in lowered:
        return "BLUE"

    # Timeout fallback
    if "red" in lowered and "exceeded available time" in lowered:
        return "BLUE"

    if "blue" in lowered and "exceeded available time" in lowered:
        return "RED"

    return "UNKNOWN"


def parse_last_turn(output: str):
    turns = re.findall(r"turn_begin\s+(\d+)", output)

    if not turns:
        turns = re.findall(r"turn\s+(\d+)", output)

    if turns:
        return int(turns[-1])

    return None


def generate_weight_settings():
    keys = list(WEIGHT_GRID.keys())
    values = [WEIGHT_GRID[key] for key in keys]

    for combo in itertools.product(*values):
        yield dict(zip(keys, combo))




def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"tuning_results_{timestamp}.csv"

    settings = list(generate_weight_settings())
    total_settings = len(settings)

    print(f"Testing {total_settings} weight settings")
    print(f"{GAMES_PER_SETTING} games per setting")
    print(f"Saving to {output_file}")

    fieldnames = [
        "setting_id",
        "wins_red",
        "wins_blue",
        "unknown",
        "avg_turns",
        "score",
        "W_MATERIAL",
        "W_EAT",
        "W_SAFE_EAT",
        "W_THREAT",
        "W_CASCADE_KILL",
        "W_CASCADE_SELF_LOSS",
        "W_TRAPPED",
    ]

    rows = []

    for idx, weights in enumerate(settings, start=1):
        wins_red = 0
        wins_blue = 0
        unknown = 0
        turn_list = []

        print(f"\n[{idx}/{total_settings}] Testing {weights}")

        for game_num in range(1, GAMES_PER_SETTING + 1):
            result = run_one_game(weights, game_num)
            winner = result["winner"]

            if winner == "RED":
                wins_red += 1
            elif winner == "BLUE":
                wins_blue += 1
            else:
                unknown += 1

            if result["turns"] is not None:
                turn_list.append(result["turns"])

            print(f"  Game {game_num}: winner={winner}, turns={result['turns']}")

        avg_turns = sum(turn_list) / len(turn_list) if turn_list else None

        # Score formula
        # prioritize RED wins, then faster wins
        score = wins_red * 100 - wins_blue * 100 - unknown * 20

        if avg_turns is not None:
            # If RED wins, faster is better
            # If mostly losing, longer survival is slightly better
            if wins_red >= wins_blue:
                score -= avg_turns * 0.2
            else:
                score += avg_turns * 0.05

        row = {
            "setting_id": idx,
            "wins_red": wins_red,
            "wins_blue": wins_blue,
            "unknown": unknown,
            "avg_turns": avg_turns,
            "score": score,
            **weights,
        }

        rows.append(row)

        # Save after every setting so you do not lose progress
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        best = sorted(rows, key=lambda r: r["score"], reverse=True)[0]
        print(f"  Current best: score={best['score']}, RED wins={best['wins_red']}, weights={extract_weights(best)}")

    print("\nDONE.")
    print("Top 10 settings:")

    top_rows = sorted(rows, key=lambda r: r["score"], reverse=True)[:10]

    for row in top_rows:
        print(
            f"score={row['score']}, "
            f"RED={row['wins_red']}, BLUE={row['wins_blue']}, "
            f"avg_turns={row['avg_turns']}, "
            f"weights={extract_weights(row)}"
        )


def extract_weights(row):
    return {
        "W_MATERIAL": row["W_MATERIAL"],
        "W_EAT": row["W_EAT"],
        "W_SAFE_EAT": row["W_SAFE_EAT"],
        "W_THREAT": row["W_THREAT"],
        "W_CASCADE_KILL": row["W_CASCADE_KILL"],
        "W_CASCADE_SELF_LOSS": row["W_CASCADE_SELF_LOSS"],
        "W_TRAPPED": row["W_TRAPPED"],
    }


if __name__ == "__main__":
    main()