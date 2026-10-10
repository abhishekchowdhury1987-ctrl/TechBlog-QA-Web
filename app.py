import copy
import hmac
import json
import os
import re
import secrets
import tempfile

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["EDITOR_PASSWORD"] = os.environ.get("DEV_EDITOR_PASSWORD")
CONTENT_FILE = os.path.join(app.root_path, "data", "stories.json")

ARTICLES = [
    {
        "slug": "building-faster-ai-experiences",
        "title": "Building faster AI experiences with smarter inference",
        "summary": "A practical look at the tools and techniques helping teams move generative AI from prototype to production.",
        "category": "AI & ML",
        "date": "October 2, 2026",
        "read_time": "8 min read",
        "author": "Maya Chen",
        "image": "photo-1677442136019-21780ecad995",
        "accent": "violet",
    },
    {
        "slug": "designing-for-the-agentic-web",
        "title": "Designing products for the agentic web",
        "summary": "The best agent experiences feel less like a chatbot and more like a thoughtful collaborator.",
        "category": "Web",
        "date": "September 29, 2026",
        "read_time": "6 min read",
        "author": "Jordan Lee",
        "image": "photo-1498050108023-c5249f4df085",
        "accent": "blue",
    },
    {
        "slug": "shipping-smaller-android-apps",
        "title": "A smaller Android app starts with a better build",
        "summary": "Trim what you ship, speed up installs, and make every megabyte count with these build system improvements.",
        "category": "Android",
        "date": "September 25, 2026",
        "read_time": "5 min read",
        "author": "Priya Nair",
        "image": "photo-1512941937669-90a1b58e7e9c",
        "accent": "green",
    },
    {
        "slug": "cloud-costs-without-compromise",
        "title": "Keep cloud costs in check without slowing down",
        "summary": "A platform team's field guide to right-sizing workloads while keeping services resilient and ready to scale.",
        "category": "Cloud",
        "date": "September 22, 2026",
        "read_time": "7 min read",
        "author": "Sam Rivera",
        "image": "photo-1451187580459-43490279c0fa",
        "accent": "orange",
    },
    {
        "slug": "the-new-rules-of-accessibility",
        "title": "Accessibility is a product advantage",
        "summary": "Small, intentional improvements can make your interface work better for everyone who uses it.",
        "category": "Design",
        "date": "September 18, 2026",
        "read_time": "4 min read",
        "author": "Alex Morgan",
        "image": "photo-1558655146-d09347e92766",
        "accent": "pink",
    },
    {
        "slug": "open-source-maintainers-that-scale",
        "title": "Open source maintainer habits that scale",
        "summary": "Healthy projects are built on more than code. Here are the small practices that help communities thrive.",
        "category": "Open source",
        "date": "September 15, 2026",
        "read_time": "6 min read",
        "author": "Devon Brooks",
        "image": "photo-1522071820081-009f0129c71c",
        "accent": "teal",
    },
]

FEATURED = {
    "slug": "from-prompt-to-production",
    "title": "From prompt to production: a new era for AI developers",
    "summary": "Meet the ideas, logics, and teams turning the next wave of AI breakthroughs into products people can use every day.",
    "category": "AI & ML",
    "date": "October 4, 2026",
    "read_time": "9 min read",
    "author": "The QABeacon team",
    "image": "photo-1676299081847-824916de030a",
    "accent": "violet",
}

TOPICS = ["AI & ML", "Web", "Android", "Cloud", "Design", "Open source"]
DEFAULT_STORY_IMAGE = "photo-1677442136019-21780ecad995"
DEFAULT_STORY_BLOCKS = (
    (
        "paragraph",
        "Good ideas create value when applied in real-world contexts. For developers and testers, this means transforming promising tools and emerging capabilities into experiences that are reliable, thoughtfully designed, and genuinely useful.",
    ),
    ("heading", "Start with the problem"),
    (
        "paragraph",
        "Before reaching for a new framework or model, get close to the people who will use what you build. The most effective solutions begin with a clear understanding of the friction they are meant to remove. A small, well-tested improvement is often more valuable than a sweeping rewrite.",
    ),
    (
        "paragraph",
        "From there, make room to experiment. Build a focused prototype, measure how it performs in real conditions, and use what you learn to guide the next iteration. This approach keeps teams moving while making it easier to spot the details that matter.",
    ),
    ("heading", "Make progress you can trust"),
    (
        "paragraph",
        "Great developer tools make the path from idea to launch clearer. Strong defaults, accessible design, and careful attention to performance help teams spend less time fighting their stack and more time creating something meaningful.",
    ),
    (
        "paragraph",
        "Keep learning, share what works, and bring your community along. That's how good ideas become the foundations for what's next.",
    ),
)


