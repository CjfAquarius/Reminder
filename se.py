import cmd
import pickle
import os
import sys
from datetime import datetime

DATA_FILE = "scheduler.dat"

class SchedulerCmd(cmd.Cmd):
    intro = "Scheduler editor\tVersion 1.0\n" + "="*50 + "\nIndexes begin with 0 (Monday) and end with 6 (Sunday)."
    prompt = "(scheduler) >>> "

    def __init__(self):
        super().__init__()
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                self.schedule = pickle.load(f)
        else:
            # 7 lists, corresponding to 0~6 (Monday~Sunday)
            self.schedule = [[], [], [], [], [], [], []]

    def save_data(self):
        with open(DATA_FILE, "wb") as f:
            pickle.dump(self.schedule, f)
        print("Data saved.")

    def do_add(self, arg):
        """Add a plan. Usage: add weekday(0-6) time plan_content\nExample: add 0 14:30 meeting (0 means Monday)"""
        args = arg.split(maxsplit=2)
        if len(args) != 3:
            sys.stderr.write("Error: Incorrect number of arguments. Usage: add weekday(0-6) time plan_content\n")
            return
        
        try:
            weekday = int(args[0])
            if not 0 <= weekday <= 6:
                sys.stderr.write("Error: Weekday must be 0 (Monday) to 6 (Sunday).\n")
                return
            time_str = args[1]
            datetime.strptime(time_str, "%H:%M") # Validate time format
            plan_text = args[2]
            
            self.schedule[weekday].append([time_str, plan_text])
            self.schedule[weekday].sort(key=lambda x: x[0])
            self.save_data()
            print(f"Added: Day {weekday+1} {time_str} - {plan_text}")
            
        except ValueError:
            sys.stderr.write("Error: Weekday must be a number, time format must be HH:MM.\n")

    def do_copy(self, arg):
        """Copy plans. Usage: copy A B (copy plans from Day A to Day B)\nExample: copy 0 2 (copy Monday's plans to Wednesday)"""
        args = arg.split()
        if len(args) != 2:
            sys.stderr.write("Error: Incorrect number of arguments. Usage: copy A B\n")
            return
        
        try:
            src = int(args[0])
            dst = int(args[1])
            if not (0 <= src <= 6 and 0 <= dst <= 6):
                sys.stderr.write("Error: Weekday must be 0 (Monday) to 6 (Sunday).\n")
                return
            
            if not self.schedule[src]:
                sys.stderr.write(f"Warning: Day {src+1} is empty, nothing to copy.\n")
                return
            
            # Deep copy and append
            copied_items = [item[:] for item in self.schedule[src]]
            self.schedule[dst].extend(copied_items)
            self.schedule[dst].sort(key=lambda x: x[0])
            
            self.save_data()
            print(f"Success: {len(copied_items)} plan(s) from Day {src+1} have been copied and appended to Day {dst+1}.")
            
        except ValueError:
            sys.stderr.write("Error: Arguments must be numbers.\n")

    def do_clear(self, arg):
        """Clear plans. Usage: clear C\nExample: clear 2 (clear all plans for Wednesday)"""
        try:
            weekday = int(arg.strip())
            if not 0 <= weekday <= 6:
                sys.stderr.write("Error: Weekday must be 0 (Monday) to 6 (Sunday).\n")
                return
            
            if not self.schedule[weekday]:
                sys.stderr.write(f"Warning: Day {weekday+1} is already empty, no need to clear.\n")
                return
            
            count = len(self.schedule[weekday])
            self.schedule[weekday] = []
            self.save_data()
            print(f"Cleared {count} plan(s) from Day {weekday+1}.")
            
        except ValueError:
            sys.stderr.write("Error: Please enter a number (0-6).\n")

    def do_list(self, arg):
        """List all plans. Usage: list [weekday]"""
        if arg:
            try:
                weekday = int(arg)
                if not 0 <= weekday <= 6:
                    sys.stderr.write("Error: Weekday must be 0 (Monday) to 6 (Sunday).\n")
                    return
                print(f"\n--- Day {weekday+1} Plans ---")
                for t, p in self.schedule[weekday]:
                    print(f"  {t} : {p}")
            except ValueError:
                sys.stderr.write("Error: Please enter a number 0-6.\n")
        else:
            for i in range(7): # 0~6
                if self.schedule[i]:
                    print(f"\n--- Day {i+1} Plans ---")
                    for t, p in self.schedule[i]:
                        print(f"  {t} : {p}")
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
    def do_delete(self, arg):
        """Delete a plan. Usage: delete weekday index\nExample: delete 0 0 (delete the 1st plan of Monday)"""
        args = arg.split()
        if len(args) != 2:
            sys.stderr.write("Error: Incorrect number of arguments. Usage: delete weekday index\n")
            return
        
        try:
            weekday = int(args[0])
            index = int(args[1])
            if not 0 <= weekday <= 6:
                sys.stderr.write("Error: Weekday must be 0 (Monday) to 6 (Sunday).\n")
                return
            
            if 0 <= index < len(self.schedule[weekday]):
                removed = self.schedule[weekday].pop(index)
                self.save_data()
                print(f"Deleted: Day {weekday+1} {removed[0]} - {removed[1]}")
            else:
                sys.stderr.write(f"Error: Index out of range (Currently {len(self.schedule[weekday])} plan(s) available).\n")
        except ValueError:
            sys.stderr.write("Error: Weekday and index must be numbers.\n")

    def do_quit(self, arg):
        """Exit the editor"""
        print()
        return True

if __name__ == "__main__":
    SchedulerCmd().cmdloop()

