# Padhotec

A study platform that models each student's knowledge, risk, and next best action with calibrated
uncertainty. See [docs/PLAN.md](docs/PLAN.md) for the five-phase plan.

## Run the backend

```sh
cd backend
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
uv run pytest
```

## Run the frontend

```sh
cd frontend
npm install
npm run dev   # http://localhost:3000
```

The app talks to the API at `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` to change that.

## Models

The risk model and its backtests need the OULAD dataset (CC BY 4.0) in `backend/ml/data/oulad/`. It is not
in the repo. Download it from the [UCI mirror](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset)
and unzip the CSVs there. The trained model ships in the repo, so the app runs without the dataset.
See [docs/MODELS.md](docs/MODELS.md) for methods, results and limits.

## Database

By default the backend uses a local SQLite file. To use Postgres, run `docker compose up -d db` and set
`PADHOTEC_DATABASE_URL` as shown in `backend/.env.example`.

Set `PADHOTEC_JWT_SECRET` to a long random value before deploying. The built-in default is for
local development only.
