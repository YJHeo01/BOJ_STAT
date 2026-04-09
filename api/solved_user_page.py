import requests, logging

from models.user_stats import SolvedUserData

logger = logging.getLogger(__name__)

def solved_user_data(username):
    url = "https://solved.ac/api/v3/user/show"
    
    querystring = {"handle":username}
    headers = {
        "x-solvedac-language": "",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers,params=querystring)
    
    if response.status_code == 200:
        information = response.json()
        class_value = information['class'] * 3
        if information['classDecoration'] == "silver":
            class_value += 1
        if information['classDecoration'] == "gold":
            class_value += 2
        return SolvedUserData(
            solvedCount=information['solvedCount'],
            voteCount=information['voteCount'],
            tier=information['tier'],
            classValue=class_value
        )
    else:
        if response.status_code != 404:
            return SolvedUserData.failure()
    return SolvedUserData()
