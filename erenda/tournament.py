#!/usr/bin/env python2.5
import os

from .models import Team, Matchup, TournamentMatchup, Tournament, TournamentTeam
from .maximus_utils import get_team_groups

from google.appengine.ext import db 
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

round_matches = [[None for i in range(0,8)],[None for i in range(0,4)],[None, None]]

class TournamentMatchups(webapp.RequestHandler):
    def get(self):
        tourney = db.get(db.Key(self.request.get("tournament")))
        teams = []
        for team in tourney.tourney_team_set:
            teams.append(team.team)
        matches = [None, None, None]
        for match in tourney.tourney_match_set:
            if not match.round in matches:
                matches[match.round] = []
            matches[match.round][match.index] = match
            
        model = { "teams": teams, "matches": matches}
        
        path = os.path.join(os.path.dirname(__file__), '../templates/tournament/matchups.html')
        self.response.out.write(template.render(path, model))
        
    def post(self):
        tourney = db.get(db.Key(self.request.get("tournament")))
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
        
class CreateTournament(webapp.RequestHandler):
    def get(self):
        model = { 'teams': get_team_groups() }
        path=os.path.join(os.path.dirname(__file__), '../templates/tournament/create.html')
        self.response.out.write(template.render(path, model))
        
    def post(self):
        tournament = Tournament()
        tournament.current_round = 0
        
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

        logging.info(models)
        self.redirect('/tournament/matchups?tournament=' + str(tournament.key()))