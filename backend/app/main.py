import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .db import connect, init_db
from .schemas import RuleIn, ReviewIn, ContentUpdate, StatusUpdate, CommentIn

app = FastAPI(title="BrandGuard AI API", version="0.2.0",
              description="Explainable brand-rule review and human approval MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.on_event("startup")
def startup():
    init_db()

def dictrow(row):
    return dict(row) if row else None

def event(db, review_id, actor, action, details=""):
    db.execute("INSERT INTO events(review_id, actor, action, details) VALUES(?,?,?,?)",
               (review_id, actor, action, details))

def get_review_or_404(db, rid):
    row = db.execute("SELECT * FROM reviews WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Review not found")
    return row

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "BrandGuard AI API"}

@app.get("/api/rules")
def list_rules():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM rules ORDER BY id DESC")]

@app.post("/api/rules")
def create_rule(payload: RuleIn):
    with connect() as db:
        cur = db.execute("""INSERT INTO rules(name,rule_type,pattern,replacement,severity,explanation,enabled)
            VALUES(?,?,?,?,?,?,?)""", (payload.name, payload.rule_type, payload.pattern,
            payload.replacement, payload.severity, payload.explanation, int(payload.enabled)))
        return dict(db.execute("SELECT * FROM rules WHERE id=?", (cur.lastrowid,)).fetchone())

