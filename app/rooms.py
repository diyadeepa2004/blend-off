"""
In-memory room store for Blend-Wars's "everyone logs in as themselves" flow.

A room is just: a short id, plus a dict of {display_name: track_list} for
whoever has joined and added their own Blend so far.

NOTE: this is a process-local dict — fine for local dev or a single Render
instance, but it resets on every restart/reload and won't work if you ever
scale to multiple server instances. If you outgrow it, `redis` is already
in your dependency tree (via spotipy) and is the natural next step.
"""
import secrets
from datetime import datetime, timezone

# room_id -> {"created_at": datetime, "members": {display_name: [track_record, ...]}}
_ROOMS: dict[str, dict] = {}


def create_room() -> str:
    room_id = secrets.token_urlsafe(6)
    _ROOMS[room_id] = {"created_at": datetime.now(timezone.utc), "members": {}}
    return room_id


def room_exists(room_id: str) -> bool:
    return room_id in _ROOMS


def get_room(room_id: str) -> dict:
    if not room_exists(room_id):
        raise KeyError(f"No such room: {room_id}")
    return _ROOMS[room_id]


def add_member(room_id: str, display_name: str, tracks: list[dict]) -> None:
    get_room(room_id)["members"][display_name] = tracks


def member_names(room_id: str) -> list[str]:
    return list(get_room(room_id)["members"].keys())