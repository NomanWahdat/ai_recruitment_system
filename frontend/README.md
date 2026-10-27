# Recruitment frontend

Next.js App Router, React, TypeScript, Tailwind, Axios and TanStack Query.

Use Node 22.13+ or Node 24, then npm ci --ignore-scripts --no-audit --no-fund, npm run lint, npm run typecheck, npm run build and npm run start.

The browser uses an HttpOnly session with CSRF, not a localStorage token. Configure NEXT_PUBLIC_API_BASE_URL before building if the default local API is unsuitable. Keep frontend/API same-site for cookie authentication.

Connected screens include private candidate uploads/bulk uploads, profile evidence/correction, document replacement, jobs and criteria editing, rankings, application stages/history, AI tools and persistent task retries. Mobile navigation is included.

See the root README and docs/ for full setup, API contracts, real screenshots, evaluation and security limitations.
