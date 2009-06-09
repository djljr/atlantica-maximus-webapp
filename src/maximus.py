#!/usr/bin/env python2.5

import cgi
import os
import logging

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template

class Mercenary(db.Model):
	name = db.StringProperty()
	type = db.StringProperty()

class Team(db.Model):
	leader = db.ReferenceProperty(Mercenary)

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





class Index(webapp.RequestHandler):
	def get(self):
		path=os.path.join(os.path.dirname(__file__), '../templates/index.html')
		logging.info(path)
		self.response.out.write(template.render(path, {}))

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

		logging.info(self.request.get_all('winner'))
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
		result.put()
		match.delete()
		self.redirect('/matchup')

class CreateMatchup(webapp.RequestHandler):
	def get(self):
		teams = Team.all()
		matches = Matchup.all()

		model = { 'teams': get_team_groups(teams),
				  'matches': matches }
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

class DeleteTeam(webapp.RequestHandler):
	def get(self):
		team_key = db.Key(self.request.get("team"))
		
		team = db.get(team_key)
		teams = Team.gql("where leader = :1", team.leader)
		
		model = { 'todelete': team, 'teams': get_team_groups(teams) }
		path=os.path.join(os.path.dirname(__file__), '../templates/delete_team.html')
		self.response.out.write(template.render(path, model))
		
	def post(self):
		toreassign_string = self.request.get("reassign")
		logging.info("toreassign: %s" % toreassign_string)
		if toreassign_string:
			todelete_key = db.Key(self.request.get("todelete"))
			toreassign_key = db.Key(toreassign_string)
			logging.info("todelete: %s" % todelete_key)
			
			if todelete_key != toreassign_key:
				todelete = Team.get(todelete_key)
				toreassign = Team.get(toreassign_key)
				logging.info("keys were not the same")
				
				logging.info("leaders: %s == %s", todelete.leader.key(), toreassign.leader.key())
				if todelete.leader.key() == toreassign.leader.key():
					logging.info("leaders were the same")
					won_matches = MatchResult.gql("where winner = :1", todelete)
					lost_matches = MatchResult.gql("where loser = :1", todelete)
					for match in won_matches:
						if match.winner.key() == todelete.key():
							match.winner = toreassign
					for match in lost_matches:
						if match.loser.key() == todelete.key():
							match.loser = toreassign
					
					todelete.delete()
					
		self.redirect('/teams') 
		
	
class CreateTeam(webapp.RequestHandler):
	def get(self):
		teams = Team.all()

		heroes = Mercenary.gql("where type = 'Hero'")
		pawns = Mercenary.gql("where type = 'Pawn'")

		model = { 'heroes': heroes, 'pawns': pawns, 'mercrange': range(1,7), 'teams': get_team_groups(teams) }
		path=os.path.join(os.path.dirname(__file__), '../templates/teams.html')
		self.response.out.write(template.render(path, model))
	def post(self):
		team = Team()
		classc = self.request.get('hero')
		leader = Mercenary.gql("where type='Hero' and name=:1", classc)
		team.leader = leader[0]
		team.put()
		for i in range(1,10):
			who = self.request.get('pawn%s' % i)
			if who != '':
				merc = Mercenary.gql("where type = 'Pawn' and name = :1", who)
				current = TeamMember()
				current.team = team
				current.merc = merc[0]
				current.location = i
				current.put()
		self.redirect('/teams')


class CreateMerc(webapp.RequestHandler):
	def get(self):

		self.response.out.write("""
		<html><body>
		<form method="post">
			<div>Name: <input type="text" name="name" /></div>
			<div>Type: <select name="type"><option value="Hero">Hero</option><option value="Pawn">Pawn</option></select>
			<div><input type="submit" value="Submit" /></div>
		</form>
		""")

		mercs = Mercenary.gql("order by type, name")
		for merc in mercs:
			if merc.type == 'Hero':
				self.response.out.write('<div><b>%s</b></div>' % merc.name)
			else:
				self.response.out.write('<div>%s</div>' % merc.name)
		self.response.out.write('</body></html>')
	def post(self):
		merc = Mercenary()
		merc.name = self.request.get('name')
		merc.type = self.request.get('type')
		merc.put()

		self.redirect('/mercs')


application = webapp.WSGIApplication(
                                     [('/', Index),
									  ('/mercs', CreateMerc),
									  ('/teams', CreateTeam),
									  ('/teams/delete', DeleteTeam),
									  ('/matchup', CreateMatchup),
									  ('/matchup/delete', MatchupDelete),
									  ('/matchup/result', MatchupResult),
									  ('/results', ResultHistory),
									  ('/results/detail', ResultDetail)],
                                     debug=True)

def get_team_groups(teams):
	team_groups = { }
	for team in teams:
		if not team.leader in team_groups:
			team_groups[team.leader] = []
		team_groups[team.leader].append(team)
		
	return [team_groups[k] for k in sorted(team_groups.keys(), lambda x,y: cmp(x.name, y.name))]

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
