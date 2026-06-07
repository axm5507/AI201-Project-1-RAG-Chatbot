"""Source definitions for the Unofficial Guide corpus (Bryan/College Station).

Each source mirrors a row in planning.md. ``kind`` tells the chunker how to
split the document:
  - "listing": event calendars / attraction lists (small chunks, no overlap)

Note: the Reddit threads (#1, #2, #7) and TripAdvisor (#5) from planning.md are
omitted — all four sit behind anti-bot protection and return HTTP 403 to plain
HTTP scraping. To include them later, drop saved copies into documents/ (the
pipeline chunks anything there) or wire up the Reddit OAuth API.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: int
    name: str
    description: str
    url: str
    kind: str  # "discussion" | "listing"


SOURCES = [
    Source(3, "Destination Bryan", "Official Bryan things-to-do",
           "https://destinationbryan.com/things-to-do/", "listing"),
    Source(4, "Visit College Station", "Official CS things-to-do",
           "https://visit.cstx.gov/things-to-do/", "listing"),
    Source(6, "Texas A&M University", "Official university events calendar",
           "https://getinvolved.tamu.edu/events", "listing"),
    Source(8, "Visit College Station", "Official CS nightlife options",
           "https://visit.cstx.gov/things-to-do/nightlife/", "listing"),
    Source(9, "Visit College Station", "Official CS events calendar",
           "https://visit.cstx.gov/events/", "listing"),
    Source(10, "Destination Bryan", "Official Bryan events calendar",
           "https://www.destinationbryan.com/events/", "listing"),
]
