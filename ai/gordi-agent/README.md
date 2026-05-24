# gordita

Hermes + Honcho backed by Claude and GLM.

## Setup

```bash
# 1. Clone Honcho (build dependency)
git clone https://github.com/plastic-labs/honcho.git honcho

# 2. Configure env
cp .env.example .env  # fill in ANTHROPIC_API_KEY, GLM_API_KEY, HONCHO_DB_PASSWORD

# 3. Hermes first-time setup (select Anthropic + z.ai when prompted)
mkdir -p ~/.hermes
docker run -it --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent setup

# 4. Start
docker compose up -d --build
```

## Endpoints

| Service | URL |
|---|---|
| Hermes gateway | http://localhost:8642 |
| Hermes dashboard | http://localhost:9119 |
| Honcho API | http://localhost:8000 |
