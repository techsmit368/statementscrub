import json
from pathlib import Path

POSTS_DIR = Path(__file__).parent / "posts"


# utf-8-sig strips a leading BOM if present (several post files were saved
# with one by PowerShell); it is harmless for plain UTF-8 files. Without this
# json.loads raises on the BOM and the post is silently skipped.
def load_posts() -> list[dict]:
    posts = []
    for f in sorted(POSTS_DIR.glob("*.json"), reverse=True):
        try:
            posts.append(json.loads(f.read_text(encoding="utf-8-sig")))
        except Exception:
            pass
    return posts


def get_post(slug: str) -> dict | None:
    for f in POSTS_DIR.glob("*.json"):
        try:
            post = json.loads(f.read_text(encoding="utf-8-sig"))
            if post.get("slug") == slug:
                return post
        except Exception:
            pass
    return None
