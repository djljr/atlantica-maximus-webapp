var selected = { };

function toggleSelectTeam(team_key)
{
	var teamDiv = $('#' + team_key)[0];
	if(selected[team_key])
	{
		removeElementClass(teamDiv, "highlight");
		$('#select_' + team_key)[0].value = "";
		selected[team_key] = false;
	}
	else
	{
		addElementClass(teamDiv, "highlight");
		$('#select_' + team_key)[0].value = team_key;
		selected[team_key] = true;
	}
}

function postSelectedTeams(minCount, maxCount, errorCallback)
{
	var teams = getSelectedTeams()
	var teamCount = teams.length;
	if(teamCount < minCount) 
	{
		errorCallback("You must select at least " + minCount + " teams to continue (you selected " + teamCount + ")");
		return false;
	}
	else if(teamCount > maxCount)
	{
		errorCallback("You can have at most " + maxCount + " teams selected (you selected " + teamCount + ")");
		return false;
	}
	
	return true;
}

function countSelectedTeams()
{
	return getSelectedTeams().length;
}

function getSelectedTeams()
{
	returnVal = [];
	var i = 0;
	for(var key in selected)
	{
		if(selected[key])
			returnVal[i++] = key;
	}
	return returnVal;
}