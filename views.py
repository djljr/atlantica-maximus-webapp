# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from django.db import transaction
from django.db.models import Q

from maximus.models import Mercenary, Team, TeamMember, Tournament, TournamentTeam, TournamentMatchup, Matchup, MatchupStatistics, MatchResult

def index(request):
    model = Context({})
    t = loader.get_template('index.html')
    return HttpResponse(t.render(model))

def create_team(request):         
    def get():
        heroes = Mercenary.objects.filter(type='HERO')
        pawns = Mercenary.objects.filter(type='PAWN')

        model = Context({ 'heroes': heroes, 'pawns': pawns, 'mercrange': range(1,7), 'teams': get_team_groups() })
        t = loader.get_template('teams.html')
        return HttpResponse(t.render(model))
    
    def post():
        team = Team()
        class_c = request.POST['hero']
        leader = Mercenary.objects.filter(type='HERO').filter(name=class_c)
        team.leader = leader[0]
        team.wins = 0
        team.losses = 0
        team.notes = ""
        team.save()
        for i in range(1,10):
            who = request.POST['pawn%s' % i]
            if who != '':
                merc = Mercenary.objects.filter(type='PAWN').filter(name=who)
                current = TeamMember()
                current.team = team
                current.merc = merc[0]
                current.location = i
                current.save()
                
        return HttpResponseRedirect('/app/teams')
    
    if request.method == "POST":
        return post()
    else:
        return get()
        
def edit_team(request):
    def get():
        team_id = request.GET["team"]
        team = Team.objects.get(id=team_id)
        
        model = Context({ 'team': team })
        t = loader.get_template('edit_team.html')
        return HttpResponse(t.render(model))
    
    def post():
        new_notes = request.POST["notes"]
        team_id = request.POST["team"]
        
        team = Team.objects.get(id=team_id)
        team.notes = new_notes
        team.save()
        return HttpResponseRedirect('/app/teams')
        
    if request.method == "POST":
        return post()
    else:
        return get()        

def create_tournament(request):
    def get():
        inprogress = Tournament.objects.filter(completed=False);
        finished = Tournament.objects.filter(completed=True);
        model = Context({ 'teams': get_team_groups(), "in_progress": inprogress, "finished": finished })
        t = loader.get_template('tournament/create_tournament.html')
        return HttpResponse(t.render(model))
    
    @transaction.commit_on_success
    def post():
        tournament = Tournament()
        tournament.completed = False
        
        tournament.save()
        for team_id in request.POST.getlist('participant'):
            if team_id != "":
                team = Team.objects.get(id=team_id)
                tourney_team = TournamentTeam()
                tourney_team.tournament = tournament
                tourney_team.team = team
                tourney_team.save()
        
        return HttpResponseRedirect('/app/tournament/matchups?tournament=%s' % str(tournament.id))
        
    if request.method == "POST":
        return post()
    else:
        return get()        

def view_tournament(request):
    def get():
        tourney = Tournament.objects.get(id=request.GET["tournament"])
        pending_teams = []
        teams = []
        for team in tourney.tourney_team_set.all():
            if team.matchup_index == None:
                pending_teams.append(team.team)
            else:
                teams.append(team.team) 
        matches = [[i for i in range(0,4)],[i for i in range(0,2)],[0]]
        for match in tourney.tourney_match_set.all():
            matches[match.round][match.index] = match
            
        model = Context({ "pending_teams": pending_teams, "teams": teams, "matches": matches, "tourney": tourney})
        
        t = loader.get_template('tournament/view_tournament.html')
        return HttpResponse(t.render(model))
    
    @transaction.commit_on_success
    def post():
        tourney_id = request.GET["tournament"]
        tourney = Tournament.objects.get(id=tourney_id)
        versus = request.POST.getlist("versus")
        teams = []
        for team_id in versus:
            if team_id != "":
                teams.append(Team.objects.get(id=team_id))
        
        existing_matches = TournamentMatchup.objects.filter(tournament=tourney)
        
        match = Matchup()
        match.team1 = teams[0]
        match.team2 = teams[1]
        match.save()
        
        tourney_match = TournamentMatchup()
        tourney_match.tournament = tourney
        tourney_match.matchup = match
        tourney_match.round = 0
        tourney_match.index = existing_matches.count()
        tourney_match.save()
        
        tourney_teams = []
        tourney_teams.append(TournamentTeam.objects.filter(tournament=tourney).filter(team=teams[0]).get())
        tourney_teams.append(TournamentTeam.objects.filter(tournament=tourney).filter(team=teams[1]).get())
        
        tourney_teams[0].matchup_index = tourney_match.index * 2
        tourney_teams[1].matchup_index = tourney_match.index * 2 + 1
        
        tourney_teams[0].save();
        tourney_teams[1].save();
        
        return HttpResponseRedirect("/app/tournament/matchups?tournament=%s" % tourney_id)
    
    if request.method == "POST":
        return post()
    else:
        return get()

