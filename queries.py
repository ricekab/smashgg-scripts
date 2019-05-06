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