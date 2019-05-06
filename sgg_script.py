# Ow dus basically ik wil automatisch dingen van de smash.gg api halen en gwn in een
# klein bestandje zetten met kolommen die respectievelijk placing speler losses n wins geven
import csv
import json
import os
from pprint import pprint as pp

import requests
from graphqlclient import GraphQLClient as GQLClient

import queries

api_name = "DevTestToken"
api_key = "APIKEYHERE"

api_url = "https://api.smash.gg/gql/alpha"

auth_headers = {
    "Authorization": "Bearer {}".format(api_key)
}

smashgg = GQLClient(endpoint=api_url)
smashgg.inject_token(api_key)

qry_vars = {
    "event_id": 305304,
    "page_size": 32
}


class PlayerResult(object):
    def __init__(self, name, placement, wins=0, losses=0):
        self.name = name
        self.placement = placement
        self.wins = wins
        self.losses = losses

    def as_dict(self):
        return dict(name=self.name,
                    placement=self.placement,
                    wins=self.wins,
                    losses=self.losses)

    def __repr__(self):
        return "<{} #{} (W: {}, L: {})>".format(self.name,
                                                self.placement,
                                                self.wins,
                                                self.losses)


standings_request = requests.post(url=api_url,
                                  headers=auth_headers,
                                  json={
                                      "query": queries.GET_STANDINGS,
                                      "variables": qry_vars
                                  })
res_json = json.loads(standings_request.content)

# Retrieve final placements for an event
placements = res_json["data"]["event"]["standings"]["nodes"]
num_of_pages = res_json["data"]["event"]["standings"]["pageInfo"]["totalPages"]
if num_of_pages > 1:
    print("MISSING SOME PLACEMENT DATA! (More than 256 players in event)")
player_results = {
    p["entrant"]["name"]: PlayerResult(name=p["entrant"]["name"],
                                       placement=p["placement"])
    for p in placements
}

# Retrieve all sets -- Get page metadata
set_meta_request = requests.post(url=api_url,
                                 headers=auth_headers,
                                 json={
                                     "query": queries.GET_SETS_PAGE_METADATA,
                                     "variables": qry_vars
                                 })
set_meta_json = json.loads(set_meta_request.content)
set_page_count = set_meta_json["data"]["event"]["sets"]["pageInfo"][
    "totalPages"]

# Retrieve set pages
for page_nr in range(1, set_page_count + 1):
    set_request = requests.post(url=api_url,
                                headers=auth_headers,
                                json={
                                    "query": queries.GET_SETS_BY_PAGE,
                                    "variables": dict(qry_vars,
                                                      page_nr=page_nr)
                                })
    set_json = json.loads(set_request.content)
    sets = set_json["data"]["event"]["sets"]["nodes"]
    for set_ in sets:
        standings = (slot["standing"] for slot in set_["slots"])
        scores = [(s["entrant"]["name"], s["stats"]["score"]["value"],)
                  for s in standings]
        # Sort by score to have winner in index 0 and loser in index 1
        scores = sorted(scores,
                        key=lambda s: s[1],
                        reverse=True)
        winner, loser = (score[0] for score in scores)
        player_results[winner].wins += 1
        player_results[loser].losses += 1

sorted_result_dicts = (pr.as_dict()
                       for pr in sorted(player_results.values(),
                                        key=lambda pr: (pr.placement, pr.name,))
                       )

WORK_DIR = os.getcwd()
csv_file_path = os.path.join(WORK_DIR, "placements.csv")
with open(csv_file_path, 'w', newline="") as csv_file:
    field_names = ["placement", "name", "wins", "losses"]
    csv_writer = csv.DictWriter(csv_file, fieldnames=field_names)
    csv_writer.writeheader()
    csv_writer.writerows(sorted_result_dicts)
