# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader

from test_site.maximus.models import Mercenary, Team, TeamMember

def index(request):
    return HttpResponse("Hello, world. You're at the index.")

def create_team(request):         
    def get():
        heroes = Mercenary.objects.filter(type='HERO')
        pawns = Mercenary.objects.filter(type='PAWN')

        model = Context({ 'heroes': heroes, 'pawns': pawns, 'mercrange': range(1,7), 'teams': get_team_groups() })
        print model
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
        
        
def get_team_groups():
    teams = Team.objects.all()
    team_groups = { }
    for team in teams:
        if not team.leader in team_groups:
            team_groups[team.leader] = []
        team_groups[team.leader].append(team)
    
    team_groups = [team_groups[k] for k in sorted(team_groups.keys(), lambda x,y: cmp(x.name, y.name))]
    print team_groups
    return team_groups   