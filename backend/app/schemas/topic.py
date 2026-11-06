from datetime import date

from pydantic import BaseModel


class TopicRead(BaseModel):
    """Bir sapak gününiň temasy (sapak: assignment_id + day + time_slot_id)."""
    id: int
    assignment_id: int
    day: date
    time_slot_id: int
    topic: str
    note: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_url: str | None = None  # serweriň salgysyna goşulýar
    preview: str | None = None  # app-yň içinde: "pdf", "image"; None — diňe ýüklemek
    preview_url: str | None = None
