# QASignal

A responsive QA and automation testing publication built with Flask. It includes searchable stories, topic filters, individual story pages, and a newsletter signup form.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000.

## Deploy on Render

Use `pip install -r requirements.txt` as the build command and
`gunicorn app:app --bind 0.0.0.0:$PORT` as the start command. The first `app`
refers to `app.py`; the second refers to the Flask application object in that
file.

## Developer story editor

Set a developer password before starting the app to enable the editor:

```powershell
$env:DEV_EDITOR_PASSWORD = "choose-a-private-password"
$env:FLASK_SECRET_KEY = "set-a-long-random-secret"
python app.py
```

Open http://127.0.0.1:5000/editor to sign in. The editor lets you create, update, feature, and delete stories. Changes are saved in `data/stories.json` and appear on the blog immediately. Story text is plain text; blank lines become paragraph breaks. New stories use the default image, and editing an existing story preserves its current image.

Keep both values private and use a strong `FLASK_SECRET_KEY` outside local development. The editor is disabled when `DEV_EDITOR_PASSWORD` is not set.
