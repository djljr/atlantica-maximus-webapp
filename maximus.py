#!/usr/bin/env python2.5

import cgi
import os

from erenda.tournament import TournamentMatchups, CreateTournament
from erenda.matches import ResultDetail, ResultHistory, MatchupDelete, MatchupResult, CreateMatchup
from erenda.admin import Admin, DeleteTeam, BuildWinLoss, CreateTeam, CreateMerc, MemCacheStats

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
	
class Index(webapp.RequestHandler):
	def get(self):
		path=os.path.join(os.path.dirname(__file__), 'templates/index.html')
		self.response.out.write(template.render(path, {}))

application = webapp.WSGIApplication(
                                     [('/', Index),
									  ('/mercs', CreateMerc),
									  ('/teams', CreateTeam),
									  ('/teams/delete', DeleteTeam),
									  ('/tournament', CreateTournament),
									  ('/tournament/matchups', TournamentMatchups),
									  ('/matchup', CreateMatchup),
									  ('/matchup/delete', MatchupDelete),
									  ('/matchup/result', MatchupResult),
									  ('/results', ResultHistory),
									  ('/results/detail', ResultDetail),
									  ('/admin', Admin),
									  ('/admin/rebuild_winloss', BuildWinLoss),
									  ('/admin/memcache', MemCacheStats)],
                                     debug=True)
			
def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
