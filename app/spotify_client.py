"""
Spotify access for Blend Wars.

IMPORTANT: Blends are Spotify's own algorithmic playlists (ID prefix
37i9dQZF1E...), not regular user-created playlists. As of Spotify's
February 2026 API changes, playlist *contents* (tracks) are only
returned to the authenticated user who owns/participates in that
specific playlist — Client Credentials (app-only) access, and even a
different logged-in user's token, both return 403 Forbidden for a
Blend they're not part of.

This is why Blend Tea can't have one person paste everybody's Blend
link. Each person has to log in as themselves and add their own Blend
— see the room-based flow in main.py.
"""
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

SCOPES = "playlist-read-private playlist-read-collaborative"


def get_user_oauth() -> SpotifyOAuth:
    """Authorization Code flow — the logged-in user's own token, required to read Blends."""
    return SpotifyOAuth(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIPY_REDIRECT_URI"],
        scope=SCOPES,
        cache_path=None,
    )


def get_app_only_client() -> spotipy.Spotify:
    """
    Client Credentials flow — kept for any future feature that only needs
    regular public playlists/artists/genres, but NOT sufficient for Blends.
    """
    auth_manager = SpotifyClientCredentials(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_display_name(sp: spotipy.Spotify) -> str:
    """The name we'll show for this person in the room (falls back to their Spotify user id)."""
    profile = sp.current_user()
    return profile.get("display_name") or profile.get("id", "unknown")


def extract_playlist_id(playlist_url_or_uri: str) -> str:
    if "spotify:playlist:" in playlist_url_or_uri:
        return playlist_url_or_uri.split("spotify:playlist:")[-1]
    if "open.spotify.com/playlist/" in playlist_url_or_uri:
        return playlist_url_or_uri.split("open.spotify.com/playlist/")[-1].split("?")[0]
    return playlist_url_or_uri.strip()


def _batch_artist_genres(sp: spotipy.Spotify, artist_ids: list[str]) -> dict[str, list[str]]:
    genres_by_artist: dict[str, list[str]] = {}
    unique_ids = list(dict.fromkeys(artist_ids))
    for i in range(0, len(unique_ids), 50):
        chunk = unique_ids[i : i + 50]
        result = sp.artists(chunk)
        for artist in result["artists"]:
            if artist:
                genres_by_artist[artist["id"]] = artist.get("genres", [])
    return genres_by_artist


def fetch_blend(sp: spotipy.Spotify, playlist_url_or_uri: str) -> list[dict]:
    """Pulls and normalizes every track from a Blend (or any playlist) the caller's token can read."""
    playlist_id = extract_playlist_id(playlist_url_or_uri)
    all_items = []
    results = sp.playlist_items(playlist_id, additional_types=["track"])
    all_items.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        all_items.extend(results["items"])

    primary_artist_ids = [
        item["track"]["artists"][0]["id"]
        for item in all_items
        if item.get("track") and item["track"].get("artists")
    ]
    genre_map = _batch_artist_genres(sp, primary_artist_ids)

    records = []
    for item in all_items:
        track = item.get("track")
        if not track or not track.get("id"):
            continue
        artist = track["artists"][0]
        records.append(
            {
                "track_id": track["id"],
                "track_name": track["name"],
                "artist_id": artist["id"],
                "artist_name": artist["name"],
                "genres": genre_map.get(artist["id"], []),
                "popularity": track.get("popularity", 0),
                "release_year": (track.get("album", {}).get("release_date", "0000"))[:4],
            }
        )
    return records