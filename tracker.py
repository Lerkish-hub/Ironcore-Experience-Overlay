from datetime import datetime, timedelta


class ExpTracker:
    def __init__(self):
        self.history = []          # Last 10 min window
        self.session_start = None  # First EXP seen
        self.session_current = None

    def add(self, exp_value):
        now = datetime.now()

        # Initialize session start once
        if self.session_start is None:
            self.session_start = exp_value

        self.session_current = exp_value

        # Add to rolling history
        self.history.append((now, exp_value))

        # Keep only last 10 minutes for rate calculations
        cutoff = now - timedelta(minutes=10)
        self.history = [h for h in self.history if h[0] >= cutoff]

    # -----------------------------
    # EXP gained in last 10 minutes
    # -----------------------------
    def exp_last_10_min(self):
        if len(self.history) < 2:
            return 0

        first_time, first_exp = self.history[0]
        last_time, last_exp = self.history[-1]

        gained = last_exp - first_exp
        return max(gained, 0)

    # -----------------------------
    # EXP per hour estimate
    # -----------------------------
    def exp_per_hour_estimate(self):
        if len(self.history) < 2:
            return 0

        first_time, first_exp = self.history[0]
        last_time, last_exp = self.history[-1]

        seconds = (last_time - first_time).total_seconds()

        if seconds <= 0:
            return 0

        gained = last_exp - first_exp

        if gained <= 0:
            return 0

        return int((gained / seconds) * 3600)

    # -----------------------------
    # Total session EXP gained
    # -----------------------------
    def session_total(self):
        if self.session_start is None or self.session_current is None:
            return 0

        gained = self.session_current - self.session_start
        return max(gained, 0)

    def reset_session(self):
        self.history.clear()
        self.session_start = None
        self.session_current = None
