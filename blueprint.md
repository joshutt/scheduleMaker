## Project Blueprint: Schedule Maker

### 1. High-Level Vision
To generate a truly random and fair 14-week schedule for a 12-team fantasy football league that adheres to a specific set of custom constraints.

### 2. Core User Stories (MVP)
* As a League Commissioner, I can provide a CSV file containing my league's teams, divisions, and prior season standings in order to configure the generator for my specific league.
* As a League Commissioner, I can run a single script from my command line in order to produce a valid schedule that meets all of my league's structural and fairness rules.
* As a League Commissioner, I can view the complete, generated schedule in my console in order to easily copy, paste, and share it with the other league members.

### 3. Key Design Principles & Constraints
* **Script-Based Tool:** The solution will be a command-line script, prioritizing logic and functionality over a visual interface.
* **CSV-Driven Input:** All league setup data must be provided via a simple, easy-to-edit CSV file with `team_name`, `division_name`, and `previous_season_finish` columns.
* **Fixed League Structure:** The core algorithm will be designed specifically for a 12-team, 3-division, 14-week regular season format.
* **Enforce Matchup Quotas:** The schedule must guarantee that every team plays its divisional opponents exactly twice and its non-divisional opponents exactly once.
* **Deterministic Final Week:** Week 14 is not random; it is fixed to create "Rivalry Week" matchups (#1 vs. #2 and #3 vs. #4) within each division based on the previous year's standings.
* **Eliminate Pattern Repetition:** The schedule must ensure that no two pairs of teams who play each other twice have their rematches on the same two calendar weeks (e.g., if A-B play in weeks 4 & 9, C-D cannot also play in weeks 4 & 9).
* **Enforce Rematch Cooldown:** A minimum two-week gap must exist between the first and second games for any two teams that play each other twice.

### 4. Out of Scope for MVP
* **Graphical User Interface (GUI):** There will be no visual interface for input or output in this version.
* **Variable League Sizes/Structures:** The script will not support other league formats (e.g., 10 teams, 14 teams, or different divisional layouts).
* **Saving Output to File:** The script will print the schedule to the console; a feature to automatically save the output to a `.txt` or `.csv` file will be considered for a future release.
* **Advanced Strength-of-Schedule Balancing:** Beyond the fixed final week, the schedule will not use last year's standings to attempt any further strength-of-schedule balancing.