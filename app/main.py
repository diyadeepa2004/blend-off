"""
Blend-Wars — each friend authenticates with their own Spotify account.

Why: Spotify only returns a Blend's tracks to someone who's actually a
participant in that Blend (see spotify_client.py). So instead of one
person pasting everyone's links, one person starts a "room", shares the
room link, and each friend joins, logs in as themselves, and adds their
own Blend.

Run locally with:
    uvicorn app.main:app --reload
"""
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Query, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse
import spotipy

from app.spotify_client import get_user_oauth, fetch_blend, get_display_name
from app.analysis import assign_awards
from app import rooms

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Blend Tea")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-only-change-me"),
)


@app.get("/", response_class=HTMLResponse)
def home():
    return (
        "<h2>Blend Tea ☕</h2>"
        "<p>Your Blend with your bestie and your Blend with your situationship, "
        "put on trial. Start a room, invite friends, everyone adds their own Blend.</p>"
        "<form action='/room/new' method='post'>"
        "<button type='submit'>Start spilling ☕</button>"
        "</form>"
    )


@app.post("/room/new")
def new_room():
    room_id = rooms.create_room()
    return RedirectResponse(f"/room/{room_id}", status_code=303)


@app.get("/room/{room_id}", response_class=HTMLResponse)
def room_page(room_id: str):
    if not rooms.room_exists(room_id):
        raise HTTPException(404, "No such room — check the link")

    names = rooms.member_names(room_id)
    joined_html = "".join(f"<li>{n}</li>" for n in names) or "<li><em>no one yet</em></li>"

    if len(names) >= 2:
        cta = f"<p><a href='/room/{room_id}/results'>🏆 See the awards</a></p>"
    else:
        cta = f"<p>Need at least 2 people before the awards show can run ({len(names)}/2 so far).</p>"

    return (
        f"<h2>Blend Tea room</h2>"
        f"<p>Share this page's URL with friends so they can add their Blend:</p>"
        f"<p><code>/room/{room_id}</code></p>"
        f"<h3>Joined so far</h3><ul>{joined_html}</ul>"
        f"<p><a href='/room/{room_id}/login'>➕ Add your Blend</a></p>"
        f"{cta}"
    )


@app.get("/room/{room_id}/login")
def room_login(request: Request, room_id: str):
    if not rooms.room_exists(room_id):
        raise HTTPException(404, "No such room")
    # Remember which room this login is for, so /callback knows where to send them back.
    request.session["pending_room"] = room_id
    auth_manager = get_user_oauth()
    return RedirectResponse(auth_manager.get_authorize_url())


@app.get("/callback")
def callback(request: Request, code: str = Query(...)):
    room_id = request.session.get("pending_room")
    if not room_id:
        raise HTTPException(
            400,
            "No room was in progress — start from a room's 'Add your Blend' link, not directly.",
        )

    auth_manager = get_user_oauth()
    token_info = auth_manager.get_access_token(code, as_dict=True)
    # Stash the token just long enough to grab their Blend link on the next screen.
    request.session["access_token"] = token_info["access_token"]

    return RedirectResponse(f"/room/{room_id}/paste-blend")


@app.get("/room/{room_id}/paste-blend", response_class=HTMLResponse)
def paste_blend_form(request: Request, room_id: str):
    if not rooms.room_exists(room_id):
        raise HTTPException(404, "No such room")
    if not request.session.get("access_token"):
        return RedirectResponse(f"/room/{room_id}/login")

    return (
        "<h2>One more step</h2>"
        "<p>Paste the link to <strong>your own</strong> Blend "
        "(the one you're logged in as — this only works for Blends you're actually part of):</p>"
        f"<form action='/room/{room_id}/paste-blend' method='post'>"
        "<input name='blend_url' style='width:420px' "
        "placeholder='https://open.spotify.com/playlist/...'>"
        "<button type='submit'>Add me to the room</button>"
        "</form>"
    )


@app.post("/room/{room_id}/paste-blend")
def paste_blend_submit(request: Request, room_id: str, blend_url: str = Form(...)):
    if not rooms.room_exists(room_id):
        raise HTTPException(404, "No such room")

    access_token = request.session.get("access_token")
    if not access_token:
        raise HTTPException(401, "Your session expired — log in again")

    sp = spotipy.Spotify(auth=access_token)
    display_name = get_display_name(sp)
    tracks = fetch_blend(sp, blend_url.strip())
    rooms.add_member(room_id, display_name, tracks)

    # Token's done its job — don't hang on to it longer than necessary.
    request.session.pop("access_token", None)
    request.session.pop("pending_room", None)

    return RedirectResponse(f"/room/{room_id}", status_code=303)


@app.get("/room/{room_id}/results")
def results(room_id: str):
    if not rooms.room_exists(room_id):
        raise HTTPException(404, "No such room")
    room = rooms.get_room(room_id)
    if len(room["members"]) < 2:
        raise HTTPException(400, "Need at least 2 people to compare")
    return assign_awards(room["members"])