def get_story_body(article):
    return article.get("body") or "\n\n".join(
        (article["summary"], *(text for _, text in DEFAULT_STORY_BLOCKS))
    )


def get_story_blocks(article):
    if not article.get("body"):
        return [("lede", article["summary"]), *DEFAULT_STORY_BLOCKS]
    return [
        ("paragraph", paragraph)
        for paragraph in article["body"].split("\n\n")
        if paragraph.strip()
    ]


def load_content():
    if not os.path.exists(CONTENT_FILE):
        return {"featured": copy.deepcopy(FEATURED), "articles": copy.deepcopy(ARTICLES)}

    with open(CONTENT_FILE, encoding="utf-8") as content_file:
        content = json.load(content_file)
    if (
        not isinstance(content, dict)
        or not isinstance(content.get("articles"), list)
        or (content.get("featured") is not None and not isinstance(content["featured"], dict))
    ):
        raise ValueError(f"Invalid blog content format in {CONTENT_FILE}")
    return content


def save_content(content):
    os.makedirs(os.path.dirname(CONTENT_FILE), exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(CONTENT_FILE),
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(content, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, CONTENT_FILE)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def editor_token():
    if "editor_csrf_token" not in session:
        session["editor_csrf_token"] = secrets.token_urlsafe(32)
    return session["editor_csrf_token"]


@app.context_processor
def inject_editor_state():
    return {
        "editor_signed_in": session.get("developer_authenticated", False),
        "editor_enabled": bool(app.config["EDITOR_PASSWORD"]),
        "editor_csrf_token": editor_token,
    }


@app.before_request
def protect_editor():
    if not request.path.startswith("/editor"):
        return
    if not app.config["EDITOR_PASSWORD"]:
        abort(503, description="Set DEV_EDITOR_PASSWORD to enable the developer editor.")
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        if not hmac.compare_digest(submitted_token, session.get("editor_csrf_token", "")):
            abort(400, description="Your editor session expired. Reload the page and try again.")
    if request.endpoint == "editor_login":
        return
    if not session.get("developer_authenticated"):
        return redirect(url_for("editor_login"))


def make_slug(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    return slug or secrets.token_hex(4)


def validate_story(form, existing_slug=None, existing_image=None):
    fields = {
        "title": (160, "Title"),
        "summary": (500, "Summary"),
        "category": (40, "Topic"),
        "date": (40, "Date"),
        "read_time": (30, "Reading time"),
        "author": (80, "Author"),
    }
    story_data = {}
    for key, (limit, label) in fields.items():
        value = form.get(key, "").strip()
        if not value or len(value) > limit:
            raise ValueError(f"{label} is required and must be under {limit} characters.")
        story_data[key] = value

    if story_data["category"] not in TOPICS:
        raise ValueError("Choose a topic from the list.")

    story_data["slug"] = existing_slug or make_slug(story_data["title"])
    story_data["image"] = existing_image or DEFAULT_STORY_IMAGE
    story_data["body"] = (
        form.get("body", "").replace("\r\n", "\n").replace("\r", "\n").strip()
    )
    if not story_data["body"] or len(story_data["body"]) > 20000:
        raise ValueError("Story text is required and must be under 20,000 characters.")
    return story_data


@app.get("/")
def index():
    content = load_content()
    query = request.args.get("q", "").strip()
    category = request.args.get("topic", "").strip()
    articles = content["articles"]
    featured = content.get("featured")

    if category in TOPICS:
        articles = [article for article in articles if article["category"] == category]
    if query:
        search_text = query.casefold()
        articles = [
            article
            for article in articles
            if search_text
            in " ".join(
                (
                    article["title"],
                    article["summary"],
                    article["category"],
                    article["author"],
                    article.get("body", ""),
                )
            ).casefold()
        ]

    if featured and ((category and category != featured["category"]) or (
        query
        and query.casefold()
        not in " ".join(
            (
                featured["title"],
                featured["summary"],
                featured["category"],
                featured["author"],
                featured.get("body", ""),
            )
        ).casefold()
    )):
        featured = None

    return render_template(
        "index.html",
        articles=articles,
        featured=featured,
        topics=TOPICS,
        query=query,
        selected_topic=category if category in TOPICS else "",
    )


@app.get("/stories/<slug>")
def story(slug):
    content = load_content()
    article = next(
        (
            item
            for item in [content.get("featured"), *content["articles"]]
            if item and item["slug"] == slug
        ),
        None,
    )
    if article is None:
        return render_template("404.html"), 404
    return render_template(
        "story.html",
        article=article,
        story_blocks=get_story_blocks(article),
    )


@app.route("/editor/login", methods=["GET", "POST"])
def editor_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, app.config["EDITOR_PASSWORD"]):
            session.clear()
            session["developer_authenticated"] = True
            flash("You're signed in to the story editor.", "success")
            return redirect(url_for("editor"))
        flash("That password didn't match. Please try again.", "error")
    return render_template("editor_login.html")


@app.post("/editor/logout")
def editor_logout():
    session.clear()
    flash("You have signed out of the editor.", "success")
    return redirect(url_for("index"))


@app.get("/editor")
def editor():
    content = load_content()
    return render_template(
        "editor.html",
        articles=content["articles"],
        featured=content.get("featured"),
        topics=TOPICS,
    )


@app.route("/editor/stories/new", methods=["GET", "POST"])
def create_story():
    if request.method == "POST":
        try:
            article = validate_story(request.form)
            content = load_content()
            if any(
                item["slug"] == article["slug"]
                for item in [content.get("featured"), *content["articles"]]
                if item
            ):
                raise ValueError("A story with this title already exists.")
            if request.form.get("feature"):
                if content.get("featured"):
                    content["articles"].insert(0, content["featured"])
                content["featured"] = article
            else:
                content["articles"].insert(0, article)
            save_content(content)
            flash("Your story is published.", "success")
            return redirect(url_for("editor"))
        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "editor_form.html",
                article=request.form,
                is_featured=bool(request.form.get("feature")),
                topics=TOPICS,
            )
    return render_template("editor_form.html", article=None, is_featured=False, topics=TOPICS)


