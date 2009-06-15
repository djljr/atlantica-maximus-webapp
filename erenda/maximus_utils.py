#!/usr/bin/env python2.5
import logging

from .models import Team, MatchupStatistics

from google.appengine.api import memcache
from google.appengine.ext import db 

def get_team_groups():
    
    team_groups = memcache.get("team_groups")
    if team_groups is not None:
        return team_groups
    else:
        teams = Team.all()
        team_groups = { }
        for team in teams:
            if not team.leader in team_groups:
                team_groups[team.leader] = []
            team_groups[team.leader].append(team)
        
        team_groups = [team_groups[k] for k in sorted(team_groups.keys(), lambda x,y: cmp(x.name, y.name))]
        memcache.add("team_groups", team_groups)
        return team_groups

def update_stats(winner, loser):
    existing = MatchupStatistics.gql("where team1 in (:1, :2) and team2 in (:2, :1)", winner.key(), loser.key())
    stats = None
    if existing.count() == 0:
        newStats = MatchupStatistics()
        newStats.team1 = winner
        newStats.team2 = loser
        newStats.team1_wins = 1
        newStats.team2_wins = 0
        
        update_win_loss_records(winner, loser)
        
        db.put([newStats, winner, loser])
        return (1, 0)
    elif existing.count() == 1:
        oldStats = existing.fetch(1)[0]
        if oldStats.team1.key() == winner.key():
            oldStats.team1_wins = oldStats.team1_wins + 1
        else:
            oldStats.team2_wins = oldStats.team2_wins + 1
            
        update_win_loss_records(winner, loser)
        db.put([oldStats, winner, loser])
        return (0, 1)
    else:
        logging.error("unexpected state: %s matchup statistics for the same team pair (expected 1)" % existing.count())
        return (0, 0)
def update_win_loss_records(winner, loser):
    if winner.wins:
        winner.wins = winner.wins + 1
    else:
        winner.wins = 1
        
    if loser.losses:
        loser.losses = loser.losses + 1
    else:
        loser.losses = 1