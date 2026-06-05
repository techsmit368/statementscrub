import json
from pathlib import Path

POSTS_DIR = Path(__file__).parent / "posts"


def load_posts() -> list[dict]:
    posts = []
    for f in sorted(POSTS_DIR.glob("*.json"), reverse=True):
        try:
            posts.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return posts


def get_post(slug: str) -> dict | None:
    for f in POSTS_DIR.glob("*.json"):
        try:
            post = json.loads(f.read_text(encoding="utf-8"))
            if post.get("slug") == slug:
                return post
        except Exception:
            pass
    return None
