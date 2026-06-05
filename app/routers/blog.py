from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.data.blog_loader import load_posts, get_post

router = APIRouter(tags=["blog"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    posts = load_posts()
    return templates.TemplateResponse("blog/index.html", {
        "request": request,
        "posts": posts,
        "user": None,
    })


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str, request: Request):
    post = get_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    all_posts = load_posts()
    idx = next((i for i, p in enumerate(all_posts) if p["slug"] == slug), 0)
    prev_post = all_posts[idx - 1] if idx > 0 else None
    next_post = all_posts[idx + 1] if idx < len(all_posts) - 1 else None
    return templates.TemplateResponse("blog/post.html", {
        "request": request,
        "post": post,
        "prev_post": prev_post,
        "next_post": next_post,
        "user": None,
    })
