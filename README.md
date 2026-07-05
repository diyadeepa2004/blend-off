# Blend-Wars

Your Blend with your best friend and your Blend with your situationship are
about to be put on trial. Paste in two or more of your Spotify Blends and
Blend-Off puts them head-to-head in an actual awards show — Most Chaotic
Blend, Most Mainstream Blend, Most Underground Blend, Widest Time Machine,
and the one nobody wants to win: The Copycat Award. Every trophy comes with
receipts — real computed stats, not vibes.


## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in Spotify credentials
uvicorn app.main:app --reload
```

Then hit:
```
http://127.0.0.1:8000/api/blend-off?blends=Alex:https://open.spotify.com/playlist/XXXX,Sam:https://open.spotify.com/playlist/YYYY
```

## Deploying to Render

1. Push this repo to GitHub
2. On Render: New → Web Service → connect the repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (also in `Procfile`)
5. Add `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` as environment variables in the Render dashboard (not committed anywhere)
6. Deploy — Render gives you a public URL, no login flow needed since this app never touches user auth
