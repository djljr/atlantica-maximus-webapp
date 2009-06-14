selected = { }

function toggleSelectTeam(team_key)
{
	var teamDiv = $('#' + team_key)
	if(selected[team_key])
	{
		teamDiv.css("border","0px");
		selected[team_key] = false;
	}
	else
	{
		teamDiv.css("border", "3px solid yellow");
		selected[team_key] = true;
	}
}

function getSelectedTeams()
{
	return selected;
}