# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from django.db import transaction

from test_site.maximus.models import Mercenary, Team, TeamMember, Tournament, TournamentTeam, TournamentMatchup, Matchup

def index(request):
    return HttpResponse("Hello, world. You're at the index.")

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
                
        return HttpResponseRedirect('/teams')
    
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
        return HttpResponseRedirect('/teams')
        
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
        print request.POST.getlist('participant')
        for team_id in request.POST.getlist('participant'):
            print "team " + team_id
            if team_id != "":
                print team_id
                team = Team.objects.get(id=team_id)
                tourney_team = TournamentTeam()
                tourney_team.tournament = tournament
                tourney_team.team = team
                tourney_team.save()
        
        return HttpResponseRedirect('/tournament/matchups?tournament=%s' % str(tournament.id))
        
    if request.method == "POST":
        return post()
    else:
        return get()        

def view_tournament(request):
    def get():
        tourney = Tournament.objects.get(id=request.GET["tournament"])
        teams = []
        for team in tourney.tourney_team_set.all():
            if team.matchup_index == None:
                teams.append(team.team) 
        matches = [[i for i in range(0,4)],[i for i in range(0,2)],[0]]
        for match in tourney.tourney_match_set.all():
            matches[match.round][match.index] = match
            
        model = Context({ "teams": teams, "matches": matches, "tourney": tourney})
        
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
        
        return HttpResponseRedirect("/tournament/matchups?tournament=%s" % tourney_id)
    
    if request.method == "POST":
        return post()
    else:
        return get()  
def get_team_groups():
    teams = Team.objects.all()
    team_groups = { }
    for team in teams:
        if not team.leader in team_groups:
            team_groups[team.leader] = []
        team_groups[team.leader].append(team)
        
    team_groups = [sorted(team_groups[k], lambda x,y: cmp(x.id, y.id)) for k in sorted(team_groups.keys(), lambda x,y: cmp(x.name, y.name))]
    return team_groups   