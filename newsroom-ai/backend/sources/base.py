from typing import TypedDict
from datetime import datetime


SOURCE_TYPE_OFFICIAL = "official"
SOURCE_TYPE_POLITICAL_STATEMENT = "political_statement"
SOURCE_TYPE_MEDIA = "media"


ALLOWED_SOURCE_TYPES = {
    SOURCE_TYPE_OFFICIAL,
    SOURCE_TYPE_POLITICAL_STATEMENT,
    SOURCE_TYPE_MEDIA,
}


class SourceStory(TypedDict):
    external_id: str
    title: str
    summary: str | None
    url: str | None

    source: str
    source_type: str

    source_entity_id: str | None
    source_event_type: str | None

    published_at: datetime | None