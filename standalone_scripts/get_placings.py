# 1. Install dependencies
# You can use the requirements.txt or just `pip install requests` as it's
# our only dependency
import json
import csv

import requests

# 2. Fill these in

api_key = "API_KEY_HERE"
# example: 1234567890abcdef1234567890abcdef

csv_output_path = "/path/to/file/here"
# example: /user/kevin/smashgg-data/salt8_placings.csv
# example: C:/Users/kevin/smashgg_data/salt8_placings.csv

event_slug = "event-slug"
# example: "tournament/brussels-challenge-major-edition-2019/event/super-smash-bros-ultimate-solo"
# This corresponds mostly to the trailing part of the url for the event.
# For this example, the url of the page was:
# https://smash.gg/tournament/brussels-challenge-major-edition-2019/events/super-smash-bros-ultimate-solo/overview
#                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# 3. Run the script

# 4. Open / Import the CSV in your spreadsheet software of choice.

# --------------------------------------------------------
csv_output_path = os.path.normpath(csv_output_path)
event_slug = event_slug.replace("/events/", "/event/")

api_url = "https://api.smash.gg/gql/alpha"

auth_headers = {
    "Authorization": "Bearer {}".format(api_key)
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


# region Query strings
GET_EVENT_ID = """
query EventIDQuery($event_slug: String) {
  event(slug: $event_slug) {
    id
  }
}
""".strip()

GET_STANDINGS = """
query EventsQuery($event_id: ID) {
  event(id: $event_id) {
    standings(query: {
        perPage: 256
    }){
      pageInfo {
        totalPages
      }
      nodes {
        entrant {
          name
        },
        placement
      }
    }
  }
}
""".strip()

GET_SETS_PAGE_METADATA = """
query EventsQuery($event_id: ID, $page_size: Int) {
  event(id: $event_id) {
    sets (perPage: $page_size) {
      pageInfo {
        total,
        totalPages
      }
    }
  }
}
""".strip()

GET_SETS_BY_PAGE = """
query EventsQuery($event_id: ID, $page_size: Int, $page_nr: Int) {
  event(id: $event_id) {
    sets (page: $page_nr, perPage: $page_size) {
      nodes{
        displayScore,
        fullRoundText,
        slots {
          standing {
            entrant {
              name
            },
            stats {
              score {
                label,
                value
              }
            }
          }
        }
      }
    }
  }
}
""".strip()


# endregion

def get_event_id(event_slug):
    event_id_req = requests.post(url=api_url,
                                 headers=auth_headers,
                                 json={
                                     "query": GET_EVENT_ID,
                                     "variables": dict(event_slug=event_slug)
                                 })
    resp = json.loads(event_id_req.content)
    return resp["data"]["event"]["id"]


def get_standings(event_id):
    """

    :param event_id:
    :return:
    :rtype: dict[str, PlayerResult]
    """
    standings_request = requests.post(url=api_url,
                                      headers=auth_headers,
                                      json={
                                          "query": GET_STANDINGS,
                                          "variables": dict(event_id=event_id)
                                      })
    resp = json.loads(standings_request.content)
    placements = resp["data"]["event"]["standings"]["nodes"]
    num_of_pages = resp["data"]["event"]["standings"]["pageInfo"]["totalPages"]
    if num_of_pages > 1:
        print("MISSING SOME PLACEMENT DATA! (More than 256 players in event)")
    player_results = {
        p["entrant"]["name"]: PlayerResult(name=p["entrant"]["name"],
                                           placement=p["placement"])
        for p in placements
    }
    return player_results


def get_and_count_sets(event_id, player_results):
    """

    :param event_id:
    :param player_results:
    :type player_results: dict[str, PlayerResult]
    :return:
    """
    qry_vars = {
        "event_id": event_id,
        "page_size": 32
    }
    # Retrieve all sets -- Get page metadata
    set_meta_request = requests.post(url=api_url,
                                     headers=auth_headers,
                                     json={
                                         "query": GET_SETS_PAGE_METADATA,
                                         "variables": qry_vars
                                     })
    set_meta_resp = json.loads(set_meta_request.content)
    page_count = set_meta_resp["data"]["event"]["sets"]["pageInfo"][
        "totalPages"]

    # Retrieve set pages
    for page_nr in range(1, page_count + 1):
        set_request = requests.post(url=api_url,
                                    headers=auth_headers,
                                    json={
                                        "query": GET_SETS_BY_PAGE,
                                        "variables": dict(qry_vars,
                                                          page_nr=page_nr)
                                    })
        set_resp = json.loads(set_request.content)
        sets = set_resp["data"]["event"]["sets"]["nodes"]
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

    sorted_player_results = sorted(player_results.values(),
                                   key=lambda pr: (pr.placement, pr.name,))
    sorted_result_dicts = (pr.as_dict()
                           for pr in sorted_player_results)
    return sorted_result_dicts


def write_results_to_csv(csv_file_path, result_dicts):
    with open(csv_file_path, 'w', newline="", encoding="utf-8") as csv_file:
        field_names = ["placement", "name", "wins", "losses"]
        csv_writer = csv.DictWriter(csv_file, fieldnames=field_names)
        csv_writer.writeheader()
        csv_writer.writerows(result_dicts)


if __name__ == '__main__':
    event_id = get_event_id(event_slug)
    print("Event ID: {}".format(event_id))
    print("Retrieving standings...")
    player_results = get_standings(event_id)
    print("Retrieving & parsing sets...")
    sorted_result_dicts = get_and_count_sets(event_id, player_results)
    print("Writing to file: {}".format(csv_output_path))
    write_results_to_csv(csv_output_path, sorted_result_dicts)
