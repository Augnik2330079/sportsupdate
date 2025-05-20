import sports
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import requests
from bs4 import BeautifulSoup

# Desktop notifications
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

import webbrowser

# sportsipy for NFL/NBA/MLB/NHL
from sportsipy.nfl.teams import Teams as NFLTeams
from sportsipy.nba.teams import Teams as NBATeams
from sportsipy.mlb.teams import Teams as MLBTeams
from sportsipy.nhl.teams import Teams as NHLTeams

# ------------------- Notification Manager -------------------
class NotificationManager:
    def __init__(self):
        self.last_scores = {}

    def send_notification(self, title, message):
        if PLYER_AVAILABLE:
            notification.notify(title=title, message=message, app_name='Sports Live', timeout=10)

    def check_and_notify(self, match, is_fav=False):
        key = f"{match['home']} vs {match['away']}"
        current_score = f"{match['home_score']}-{match['away_score']}"
        if key not in self.last_scores:
            if is_fav:
                self.send_notification("Match Started", f"{key} | Score: {current_score}")
            self.last_scores[key] = current_score
        elif self.last_scores[key] != current_score and is_fav:
            self.send_notification("Score Update", f"{key} | New Score: {current_score}")
            self.last_scores[key] = current_score

# ------------------- Social Sharing -------------------
class SocialSharing:
    def share(self, match, platform):
        text = f"Live: {match['home']} {match['home_score']}-{match['away_score']} {match['away']} #SportsLive"
        url = (
            f"https://twitter.com/intent/tweet?text={text.replace(' ', '%20')}" 
            if platform == "twitter" 
            else f"https://www.facebook.com/sharer/sharer.php?quote={text.replace(' ', '%20')}"
        )
        webbrowser.open(url)

# ------------------- Live Match Fetching -------------------
def fetch_all_live_matches():
    try:
        return [
            {
                'sport': sport,
                'league': getattr(match, 'league', ''),
                'home': getattr(match, 'home_team', ''),
                'away': getattr(match, 'away_team', ''),
                'home_score': getattr(match, 'home_score', ''),
                'away_score': getattr(match, 'away_score', ''),
                'status': getattr(match, 'match_time', ''),
                'date': getattr(match, 'match_date', ''),
            }
            for sport, matches in sports.all_matches().items()
            for match in matches
        ]
    except Exception as e:
        print(f"Error: {e}")
        return []

# ------------------- Team Stats Fetching -------------------
def fetch_team_stats(sport, team):
    # For NFL, NBA, MLB, NHL: use sportsipy
    try:
        if sport.lower() == "nfl":
            teams = NFLTeams()
        elif sport.lower() == "nba":
            teams = NBATeams()
        elif sport.lower() == "mlb":
            teams = MLBTeams()
        elif sport.lower() == "nhl":
            teams = NHLTeams()
        else:
            # For soccer and other sports, use sports.py (basic stats only)
            try:
                team_info = sports.get_team(sport, team)
                if hasattr(team_info, 'raw'):
                    return "\n".join([f"{k}: {v}" for k, v in team_info.raw.items()])
                else:
                    return "No stats available."
            except Exception as e:
                return f"Error fetching team stats: {e}"
        for t in teams:
            if team.lower() in t.name.lower():
                return t.dataframe.transpose().to_string()
        return "Team not found."
    except Exception as e:
        return f"Error: {str(e)}"

# ------------------- Cricket Scraping -------------------
def fetch_cricket_details():
    try:
        page = requests.get("https://www.espncricinfo.com/scores/")
        soup = BeautifulSoup(page.content, "html.parser")
        return [
            {
                'teams': " vs ".join([t.find("div", class_="name-detail").text for t in detail.find_all("div", class_="team")]),
                'score': (detail.find("div", class_="score-detail").text 
                          if detail.find("div", class_="score-detail") else "Match not started"),
                'summary': detail.find("span", class_="summary").text if detail.find("span", class_="summary") else ""
            }
            for detail in soup.find_all("div", class_="match-score-block")
        ]
    except Exception as e:
        return []

# ------------------- GUI Application -------------------
class SportsLiveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("All Sports Live")
        self.root.geometry("1200x700")
        self.favorites = set()
        self.notifier = NotificationManager()
        self.social = SocialSharing()
        self.setup_gui()
        self.start_update_thread()

    def setup_gui(self):
        # Title
        tk.Label(self.root, text="🏆 All Sports Live Updates", font=("Arial", 24, "bold")).pack(pady=10)
        
        # Favorites display
        self.fav_label = tk.Label(self.root, text="Favorites: None", font=("Arial", 12))
        self.fav_label.pack()

        # Matches table
        columns = ("Sport", "League", "Home", "Away", "Score", "Status", "Date")
        self.tree = ttk.Treeview(self.root, columns=columns, show='headings', height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140 if col == "League" else 100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        actions = [
            ("🔄 Refresh", self.refresh_data),
            ("⭐ Add Favorite", self.add_favorite),
            ("📊 Team Stats", self.show_stats),
            ("🏏 Cricket", self.show_cricket),
            ("🐦 Share Twitter", lambda: self.share("twitter")),
            ("📘 Share Facebook", lambda: self.share("facebook")),
            ("🚪 Exit", self.root.destroy)
        ]
        for text, cmd in actions:
            tk.Button(btn_frame, text=text, command=cmd).pack(side=tk.LEFT, padx=5)

    def refresh_data(self):
        matches = fetch_all_live_matches()
        self.tree.delete(*self.tree.get_children())
        for match in matches:
            score = f"{match['home_score']} - {match['away_score']}"
            self.tree.insert('', tk.END, values=(
                match['sport'],
                match['league'],
                match['home'],
                match['away'],
                score,
                match['status'],
                match['date']
            ))
            # Notify favorites
            if match['home'] in self.favorites or match['away'] in self.favorites:
                self.notifier.check_and_notify(match, is_fav=True)

    def add_favorite(self):
        selected = self.tree.item(self.tree.focus(), 'values')
        if selected:
            self.favorites.add(selected[2])  # Home team
            self.fav_label.config(text=f"Favorites: {', '.join(self.favorites)}")

    def show_stats(self):
        selected = self.tree.item(self.tree.focus(), 'values')
        if selected:
            sport, home = selected[0], selected[2]
            stats = fetch_team_stats(sport, home)
            messagebox.showinfo(f"{home} Stats", stats)

    def show_cricket(self):
        details = fetch_cricket_details()
        msg = "\n\n".join([f"{d['teams']}\n{d['score']}\n{d['summary']}" for d in details])
        messagebox.showinfo("Live Cricket", msg or "No matches found.")

    def share(self, platform):
        selected = self.tree.item(self.tree.focus(), 'values')
        if selected:
            match = {
                'home': selected[2],
                'away': selected[3],
                'home_score': selected[4].split(' - ')[0],
                'away_score': selected[4].split(' - ')[1]
            }
            self.social.share(match, platform)

    def start_update_thread(self):
        def update_loop():
            while True:
                self.refresh_data()
                time.sleep(30)
        threading.Thread(target=update_loop, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SportsLiveApp(root)
    root.mainloop()
