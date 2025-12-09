# bsp-rates-web-scraper

## Getting Started:
1. Create a .env file for all environment variables.
2. `pip install virtualenv`
2. `virtualenv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `playwright install`
6. `python main.py`

## cron job:
```bash
SHELL=/bin/bash
15 9 * * * cd /path/to/project && /path/to/project/.venv/bin/python3 /path/to/project/main.py command args
```