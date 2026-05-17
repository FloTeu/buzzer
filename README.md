# Buzzer

## Local Development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv run main.py
```

The app is then available at `http://localhost:8080`.

Admin panel: `http://localhost:8080/admin`

## Deployment

```bash
gcloud run deploy buzzer --source . --region europe-west1 --allow-unauthenticated --max-instances 1 --project <project-id>
```

> `--max-instances 1` is required because the app uses in-memory state. For multi-instance setups, replace `GameState` with Firestore or Redis.