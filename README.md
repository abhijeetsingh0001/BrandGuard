# BrandGuard AI — Round 2 MVP

An explainable brand-governance platform for checking marketing content against approved brand rules, editing suggested corrections, and routing content through human review.

## Implemented MVP workflow
1. Create/list brand rules (prohibited terms, required terms, approved facts, style rules).
2. Submit content for review.
3. Run deterministic checks and receive findings with severity, explanation, evidence/rule source, and suggested corrections where possible.
4. Edit the content and rerun checks.
5. Submit for human review; reviewer can comment, approve, request changes, or reject with a reason.
6. View revision/event history and governance insights.

## Stack
- Frontend: React + Vite
- API: Python + FastAPI
- Storage: SQLite by default (keeps judge setup simple; PostgreSQL was the Round 1 proposal and can replace SQLite for deployment)
- Checks: deterministic Python rules; uncertain promotional claims are marked "Needs human verification". No external LLM is required for the core workflow.

## Run locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://127.0.0.1:8000/docs

### 2. Frontend
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open the Vite URL printed in the terminal (usually http://localhost:5173).

The frontend expects `http://127.0.0.1:8000`. Set `VITE_API_URL` in `frontend/.env` if needed.

## Demo walkthrough for judges
1. Open the app and visit **Brand Rules**. Starter rules are seeded on first API launch.
2. Go to **New Review**, enter sample content such as:
   `Our product is the best on the market. Contact us for a free trial. We guarantee 100% results.`
3. Run review. Inspect the explainable flags.
4. Edit the text, save changes, and rerun checks.
5. Send to review. Switch the role selector to **Reviewer**, add a comment, and approve / request changes / reject.
6. Open **History & Insights** to inspect events and recurring issue types.

## Important scope / honesty notes
- This is a functional MVP, not a production security certification.
- The role selector is a demo workflow convenience, not secure authentication. Add real login, server-enforced RBAC, audit hardening and deployment secrets before production.
- Exact wording checks are deterministic. Potential unsupported claims are signals for a human reviewer, not factual verdicts.
- Image OCR, external LLM integration, SSO, and direct publishing integrations are not implemented in this Round 2 MVP.
- Do not claim performance metrics until your team runs and records tests.

## Deployment outline
- Deploy the FastAPI service to Render / Railway / a similar Python host, with a persistent disk or managed PostgreSQL.
- Deploy the Vite frontend to Vercel / Netlify and set `VITE_API_URL` to the deployed API URL.
- Configure CORS for the deployed frontend origin and use persistent database storage.
- Add a real authentication provider and server-side roles before exposing confidential brand materials.

## Round 3 proposed major improvements
1. Source-linked verification and retrieval over uploaded brand documents / approved facts, with confidence labels and an explicit uncertainty path.
2. Production-grade reviewer collaboration: authenticated role-based access, assignment, threaded comments, immutable audit trail and side-by-side revision comparison.
3. Governance analytics and visual checks: recurring issue trends, rule-quality recommendations, and logo/colour/asset checks with OCR or vision support.