@app.route("/editor/stories/<slug>/edit", methods=["GET", "POST"])
def edit_story(slug):
    content = load_content()
    article = next(
        (
            item
            for item in [content.get("featured"), *content["articles"]]
            if item and item["slug"] == slug
        ),
        None,
    )
    if article is None:
        abort(404)
    is_featured = content.get("featured", {}).get("slug") == slug

    if request.method == "POST":
        try:
            updated_article = validate_story(
                request.form,
                existing_slug=slug,
                existing_image=article.get("image"),
            )
            if request.form.get("feature"):
                if content.get("featured") and not is_featured:
                    content["articles"].insert(0, content["featured"])
                content["articles"] = [
                    item for item in content["articles"] if item["slug"] != slug
                ]
                content["featured"] = updated_article
            elif is_featured:
                content["featured"] = None
                content["articles"].insert(0, updated_article)
            else:
                content["articles"] = [
                    updated_article if item["slug"] == slug else item
                    for item in content["articles"]
                ]
            save_content(content)
            flash("Your story has been updated.", "success")
            return redirect(url_for("editor"))
        except ValueError as error:
            flash(str(error), "error")
            article = {**article, **request.form}
            is_featured = bool(request.form.get("feature"))

    return render_template(
        "editor_form.html",
        article={**article, "body": get_story_body(article)},
        is_featured=is_featured,
        topics=TOPICS,
    )


@app.post("/editor/stories/<slug>/delete")
def delete_story(slug):
    content = load_content()
    featured = content.get("featured")
    original_article_count = len(content["articles"])
    content["articles"] = [
        article for article in content["articles"] if article["slug"] != slug
    ]
    if featured and featured["slug"] == slug:
        content["featured"] = None
    elif len(content["articles"]) == original_article_count:
        abort(404)
    save_content(content)
    flash("The story has been deleted.", "success")
    return redirect(url_for("editor"))


@app.post("/subscribe")
def subscribe():
    email = request.form.get("email", "").strip()
    if not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        flash("Enter a valid email address to subscribe.", "error")
    else:
        flash("You're on the list. Look out for the next QABeacon dispatch.", "success")
    return redirect(url_for("index") + "#newsletter")


if __name__ == "__main__":
    app.run(debug=True)
