# FinAlly Frontend

Next.js 16 (App Router) + TypeScript + Tailwind v4. Static export served by FastAPI.

## Develop

```
npm install
npm run dev          # http://localhost:3000 (proxies /api expected on :8000)
npm run test         # Vitest + RTL
npm run typecheck
npm run build        # writes static export to ./out
```

## Notes

- Static export (`output: 'export'`). API calls go to `/api/*` on the same origin in production. In dev, run the FastAPI backend on the same port or proxy.
- Theme tokens live in `app/globals.css` under `@theme`. Palette: bg `#0d1117` / `#1a1a2e`, accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991`.
- Live prices flow via `useSseStream` -> `priceStore` (zustand). Sparklines accumulate up to 60 points per ticker since page load.
