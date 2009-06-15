#!/usr/bin/env python2.5
import os
import logging

from .models import MatchResult, Matchup
from .maximus_utils import get_team_groups

from google.appengine.ext import webapp
from google.appengine.ext import db 
from google.appengine.ext.webapp import template

class ResultDetail(webapp.RequestHandler):
    def get(self):
        result_key = db.Key(self.request.get('match'))
        match = MatchResult.get(result_key)

        model = { 'match': match }
        path=os.path.join(os.path.dirname(__file__), '../templates/result_detail.html')
        self.response.out.write(template.render(path, model))

class ResultHistory(webapp.RequestHandler):
    def get(self):
        matches = MatchResult.all()
        model = { 'matches': matches }

        path=os.path.join(os.path.dirname(__file__), '../templates/results.html')
        self.response.out.write(template.render(path, model))

class MatchupDelete(webapp.RequestHandler):
    def post(self):
        match_key = db.Key(self.request.get('match_key'))
        match = Matchup.get(match_key)
        match.delete()
        
        self.redirect('/matchup')
    
class MatchupResult(webapp.RequestHandler):
    def post(self):
        match_key = db.Key(self.request.get('match_key'))
        match = Matchup.get(match_key)

        winner_key = db.Key(self.request.get('winner'))
        result = MatchResult()
        if winner_key == match.team1.key():
            result.winner = match.team1
            result.loser = match.team2
        elif winner_key == match.team2.key():
            result.winner = match.team2
            result.loser = match.team1
        else:
            logging.error("could not determine winner key: %s" % winner_key)
            
        update_stats(result.winner, result.loser)
        result.put()
        match.delete()
        
        memcache.delete("team_groups")
        self.redirect('/matchup')

class CreateMatchup(webapp.RequestHandler):
    def get(self):
        matches = Matchup.all()

        model = { 'teams': get_team_groups(),
                  'matches': matches,
                  'check_team_box': True }
        path=os.path.join(os.path.dirname(__file__), '../templates/matchup.html')
        self.response.out.write(template.render(path, model))
    def post(self):
        keys = self.request.get_all('versus')
        key_team1 = keys[0]
        key_team2 = keys[1]

        team1 = db.get(db.Key(key_team1))
        team2 = db.get(db.Key(key_team2))

        matchup = Matchup()
        matchup.team1 = team1
        matchup.team2 = team2
        matchup.put()

        self.redirect('/matchup')