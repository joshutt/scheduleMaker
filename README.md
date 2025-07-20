# Fantasy Football Schedule Maker

This project contains a Python script, `schedule_maker.py`, that generates a valid 14-week, 12-team fantasy football schedule based on a complex set of rules. It uses a backtracking algorithm with advanced heuristics (like thrashing detection and a restarting mechanism) to efficiently find a schedule that meets all constraints.

## Features

The generated schedule adheres to the following rules:
- **League Structure:** 12 teams, organized into 3 divisions of 4 teams each.
- **Schedule Length:** A full 14-week regular season.
- **Matchup Quotas:**
    - Each team plays its divisional opponents **twice**.
    - Each team plays every non-divisional opponent **once**.
- **Rivalry Week:** Week 14 is a fixed "Rivalry Week" where divisional opponents play each other based on the previous season's finish (1st vs. 2nd, 3rd vs. 4th).
- **Rematch Cooldown:** There is a minimum 2-week gap between the first and second games of a divisional rematch (e.g., a Week 1 rematch cannot occur in Week 2 or 3).
- **No Pattern Repetition:** The week-pairs for rematches are unique. For example, if one rematch occurs in Weeks (2, 8), no other rematch can use that same pair of weeks.

## Prerequisites

- Python 3.x
- No external libraries are required. The script only uses modules from the Python standard library.

## Setup

1.  **Place the files:** Ensure `schedule_maker.py` and your team data file are in the same directory.
2.  **Create your teams file:** The script requires a CSV file named `teams.csv` to load team data. This file **must** contain the following three columns:
    - `team_name`: The unique name of the team.
    - `division_name`: The name of the division the team belongs to.
    - `previous_season_finish`: The team's rank within their division from the prior season (1-4).

### Example `teams.csv`

```csv
team_name,division_name,previous_season_finish
Vortex Vipers,Quantum,1
Galaxy Gladiators,Quantum,2
Nebula Ninjas,Quantum,3
Cosmic Comets,Quantum,4
Avalanche Aces,Atomic,1
Fusion Phantoms,Atomic,2
Reactor Rebels,Atomic,3
Proton Predators,Atomic,4
Byte-sized Brawlers,Binary,1
Silicon Strikers,Binary,2
Digital Dynamos,Binary,3
Firewall Phalanx,Binary,4
```

## How to Run

1.  Open a terminal or command prompt.
2.  Navigate to the directory where you saved the project files.
3.  Run the script using the following command:
```shell
python schedule_maker.py
```

## Expected Output
The script will provide real-time feedback as it works to find a valid schedule.

```commandline
Loading and validating teams...
Successfully loaded 12 teams into 3 divisions.
Generating all required matchups...
Successfully generated 84 total matchups to be scheduled.

--- Attempt 1 of 20 ---
Building schedule...
Fixed Week 14 (Rivalry Week) matchups.
Solving for Week 13...
Solving for Week 12...
Solving for Week 11...
...
Solving for Week 1...

Solution found! Validating...
Schedule is valid and meets all constraints.

Success! Schedule generated on attempt 1.
Total backtracks for successful attempt: 1,234

--- Generated Schedule ---

Week 1:
  Avalanche Aces vs. Byte-sized Brawlers
  Cosmic Comets vs. Digital Dynamos
  ...
```

### If a Solution Isn't Found Quickly

The script uses a restarting heuristic. If one attempt takes too long (by exceeding a backtrack limit), it will automatically abandon it and start a new one with a different random seed. This significantly increases the chances of finding a solution quickly.
```commandline
...
Solving for Week 2...
Attempt 1 failed: Backtrack limit of 5,000,000 reached.

--- Attempt 2 of 20 ---
Building schedule...
...
```