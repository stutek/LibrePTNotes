"""`python -m deploy` — serve src/ under /LibrePTNotes/ on the dev-server port."""

from .local_http_server import main

if __name__ == "__main__":
    main()
