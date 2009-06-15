#!/usr/bin/env python2.5
import os
import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from .models import MatchResult, MatchupStatistics, Mercenary, Team
from .maximus_utils import update_stats, get_team_groups

class Admin(webapp.RequestHandler):
	def get(self):
		model = { }
		path=os.path.join(os.path.dirname(__file__), '../templates/admin.html')
		self.response.out.write(template.render(path, model))
		
class BuildWinLoss(webapp.RequestHandler):
	def post(self):
		logging.info("Rebuilding win-loss records")
		batch_size = 10
		batch = MatchResult.gql("order by __key__")
		
		query = "where __key__ > :1 order by __key__"
		
		matchups = []
		teams = []
		for matchup_stats in MatchupStatistics.all():
			matchups.append(matchup_stats)
		for team in Team.all():
			team.wins = 0
			team.losses = 0
			teams.append(team)
			
		db.delete(matchups)
		db.put(teams)
		
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
		
		memcache.delete("team_groups")
		self.redirect("/admin?match_count=%s&created=%s&updated=%s" % (total_count, total_create, total_update))
		
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
		heroes = Mercenary.gql("where type = 'Hero'")
		pawns = Mercenary.gql("where type = 'Pawn'")

		model = { 'heroes': heroes, 'pawns': pawns, 'mercrange': range(1,7), 'teams': get_team_groups() }
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
				
		memcache.delete("team_groups")
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

class MemCacheStats(webapp.RequestHandler):
	def get(self):
		stats = memcache.get_stats()
		self.response.out.write("<html><body>")
		self.response.out.write("<b>Cache Hits:%s</b><br />" % stats['hits'])
		self.response.out.write("<b>Cache Misses:%s</b><br />" % stats['misses'])
		self.response.out.write("</body></html>")		