# DuoStats

Duolingo progress visualizer with a daily-updated profile card, weekly chart, and stats explorer. Built with Python, GitHub Actions, and a static web UI.

Forked from https://github.com/lauslim12/japanese-duolingo-visualizer.

## Quick Start (GitHub Actions)

1) Fork this repository.
2) Log in to Duolingo in your browser and copy your JWT cookie value.
3) Add repository secrets in Settings -> Secrets and variables -> Actions:
   - `DUOLINGO_USERNAME`
   - `DUOLINGO_JWT`
   - `GIT_AUTHOR_NAME`
   - `GIT_AUTHOR_EMAIL`
   - Optional: `DUOLINGO_PASSWORD`
4) Enable GitHub Pages:
   - Settings -> Pages -> Source = Deploy from a branch
   - Branch = `main`, Folder = `/web`

The workflow runs daily and updates the data files plus web/card.svg.

## Local Setup

```bash
git clone <your-fork>
cd DuoStats

uv python install
uv sync --all-extras
source .venv/bin/activate

cp .env.example .env
```

Edit `.env` and set:

```env
DUOLINGO_USERNAME=your_username
DUOLINGO_JWT=your_jwt
DUOSTATS_LANGUAGE_LEVELS=English:130,Japanese:12
```

Run the sync and serve the site:

```bash
bash scripts/local-sync.sh
cd web
python -m http.server 8000
```

## Outputs

- Static page: `/web/index.html`
- SVG card: `/web/card.svg`

## License

MIT License.
