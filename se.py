def do_addx(self, arg):
        """Add multiple plans to one weekday. Usage: addx weekday
Then input lines of 'time content'. Press Ctrl+D (EOF) to finish.
Example:
  addx 0
  09:00 standup
  14:30 meeting
  (Ctrl+D)
"""
        arg = arg.strip()
        if not arg:
            sys.stderr.write("Error: Usage: addx weekday\n")
            return

        try:
            weekday = int(arg)
        except ValueError:
            sys.stderr.write("Error: weekday must be a number 0-6.\n")
            return

        if not 0 <= weekday <= 6:
            sys.stderr.write("Error: Weekday must be 0 (Monday) to 6 (Sunday).\n")
            return

        print(f"Enter plans for Day {weekday+1} (time content), one per line. Ctrl+D to finish:")
        added = 0
        try:
            while True:
                try:
                    line = input(f"  [{added+1}] ").strip()
                except EOFError:
                    # Ctrl+D pressed
                    break

                if not line:
                    continue

                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    sys.stderr.write("  Error: format must be 'time content'. Ignored.\n")
                    continue

                time_str, plan_text = parts
                try:
                    datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    sys.stderr.write(f"  Error: invalid time '{time_str}'. Ignored.\n")
                    continue

                self.schedule[weekday].append([time_str, plan_text])
                print(f"  Added: {time_str} - {plan_text}")
                added += 1

        finally:
            if added > 0:
                self.schedule[weekday].sort(key=lambda x: x[0])
                self.save_data()
            print(f"\nDone. {added} plan(s) added to Day {weekday+1}.")
