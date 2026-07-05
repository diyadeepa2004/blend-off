"""
Award assignment for Blend-Wars.

Takes {display_name: [track_record, ...]} (the shape fetch_blend()
returns per person) and works out who wins each award, with the actual
numbers behind each call so nobody can argue it's just vibes.

Awards:
- Most Mainstream   -> highest average track popularity
- Most Underground  -> lowest average track popularity
- Most Chaotic       -> most unique genres across the whole Blend
- Widest Time Machine -> biggest gap between oldest and newest track
- Copycat Award      -> the two people whose Blends overlap the most
"""
from statistics import mean


def _avg_popularity(tracks: list[dict]) -> float:
    return mean(t.get("popularity", 0) for t in tracks) if tracks else 0.0


def _unique_genres(tracks: list[dict]) -> set[str]:
    genres: set[str] = set()
    for t in tracks:
        genres.update(t.get("genres", []))
    return genres


def _year_span(tracks: list[dict]) -> tuple[int, int, int]:
    years = [
        int(t["release_year"])
        for t in tracks
        if t.get("release_year", "0000").isdigit() and t["release_year"] != "0000"
    ]
    if not years:
        return (0, 0, 0)
    return (min(years), max(years), max(years) - min(years))


def _track_id_set(tracks: list[dict]) -> set[str]:
    return {t["track_id"] for t in tracks}


def assign_awards(blend_tracks: dict[str, list[dict]]) -> dict:
    names = list(blend_tracks.keys())
    if len(names) < 2:
        raise ValueError("Need at least 2 Blends to compare")

    stats = {}
    for name, tracks in blend_tracks.items():
        oldest, newest, spread = _year_span(tracks)
        stats[name] = {
            "track_count": len(tracks),
            "avg_popularity": round(_avg_popularity(tracks), 1),
            "genre_count": len(_unique_genres(tracks)),
            "oldest_year": oldest,
            "newest_year": newest,
            "year_spread": spread,
        }

    most_mainstream = max(stats, key=lambda n: stats[n]["avg_popularity"])
    most_underground = min(stats, key=lambda n: stats[n]["avg_popularity"])
    most_chaotic = max(stats, key=lambda n: stats[n]["genre_count"])
    widest_time_machine = max(stats, key=lambda n: stats[n]["year_spread"])

    # Copycat Award: the pair with the highest track-overlap (Jaccard similarity)
    copycat = None
    best_overlap = -1.0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            set_a, set_b = _track_id_set(blend_tracks[a]), _track_id_set(blend_tracks[b])
            if not set_a or not set_b:
                continue
            union = set_a | set_b
            overlap = len(set_a & set_b) / len(union) if union else 0.0
            if overlap > best_overlap:
                best_overlap = overlap
                copycat = (a, b, len(set_a & set_b))

    awards = {
        "Most Mainstream": {
            "winner": most_mainstream,
            "avg_popularity": stats[most_mainstream]["avg_popularity"],
        },
        "Most Underground": {
            "winner": most_underground,
            "avg_popularity": stats[most_underground]["avg_popularity"],
        },
        "Most Chaotic": {
            "winner": most_chaotic,
            "genre_count": stats[most_chaotic]["genre_count"],
        },
        "Widest Time Machine": {
            "winner": widest_time_machine,
            "oldest_year": stats[widest_time_machine]["oldest_year"],
            "newest_year": stats[widest_time_machine]["newest_year"],
            "year_spread": stats[widest_time_machine]["year_spread"],
        },
    }

    if copycat:
        a, b, shared_count = copycat
        awards["Copycat Award"] = {
            "winners": [a, b],
            "shared_tracks": shared_count,
            "overlap_pct": round(best_overlap * 100, 1),
        }

    return {"stats": stats, "awards": awards}