@app.patch("/api/rules/{rule_id}")
def toggle_rule(rule_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone()
        if not row: raise HTTPException(404, "Rule not found")
        db.execute("UPDATE rules SET enabled=? WHERE id=?", (0 if row["enabled"] else 1, rule_id))
        return dict(db.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone())

def run_checks(db, review_id, content):
    db.execute("DELETE FROM findings WHERE review_id=?", (review_id,))
    rules = db.execute("SELECT * FROM rules WHERE enabled=1").fetchall()
    findings = []
    for rule in rules:
        pattern = rule["pattern"]
        matches = []
        try:
            if rule["rule_type"] == "required":
                if pattern.lower() not in content.lower():
                    matches = [pattern]
            elif rule["rule_type"] == "claim":
                matches = [m.group(0) for m in re.finditer(pattern, content, flags=re.I)]
            else:
                matches = [m.group(0) for m in re.finditer(re.escape(pattern), content, flags=re.I)]
        except re.error:
            matches = []
        for match in matches[:10]:
            if rule["rule_type"] == "required":
                excerpt = "Required phrase missing: " + pattern
                issue_type = "Missing terminology"
                suggestion = "Consider adding the approved phrase: " + pattern
            elif rule["rule_type"] == "claim":
                excerpt = match
                issue_type = "Needs human verification"
                suggestion = "Attach an approved source or rewrite this claim more cautiously."
            else:
                excerpt = match
                issue_type = "Brand terminology"
                suggestion = rule["replacement"] or "Review and rewrite this phrase."
            cur = db.execute("""INSERT INTO findings
                (review_id,rule_id,rule_name,issue_type,severity,excerpt,explanation,suggestion)
                VALUES(?,?,?,?,?,?,?,?)""",
                (review_id, rule["id"], rule["name"], issue_type, rule["severity"],
                 excerpt, rule["explanation"], suggestion))
            findings.append(dict(db.execute("SELECT * FROM findings WHERE id=?", (cur.lastrowid,)).fetchone()))
    # A deliberately conservative heuristic: claims are sent for human verification, never stated as false.
    if re.search(r"\b(guarantee|guaranteed|proven|number one|no\.?\s*1)\b", content, re.I):
        already = any(f["excerpt"].lower() in content.lower() and f["issue_type"] == "Needs human verification" for f in findings)
        if not already:
            cur = db.execute("""INSERT INTO findings
                (review_id,rule_name,issue_type,severity,excerpt,explanation,suggestion)
                VALUES(?,?,?,?,?,?,?)""", (review_id, "Promotional claim review", "Needs human verification",
                "high", "Promotional claim detected",
                "This wording may imply a factual or performance claim. The system has not verified it; a reviewer should check approved evidence.",
                "Link an approved source or use qualified wording."))
            findings.append(dict(db.execute("SELECT * FROM findings WHERE id=?", (cur.lastrowid,)).fetchone()))
    return findings

@app.post("/api/reviews")
def create_review(payload: ReviewIn):
    with connect() as db:
        cur = db.execute("INSERT INTO reviews(title,content,created_by,status) VALUES(?,?,?,'draft')",
                         (payload.title, payload.content, payload.created_by))
        rid = cur.lastrowid
        event(db, rid, payload.created_by, "Created draft", "Content submitted for brand review.")
        findings = run_checks(db, rid, payload.content)
        event(db, rid, payload.created_by, "Checks completed", f"{len(findings)} finding(s) generated.")
        return review_detail(db, rid)

@app.get("/api/reviews")
def list_reviews():
    with connect() as db:
        rows = db.execute("""SELECT r.*, (SELECT COUNT(*) FROM findings f WHERE f.review_id=r.id) finding_count
            FROM reviews r ORDER BY r.updated_at DESC, r.id DESC""").fetchall()
        return [dict(r) for r in rows]

def review_detail(db, rid):
    r = dict(get_review_or_404(db, rid))
    r["findings"] = [dict(x) for x in db.execute("SELECT * FROM findings WHERE review_id=? ORDER BY id", (rid,))]
    r["events"] = [dict(x) for x in db.execute("SELECT * FROM events WHERE review_id=? ORDER BY id DESC", (rid,))]
    r["comments"] = [dict(x) for x in db.execute("SELECT * FROM comments WHERE review_id=? ORDER BY id DESC", (rid,))]
    return r

@app.get("/api/reviews/{review_id}")
def get_review(review_id: int):
    with connect() as db:
        return review_detail(db, review_id)

@app.put("/api/reviews/{review_id}/content")
def update_content(review_id: int, payload: ContentUpdate):
    with connect() as db:
        r = get_review_or_404(db, review_id)
        if r["status"] == "approved":
            raise HTTPException(409, "Approved content is locked. Create a new review to make further edits.")
        db.execute("UPDATE reviews SET content=?, status='draft', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (payload.content, review_id))
        event(db, review_id, payload.actor, "Content revised", "Creator saved a new content version.")
        findings = run_checks(db, review_id, payload.content)
        event(db, review_id, payload.actor, "Checks rerun", f"{len(findings)} finding(s) generated.")
        return review_detail(db, review_id)

@app.post("/api/reviews/{review_id}/check")
def rerun_checks(review_id: int, actor: str = "Creator"):
    with connect() as db:
        r = get_review_or_404(db, review_id)
        findings = run_checks(db, review_id, r["content"])
        db.execute("UPDATE reviews SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (review_id,))
        event(db, review_id, actor, "Checks rerun", f"{len(findings)} finding(s) generated.")
        return review_detail(db, review_id)

@app.patch("/api/reviews/{review_id}/status")
def update_status(review_id: int, payload: StatusUpdate):
    with connect() as db:
        r = get_review_or_404(db, review_id)
        if payload.status == "approved" and r["status"] == "approved":
            raise HTTPException(409, "This review is already approved.")
        if payload.status in ("changes_requested", "rejected") and not payload.reason.strip():
            raise HTTPException(400, "Please provide a reason for this decision.")
        db.execute("UPDATE reviews SET status=?, reviewer=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (payload.status, payload.actor, review_id))
        label = {"in_review":"Submitted for review", "changes_requested":"Changes requested",
                 "approved":"Approved", "rejected":"Rejected"}[payload.status]
        event(db, review_id, payload.actor, label, payload.reason)
        return review_detail(db, review_id)

@app.post("/api/reviews/{review_id}/comments")
def add_comment(review_id: int, payload: CommentIn):
    with connect() as db:
        get_review_or_404(db, review_id)
        cur = db.execute("INSERT INTO comments(review_id,actor,body) VALUES(?,?,?)",
                         (review_id, payload.actor, payload.body))
        event(db, review_id, payload.actor, "Comment added", payload.body[:180])
        return dict(db.execute("SELECT * FROM comments WHERE id=?", (cur.lastrowid,)).fetchone())

@app.get("/api/insights")
def insights():
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        statuses = {r["status"]: r["n"] for r in db.execute("SELECT status, COUNT(*) n FROM reviews GROUP BY status")}
        top = [dict(r) for r in db.execute("""SELECT rule_name, issue_type, severity, COUNT(*) count
            FROM findings GROUP BY rule_name, issue_type, severity ORDER BY count DESC LIMIT 8""")]
        recent = [dict(r) for r in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 12")]
        return {"total_reviews": total, "statuses": statuses, "top_issues": top, "recent_events": recent}
