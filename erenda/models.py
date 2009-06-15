#!/usr/bin/env python2.5
from google.appengine.ext import db

class Mercenary(db.Model):
    name = db.StringProperty()
    type = db.StringProperty()

class Team(db.Model):
    leader = db.ReferenceProperty(Mercenary)
    wins = db.IntegerProperty()
    losses = db.IntegerProperty()

class TeamMember(db.Model):
    team = db.ReferenceProperty(Team)
    merc = db.ReferenceProperty(Mercenary)
    location = db.IntegerProperty()

class Matchup(db.Model):
    team1 = db.ReferenceProperty(Team, collection_name="team1_set")
    team2 = db.ReferenceProperty(Team, collection_name="team2_set")

class MatchResult(db.Model):
    winner = db.ReferenceProperty(Team, collection_name="winner_set")
    loser = db.ReferenceProperty(Team, collection_name="loser_set")

class MatchupStatistics(db.Model):
    team1 = db.ReferenceProperty(Team, collection_name="team1_stats_set")
    team2 = db.ReferenceProperty(Team, collection_name="team2_stats_set")
    team1_wins = db.IntegerProperty()
    team2_wins = db.IntegerProperty()

class Tournament(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    current_round = db.IntegerProperty()
    completed = db.BooleanProperty()
    winner = db.ReferenceProperty(Team, collection_name="tourney_winner_set")

class TournamentTeam(db.Model):
    tournament = db.ReferenceProperty(Tournament, collection_name="tourney_team_set")
    team = db.ReferenceProperty(Team, collection_name="participant_set")
    matchup_index = db.IntegerProperty()

class TournamentMatchup(db.Model):
    tournament = db.ReferenceProperty(Tournament, collection_name="tourney_match_set")
    matchup = db.ReferenceProperty(Matchup)
    round = db.IntegerProperty()
    index = db.IntegerProperty()