from django.db import models

# Create your models here.
class Mercenary(models.Model):
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=(('HERO', 'Hero'), ('PAWN', 'Pawn')))
    
    def __unicode__(self):
        if self.type == "HERO":
            return "(H) %s" % self.name
        else:
            return self.name
        
class Team(models.Model):
    leader = models.ForeignKey(Mercenary)
    wins = models.IntegerField()
    losses = models.IntegerField()
    notes = models.TextField()
    
    def __unicode__(self):
        return "Team %s" % self.leader 

class TeamMember(models.Model):
    team = models.ForeignKey(Team)
    merc = models.ForeignKey(Mercenary)
    location = models.IntegerField()

class Matchup(models.Model):
    team1 = models.ForeignKey(Team, related_name="team1_set")
    team2 = models.ForeignKey(Team, related_name="team2_set")

class MatchResult(models.Model):
    winner = models.ForeignKey(Team, related_name="winner_set")
    loser = models.ForeignKey(Team, related_name="loser_set")

class MatchupStatistics(models.Model):
    team1 = models.ForeignKey(Team, related_name="team1_stats_set")
    team2 = models.ForeignKey(Team, related_name="team2_stats_set")
    team1_wins = models.IntegerField()
    team2_wins = models.IntegerField()

class Tournament(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField()
    winner = models.ForeignKey(Team, related_name="tourney_winner_set", blank=True, null=True)

class TournamentTeam(models.Model):
    tournament = models.ForeignKey(Tournament, related_name="tourney_team_set")
    team = models.ForeignKey(Team, related_name="participant_set")
    matchup_index = models.IntegerField(blank=True, null=True)

class TournamentMatchup(models.Model):
    tournament = models.ForeignKey(Tournament, related_name="tourney_match_set")
    matchup = models.ForeignKey(Matchup)
    round = models.IntegerField()
    index = models.IntegerField()
