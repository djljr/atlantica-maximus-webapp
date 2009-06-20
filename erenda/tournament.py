#!/usr/bin/env python2.5
import os
import logging

from .models import Team, Matchup, TournamentMatchup, Tournament, TournamentTeam, MatchResult
from .maximus_utils import get_team_groups, update_stats

from google.appengine.api import memcache
from google.appengine.ext import db 
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class TournamentMatchResult(webapp.RequestHandler):
    def post(self):
        tournament_match_key = db.Key(self.request.get('tournament_match_key'))
        match = TournamentMatchup.get(tournament_match_key)

        winner_key = db.Key(self.request.get('winner'))
        matchup = match.matchup
        result = MatchResult()
        if winner_key == matchup.team1.key():
            result.winner = matchup.team1
            result.loser = matchup.team2
        elif winner_key == matchup.team2.key():
            result.winner = matchup.team2
            result.loser = matchup.team1
        else:
            logging.error("could not determine winner key: %s" % winner_key)
            
        update_stats(result.winner, result.loser)
        result.put()
        
        next_round_indices = {0:0, 1:0, 2:1, 3:1}
        next_round_index = next_round_indices[match.index]
        next_round = match.round + 1
        if match.round < 2:
            # look in existing matches for this winner's opponent
            existing = TournamentMatchup.gql("where tournament = :1 and round = :3 and index = :2", match.tournament, next_round_index, next_round)
            if existing.count() == 1:
                next_match = existing[0]
                next_matchup = next_match.matchup
                next_matchup.team2 = result.winner
                db.put(next_matchup)
            elif existing.count() == 0:
                next_match = TournamentMatchup()
                next_matchup = Matchup()
                next_matchup.team1 = result.winner
                db.put(next_matchup)
                
                next_match.tournament = match.tournament
                next_match.round = next_round
                next_match.index = next_round_index
                next_match.matchup = next_matchup
                db.put(next_match)
        else:
            tourney = match.tournament
            tourney.completed = True
            tourney.winner = result.winner
            db.put(tourney)
            
        match.matchup.delete()
        match.matchup = None
        match.result = result
        match.put()
        
        memcache.delete("team_groups")
        self.redirect('/tournament/matchups?tournament=%s' % str(match.tournament.key()))
        
class TournamentMatchups(webapp.RequestHandler):
    def get(self):
        tourney = db.get(db.Key(self.request.get("tournament")))
        teams = []
        for team in tourney.tourney_team_set:
            if team.matchup_index == None:
                teams.append(team.team) 
        matches = [[i for i in range(0,4)],[i for i in range(0,2)],[0]]
        for match in tourney.tourney_match_set:
            matches[match.round][match.index] = match
            
        model = { "teams": teams, "matches": matches, "tourney": tourney}
        
        path = os.path.join(os.path.dirname(__file__), '../templates/tournament/matchups.html')
        self.response.out.write(template.render(path, model))
    def post(self):
        tourney_key = self.request.get("tournament")
        tourney = db.get(db.Key(tourney_key))
        versus = self.request.get_all("versus")
        teams = []
        for team_key in versus:
            if team_key != "":
                teams.append(db.get(db.Key(team_key)))
        
        existing_matches = TournamentMatchup.gql("where tournament = :1", tourney)
        
        match = Matchup()
        match.team1 = teams[0]
        match.team2 = teams[1]
        db.put(match)
        
        tourney_match = TournamentMatchup()
        tourney_match.tournament = tourney
        tourney_match.matchup = match
        tourney_match.round = 0
        tourney_match.index = existing_matches.count()
        db.put(tourney_match)
        
        tourney_teams = []
        tourney_teams.append(TournamentTeam.gql("where tournament = :1 and team = :2", tourney, teams[0]).fetch(1)[0])
        tourney_teams.append(TournamentTeam.gql("where tournament = :1 and team = :2", tourney, teams[1]).fetch(1)[0])
        
        tourney_teams[0].matchup_index = tourney_match.index * 2
        tourney_teams[1].matchup_index = tourney_match.index * 2 + 1
        
        db.put(tourney_teams)
        
        self.redirect("/tournament/matchups?tournament=%s" % tourney_key)
        
class CreateTournament(webapp.RequestHandler):
    def get(self):
        inprogress = Tournament.gql("where completed = false");
        finished = Tournament.gql("where completed = true");
        model = { 'teams': get_team_groups(), "inprogress": inprogress, "finished": finished }
        path=os.path.join(os.path.dirname(__file__), '../templates/tournament/create.html')
        self.response.out.write(template.render(path, model))
        
    def post(self):
        tournament = Tournament()
        tournament.completed = False
        
        db.put(tournament)
        models = []
        for team_key in self.request.get_all('participant'):
            if team_key != "":
                team = db.get(db.Key(team_key))
                tourney_team = TournamentTeam()
                tourney_team.tournament = tournament
                tourney_team.team = team
                models.append(tourney_team)
        
        db.put(models)

        self.redirect('/tournament/matchups?tournament=%s' % str(tournament.key()))