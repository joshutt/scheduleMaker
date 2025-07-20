import csv
import random
from collections import defaultdict, Counter, deque
import sys
from itertools import combinations

# --- Constants based on the blueprint ---
TOTAL_TEAMS = 12
TOTAL_DIVISIONS = 3
TEAMS_PER_DIVISION = TOTAL_TEAMS // TOTAL_DIVISIONS
TOTAL_WEEKS = 14
GAMES_PER_WEEK = TOTAL_TEAMS // 2
REMATCH_COOLDOWN = 2  # Min 2-week gap means 3 weeks total (e.g., Week 1 -> Week 4)
# --- Heuristic Limits ---
BACKTRACK_LIMIT_PER_ATTEMPT = 1_000_000 # Give up on an attempt after this many backtracks
THRASHING_HISTORY_LENGTH = 200
THRASHING_DEEP_BACKTRACK_WEEKS = 4


class ScheduleMaker:
    """
    Generates a 14-week, 12-team fantasy football schedule based on specific constraints.
    """

    def __init__(self, teams_file_path):
        """Initializes the ScheduleMaker with the path to the teams CSV file."""
        self.teams_file_path = teams_file_path
        self.teams = []
        self.divisions = defaultdict(list)
        self.team_map = {}  # For easy lookup by name
        self.required_matchups = []
        self.search_iterations = 0
        self.rematches = set()  # To store matchups that occur twice for fast lookups
        self.last_printed_week = -1
        self.backtrack_count = 0
        # --- New attributes for thrashing detection ---
        self.week_history = deque(maxlen=200)
        self.force_backtrack_count = 0

    def load_and_validate_teams(self):
        """
        Loads team data from the CSV and validates its structure.
        Raises:
            FileNotFoundError: If the csv file cannot be found.
            ValueError: If the data within the csv is not valid.
        """
        print("Loading and validating teams...")
        try:
            with open(self.teams_file_path, mode='r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                # Sanitize field names to prevent issues with BOM or spacing
                reader.fieldnames = [name.strip().lower().replace(' ', '_') for name in reader.fieldnames]

                # Check for required columns
                required_columns = {'team_name', 'division_name', 'previous_season_finish'}
                if not required_columns.issubset(reader.fieldnames):
                    raise ValueError(f"CSV file is missing one of the required columns: {', '.join(required_columns)}")

                loaded_teams = list(reader)

        except FileNotFoundError:
            raise FileNotFoundError(f"Error: The file '{self.teams_file_path}' was not found.")
        except Exception as e:
            raise IOError(f"Error reading or parsing CSV file: {e}")

        # --- Data Validation ---
        if len(loaded_teams) != TOTAL_TEAMS:
            raise ValueError(f"Error: The CSV must contain exactly {TOTAL_TEAMS} teams. Found {len(loaded_teams)}.")

        for row in loaded_teams:
            try:
                team = {
                    'name': row['team_name'].strip(),
                    'division': row['division_name'].strip(),
                    'rank': int(row['previous_season_finish'])
                }
                if not team['name'] or not team['division']:
                    raise ValueError("Team name and division name cannot be empty.")
                self.teams.append(team)
                self.divisions[team['division']].append(team)
                self.team_map[team['name']] = team
            except (ValueError, KeyError) as e:
                raise ValueError(f"Error processing row: {row}. Please check data format. Details: {e}")

        if len(self.divisions) != TOTAL_DIVISIONS:
            raise ValueError(
                f"Error: The league must have exactly {TOTAL_DIVISIONS} divisions. Found {len(self.divisions)}.")

        for division_name, teams_in_division in self.divisions.items():
            if len(teams_in_division) != TEAMS_PER_DIVISION:
                raise ValueError(
                    f"Error: Division '{division_name}' must have {TEAMS_PER_DIVISION} teams. Found {len(teams_in_division)}.")

        print(f"Successfully loaded {TOTAL_TEAMS} teams into {TOTAL_DIVISIONS} divisions.")

    def generate_all_matchups(self):
        """
        Creates a master list of all games that must be played based on the rules.
        - Divisional teams play each other twice.
        - Non-divisional teams play each other once.
        This populates self.required_matchups.
        """
        print("Generating all required matchups...")
        matchups = []

        # 1. Generate divisional matchups (twice each)
        for teams_in_division in self.divisions.values():
            team_names = [team['name'] for team in teams_in_division]
            for team1, team2 in combinations(team_names, 2):
                matchups.append(tuple(sorted((team1, team2))))
                matchups.append(tuple(sorted((team1, team2))))

        # 2. Generate non-divisional matchups (once each)
        division_names = list(self.divisions.keys())
        for div1_name, div2_name in combinations(division_names, 2):
            teams_in_div1 = [team['name'] for team in self.divisions[div1_name]]
            teams_in_div2 = [team['name'] for team in self.divisions[div2_name]]
            for team1 in teams_in_div1:
                for team2 in teams_in_div2:
                    matchups.append(tuple(sorted((team1, team2))))

        # --- Pre-calculate rematches for performance ---
        matchup_counts = Counter(matchups)
        self.rematches = {match for match, count in matchup_counts.items() if count == 2}

        # Sanity check the total number of games
        expected_matchups = (TOTAL_TEAMS * TOTAL_WEEKS) // 2
        if len(matchups) != expected_matchups:
            raise RuntimeError(
                f"FATAL: Generated {len(matchups)} matchups, "
                f"but expected {expected_matchups}. Check generation logic."
            )

        # Shuffle the list to ensure the backtracking algorithm
        # doesn't always try matchups in a predictable order, leading to random schedules.
        random.shuffle(matchups)
        self.required_matchups = matchups

        print(f"Successfully generated {len(self.required_matchups)} total matchups to be scheduled.")

    def build_schedule(self):
        """
        Public method to orchestrate the schedule generation.
        It sets up Week 14 and then calls the recursive backtracking solver.
        """
        print("Building schedule...")
        schedule = {week: [] for week in range(1, TOTAL_WEEKS + 1)}
        matchups_to_schedule = self.required_matchups[:]

        # --- Pre-assign fixed Week 14 "Rivalry Week" matchups ---
        week14_matchups = []
        for division in self.divisions.values():
            sorted_teams = sorted(division, key=lambda x: x['rank'])
            t1, t2, t3, t4 = [t['name'] for t in sorted_teams]
            week14_matchups.append(tuple(sorted((t1, t2))))
            week14_matchups.append(tuple(sorted((t3, t4))))

        for match in week14_matchups:
            schedule[TOTAL_WEEKS].append(match)
            if match in matchups_to_schedule:
                matchups_to_schedule.remove(match)

        print(f"Fixed Week {TOTAL_WEEKS} (Rivalry Week) matchups.")

        # --- Start the recursive backtracking process ---
        self.search_iterations = 0  # Reset counter for this run
        self.last_printed_week = -1 # Add this line to reset the tracker
        self.backtrack_count = 0    # Reset backtrack counter for this run
        # --- Reset new attributes for this run ---
        self.week_history.clear()
        self.force_backtrack_count = 0

        if self._recursive_backtrack(schedule, matchups_to_schedule, 0):
            print()  # Final newline to move past the progress indicator line
            return schedule
        else:
            print()  # Final newline to move past the progress indicator line
            return None

    def _recursive_backtrack(self, schedule, matchups_to_schedule, slot_index):
        """
        The core recursive solver using a backtracking algorithm.
        It works backward from Week 13 to Week 1 for efficiency.
        """
        # Check if the attempt's backtrack budget has been exceeded$---
        if self.backtrack_count > BACKTRACK_LIMIT_PER_ATTEMPT:
            return False # This attempt is too costly, give up.

        # Handle forced deep backtrack
        if self.force_backtrack_count > 0:
            self.force_backtrack_count -= 1
            # Increment the main backtrack counter to keep the total accurate
            self.backtrack_count += 1
            return False  # Force this level to fail and unwind the stack

        self.search_iterations += 1

        # --- Progress Indicators ---
        if self.search_iterations % 1000 == 0:
            print(".", end="", flush=True)

        total_slots_to_fill = (TOTAL_WEEKS - 1) * GAMES_PER_WEEK
        if slot_index >= total_slots_to_fill:
            return True

        week = TOTAL_WEEKS - 1 - (slot_index // GAMES_PER_WEEK)

        # This logic ensures the "Solving for" message is only printed when the
        # week number changes, preventing repeats during backtracking.
        if week != self.last_printed_week:
            # if self.last_printed_week != -1:
            #     # Move to a new line after the dots from the previous week are done.
            #     print()
            # print(f"Solving for Week {week}...", end="", flush=True)
            self.last_printed_week = week
            self.week_history.append(week)

            # Thrashing Detection Logic
            if len(self.week_history) == 200 and len(set(self.week_history)) == 2:
                # print(f"\nThrashing detected between weeks {sorted(list(set(self.week_history)))}! Initiating a deep backtrack of 4 weeks...")
                # Set the counter to force N slots to backtrack (4 weeks * 6 games/week)
                self.force_backtrack_count = 4 * GAMES_PER_WEEK
                self.week_history.clear()  # Reset history to prevent immediate re-triggering
                return False  # Start the deep backtrack immediately

        for i in range(len(matchups_to_schedule)):
            matchup = matchups_to_schedule[i]
            team1, team2 = matchup

            # 1. Check if either team is already scheduled for this week.
            teams_in_week = {team for m in schedule[week] for team in m}
            if team1 in teams_in_week or team2 in teams_in_week:
                continue

            # 2. Check rematch constraints (cooldown and pattern repetition).
            is_rematch = matchup in self.rematches
            if is_rematch:
                other_game_week = None
                for w, games in schedule.items():
                    if w == week: continue
                    if matchup in games:
                        other_game_week = w
                        break

                if other_game_week:
                    if abs(week - other_game_week) <= REMATCH_COOLDOWN:
                        continue
                    rematch_week_pairs = self._get_rematch_week_pairs(schedule)
                    if tuple(sorted((other_game_week, week))) in rematch_week_pairs:
                        continue

            # --- Place and Recurse ---
            schedule[week].append(matchup)
            remaining_matchups = matchups_to_schedule[:i] + matchups_to_schedule[i + 1:]

            if self._recursive_backtrack(schedule, remaining_matchups, slot_index + 1):
                return True

            # --- Backtrack ---
            schedule[week].pop()
            self.backtrack_count += 1

            # Display a status update every 10,000 backtracks.
            # if self.backtrack_count % 10000 == 0:
                # The \r overwrites the current line; extra spaces clear any leftover dots.
                # print(f"\rSolving for Week {self.last_printed_week}... (Backtracks: {self.backtrack_count:,})          ", end="", flush=True)


        return False

    def _get_rematch_week_pairs(self, schedule):
        """Helper to find all week-pairs used by rematches in the current schedule."""
        match_locations = defaultdict(list)
        for week, games in schedule.items():
            for game in games:
                if game in self.rematches:
                    match_locations[game].append(week)

        rematch_pairs = set()
        for locations in match_locations.values():
            if len(locations) == 2:
                rematch_pairs.add(tuple(sorted(locations)))
        return rematch_pairs

    def validate_schedule(self, schedule):
        """
        Performs a final, comprehensive check on a completed schedule.
        Returns True if valid, False otherwise.
        """
        print("Validating final schedule...")
        all_scheduled_matchups = [match for week_games in schedule.values() for match in week_games]

        # 1. Check for correct total number of games
        if len(all_scheduled_matchups) != len(self.required_matchups):
            print(
                f"Validation Error: Incorrect number of total games. Expected {len(self.required_matchups)}, found {len(all_scheduled_matchups)}.")
            return False

        # 2. Check that all required matchups were scheduled exactly as required
        if Counter(all_scheduled_matchups) != Counter(self.required_matchups):
            print("Validation Error: The set of scheduled games does not match the required matchups.")
            return False

        # 3. Check weekly structure
        for week, games in schedule.items():
            if len(games) != GAMES_PER_WEEK:
                print(
                    f"Validation Error: Week {week} has an incorrect number of games. Expected {GAMES_PER_WEEK}, found {len(games)}.")
                return False
            teams_this_week = [team for match in games for team in match]
            if len(set(teams_this_week)) != TOTAL_TEAMS:
                print(f"Validation Error: Not all teams are playing in Week {week}.")
                return False

        # 4. Check fixed Week 14
        expected_w14 = set()
        for division in self.divisions.values():
            sorted_teams = sorted(division, key=lambda x: x['rank'])
            t1, t2, t3, t4 = [t['name'] for t in sorted_teams]
            expected_w14.add(tuple(sorted((t1, t2))))
            expected_w14.add(tuple(sorted((t3, t4))))

        if set(schedule[TOTAL_WEEKS]) != expected_w14:
            print(f"Validation Error: Week {TOTAL_WEEKS} matchups do not match the required Rivalry Week format.")
            return False

        # 5. Check rematch cooldown and pattern repetition
        rematch_week_pairs = self._get_rematch_week_pairs(schedule)
        match_locations = defaultdict(list)
        for week, games in schedule.items():
            for game in games:
                match_locations[game].append(week)

        for game, weeks in match_locations.items():
            if len(weeks) == 2:
                if abs(weeks[0] - weeks[1]) <= REMATCH_COOLDOWN:
                    print(f"Validation Error: Rematch {game} in weeks {weeks} violates the cooldown rule.")
                    return False

        if len(rematch_week_pairs) != len(self.rematches):
            print(f"Validation Error: A pattern repetition was found among rematch week-pairs.")
            return False

        print("Schedule is valid and meets all constraints.")
        return True

    def print_schedule(self, schedule):
        """
        Prints the generated schedule to the console in a readable format.
        """
        print("\n--- Generated Schedule ---")
        for week, matchups in sorted(schedule.items()):
            print(f"\nWeek {week}:")
            for match in sorted(matchups):
                print(f"  {match[0]} vs. {match[1]}")

    def run(self):
        """Main execution flow with a restarting heuristic."""
        try:
            self.load_and_validate_teams()
        except (ValueError, FileNotFoundError, IOError) as e:
            print(e, file=sys.stderr)
            return

        MAX_ATTEMPTS = 20
        final_schedule = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            print(f"\n--- Attempt {attempt} of {MAX_ATTEMPTS} ---")
            # Generate a new random order of matchups for each attempt
            self.generate_all_matchups()

            schedule = self.build_schedule()

            if schedule:
                print("\nSolution found! Validating...")
                if self.validate_schedule(schedule):
                    final_schedule = schedule
                    break  # Exit the loop on success
                else:
                    # This case should be rare, but it's a fatal error in the logic
                    print("\nCRITICAL: A schedule was found but failed validation. Please report this issue.")
                    return
            # If schedule is None, the loop will naturally continue to the next attempt
            else:
                # Check why the attempt failed to give a better message
                if self.backtrack_count > BACKTRACK_LIMIT_PER_ATTEMPT:
                    print(f"\nAttempt {attempt} failed: Backtrack limit of {BACKTRACK_LIMIT_PER_ATTEMPT:,} reached.")
                elif self.force_backtrack_count > 0:
                    # This case means we hit the thrashing limit and are mid-jump
                    pass # Don't print a failure message, just let it restart
                else:
                    print(f"\nAttempt {attempt} failed: No solution found for this path.")


        if final_schedule:
            print(f"\nSuccess! Schedule generated on attempt {attempt}.")
            print(f"Total backtracks for successful attempt: {self.backtrack_count:,}")
            self.print_schedule(final_schedule)
        else:
            print(f"\nCould not generate a valid schedule after {MAX_ATTEMPTS} attempts.")

if __name__ == "__main__":
    csv_file = "teams.csv"
    maker = ScheduleMaker(csv_file)
    maker.run()