def result_tournament(request):
    @transaction.commit_on_success
    def post():
        tournament_match_id = request.GET['tournament_match_key']
        match = TournamentMatchup.objects.get(id=tournament_match_id)

        winner_id = int(request.POST['winner'])
        matchup = match.matchup
        result = MatchResult()
        if winner_id == matchup.team1.id:
            result.winner = matchup.team1
            result.loser = matchup.team2
        elif winner_id == matchup.team2.id:
            result.winner = matchup.team2
            result.loser = matchup.team1
        else:
            raise Exception("could not determine winner key: %s (%s, %s)" % (winner_id, matchup.team1.id, matchup.team2.id))
            
        update_stats(result.winner, result.loser)
        result.save()
        
        next_round_indices = {0:0, 1:0, 2:1, 3:1}
        next_round_index = next_round_indices[match.index]
        next_round = match.round + 1
        if match.round < 2:
            # look in existing matches for this winner's opponent
            existing = TournamentMatchup.objects.filter(tournament=match.tournament).filter(round=next_round).filter(index=next_round_index)
            if existing.count() == 1:
                next_match = existing[0]
                next_matchup = next_match.matchup
                next_matchup.team2 = result.winner
                next_matchup.save()
            elif existing.count() == 0:
                next_match = TournamentMatchup()
                next_matchup = Matchup()
                next_matchup.team1 = result.winner
                next_matchup.save()
                
                next_match.tournament = match.tournament
                next_match.round = next_round
                next_match.index = next_round_index
                next_match.matchup = next_matchup
                next_match.save()
        else:
            tourney = match.tournament
            tourney.completed = True
            tourney.winner = result.winner
            tourney.save()
            
        match.matchup.delete()
        match.matchup = None
        match.result = result
        match.save()
    
        return HttpResponseRedirect("/app/tournament/matchups?tournament=%s" % match.tournament.id)
       
    if request.method == "POST":
        return post()
    else:
        return HttpResponseRedirect("/app/tournament/matchups?tournament=%s" % request.GET["tournament"])   

def result_detail(request):
    result_id = request.GET['match']
    match = MatchResult.objects.get(id=result_id)

    model = Context({ 'match': match })
        
    t = loader.get_template('result_detail.html')
    return HttpResponse(t.render(model))
            
def get_team_groups():
    teams = Team.objects.all()
    team_groups = { }
    for team in teams:
        if not team.leader in team_groups:
            team_groups[team.leader] = []
        team_groups[team.leader].append(team)
        
    team_groups = [sorted(team_groups[k], lambda x,y: cmp(x.id, y.id)) for k in sorted(team_groups.keys(), lambda x,y: cmp(x.name, y.name))]
    return team_groups

def update_stats(winner, loser):
    existing = MatchupStatistics.objects.filter(Q(team1__in=[winner.id, loser.id]) & Q(team2__in=[winner.id, loser.id]))
    stats = None
    if existing.count() == 0:
        newStats = MatchupStatistics()
        newStats.team1 = winner
        newStats.team2 = loser
        newStats.team1_wins = 1
        newStats.team2_wins = 0
        
        winner.wins = winner.wins + 1
        loser.losses = loser.losses + 1
        
        newStats.save()
        winner.save()
        loser.save()
        return (1, 0)
    elif existing.count() == 1:
        oldStats = existing.fetch(1)[0]
        if oldStats.team1.id == winner.id:
            oldStats.team1_wins = oldStats.team1_wins + 1
        else:
            oldStats.team2_wins = oldStats.team2_wins + 1
            
        winner.wins = winner.wins + 1
        loser.losses = loser.losses + 1
        oldStats.save()
        winner.save()
        loser.save()
        
        return (0, 1)
    else:
        logging.error("unexpected state: %s matchup statistics for the same team pair (expected 1)" % existing.count())
        return (0, 0)
