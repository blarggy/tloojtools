from leeger.league_loader import SleeperLeagueLoader
from leeger.model.league import League, Year
from leeger.util.excel import leagueToExcel

if __name__ == "__main__":
    sleeperLeagueLoader = SleeperLeagueLoader("1075600889420845056", [2023])
    league: League = sleeperLeagueLoader.loadLeague()

    # Get a dummy Year object
    year: Year = league.years[0]

    # Overwrite an existing file by using the 'overwrite' keyword argument
    leagueToExcel(league, "myLeagueStats.xlsx", overwrite=True)
