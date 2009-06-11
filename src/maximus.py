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

class BuildWinLoss(webapp.RequestHandler):
	def post(self):
		logging.info("Rebuilding win-loss records")
		batch_size = 10
		batch = MatchResult.gql("order by __key__")
		
		query = "where __key__ > :1 order by __key__"
		
		matchups = []
		for matchup_stats in MatchupStatistics.all():
			matchups.append(matchup_stats)
		db.delete(matchups)
		
		total_count = 0
		total_create = 0
		total_update = 0
		batch_count = batch.count()
		logging.info("new batch size: %s", batch_count)
		while batch_count > 0:
			for match in batch.fetch(batch_size):
				(created, updated) = update_stats(match.winner, match.loser)
				total_create = total_create + created
				total_update = total_update + updated
				total_count = total_count + 1
			
			logging.info("so far created %s and updated %s" % (total_create, total_update))
			last_key = batch.fetch(1, min([batch_size, batch_count]) - 1)[0].key()
			batch = MatchResult.gql(query, last_key)
			batch_count = batch.count()
			logging.info("new batch size: %s", batch_count)
		
		self.redirect("/admin?match_count=%s&created=%s&updated=%s" % (total_count, total_create, total_update))
		
class Admin(webapp.RequestHandler):
	def get(self):
		model = { }
		path=os.path.join(os.path.dirname(__file__), '../templates/admin.html')
		self.response.out.write(template.render(path, model))
	
class Index(webapp.RequestHandler):
	def get(self):
		path=os.path.join(os.path.dirname(__file__), '../templates/index.html')
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
		if toreassign_string:
			todelete_key = db.Key(self.request.get("todelete"))
			toreassign_key = db.Key(toreassign_string)
			
			if todelete_key != toreassign_key:
				todelete = Team.get(todelete_key)
				toreassign = Team.get(toreassign_key)
				
				if todelete.leader.key() == toreassign.leader.key():
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
									  ('/results/detail', ResultDetail),
									  ('/admin', Admin),
									  ('/admin/rebuild_winloss', BuildWinLoss)],
                                     debug=True)

def get_team_groups(teams):
	team_groups = { }
	for team in teams:
		if not team.leader in team_groups:
			team_groups[team.leader] = []
		team_groups[team.leader].append(team)
		
	return [team_groups[k] for k in sorted(team_groups.keys(), lambda x,y: cmp(x.name, y.name))]

def update_stats(winner, loser):
	existing = MatchupStatistics.gql("where team1 in (:1, :2) and team2 in (:2, :1)", winner.key(), loser.key())
	if existing.count() == 0:
	    newStats = MatchupStatistics()
	    newStats.team1 = winner
	    newStats.team2 = loser
	    newStats.team1_wins = 1
	    newStats.team2_wins = 0
	    
	    newStats.team1.wins = 1
	    newStats.team1.losses = 0
	    newStats.team2.wins = 0
	    newStats.team2.losses = 1
	    
	    db.put([newStats, newStats.team1, newStats.team2])
	    return (1, 0)
	elif existing.count() == 1:
		oldStats = existing.fetch(1)[0]
		if oldStats.team1.key() == winner.key():
			oldStats.team1_wins = oldStats.team1_wins + 1
			oldStats.team1.wins = oldStats.team1.wins + 1
			oldStats.team2.losses = oldStats.team2.losses + 1
		else:
			oldStats.team2_wins = oldStats.team2_wins + 1
			oldStats.team2.wins = oldStats.team2.wins + 1
			oldStats.team1.losses = oldStats.team1.losses + 1
			
		db.put([oldStats, oldStats.team1, oldStats.team2])
		return (0, 1)
	else:
		logging.error("unexpected state: %s matchup statistics for the same team pair (expected 1)" % existing.count())
		return (0, 0)
		
def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
