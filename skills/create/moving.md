# Moving code into stackkit

How to fit existing code into a stackkit project: a whole project being moved onto stackkit, or a feature from another project being added to one. `bootstrap` reads this while it builds the move list and asks about what doesn't fit; `create` follows it while it moves the code.

## The aim

Move as much of the old code as will fit, and adapt it so the project's own make targets run it. Don't rewrite what can be moved. When the move is done:

- `make setup` installs everything the moved code needs
- `make run` serves the moved app (`make run-fe` the page alone, `make run-be` the server alone)
- `make build` builds the moved frontend into the server's static folder (`make build-fe` the page alone)
- `make check` lints, typechecks and tests the moved code with the template's own tools
- anything else the old project ran (seeding data, a worker, a scheduled job, a script) has its own make target

The template's targets and tooling stay as they are: adapt the moved code to Vite, Bun, FastAPI and uv, not the Makefile to the old toolchain. Add new targets only for jobs the template has no target for.

## How to move

1. **Copy, then adapt.** Copy whole code folders across with `--copy` into the folder they belong in (table below), then fix them in place with Edit. Copying keeps the code, its comments and its structure. Write new files only for glue (routes, a page wrapper, a FastAPI route that replaces a server-side handler).
2. **Dependencies follow the code.** Add each package the moved code imports to `frontend/package.json` or the right `pyproject.toml` with Edit, at the old project's version where it still works with the template's (React 19, Vite, Tailwind v4). Leave out what the move replaces (the old framework, its auth, database client and host's SDK). `check.py` installs them.
3. **Tests come too.** Move the old tests next to the code they test, on Vitest or pytest. Keep the template's own tests passing.
4. **Settings.** Public build-time settings become `VITE_` settings (`import.meta.env.VITE_*`). Server-only settings and keys become secret names (step 2 of `create`), never values.
5. **Scripts become make targets.** Each script in the old `package.json`, `Procfile`, cron config or `bin/` folder that isn't a dev, build, lint or test command gets a target in the root `Makefile`, written to run the moved code (`make seed`, `make worker`). Add it to `AGENTS.md`'s command list.
6. **Docs.** Useful parts of the old README (what it does, how it's used, gotchas) go into the new `Readme.md` or `docs/`. Setup steps for the old stack don't.

## Where things go

| Old project has | Goes to |
|---|---|
| React components, hooks, utilities, types | `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/lib/` |
| Pages or screens | `frontend/src/pages/<Name>Page.tsx`, each with a route in `frontend/src/App.tsx` |
| Static files (images, fonts, `favicon`, `robots.txt`) | `frontend/public/` |
| Global CSS | `frontend/src/index.css` |
| Server endpoints, in any language | FastAPI routes in `api_service/api/`, included in `api_router` (prefix `/api`, so URLs the page calls stay the same) |
| Python server code (Flask, Django, FastAPI) | `api_service/`, mostly as it is, its routes on `api_router` |
| Database access and models | Pydantic models and the Firestore client from `gcp_services` (`AGENTS.md`, "Firebase Client Access") |
| Sign-in | The sign-in chosen in the interview (`auth_iap` or `auth_firebase`) |
| AI calls | `shared/gcp_services/clients/gcp_vertex.py`, or an agent in `agent_service/agents/` |
| Background jobs and scripts | `api_service/` (Python) or `frontend/scripts/` (TypeScript), each with a make target |

Never keep the old layout beside the new one: no `legacy/`, `old/`, `src/`, `app/` or `public/` at the root.

## Next.js

The React code moves almost as it is. What changes is everything Next does around it: routing, rendering on the server, and API routes.

| Next.js | In stackkit |
|---|---|
| `components/`, `lib/`, `hooks/`, `types/`, `utils/` (or under `src/`) | `--copy` to the same names under `frontend/src/`. Its `@/` import alias already points at `frontend/src/` |
| `app/**/page.tsx` or `pages/**/*.tsx` | `frontend/src/pages/<Name>Page.tsx`, one route each in `createBrowserRouter` in `App.tsx`. Folder path → route path; `[id]` → `:id` with `useParams`; `[...slug]` → `*` |
| `app/**/layout.tsx`, `pages/_app.tsx` | A layout component rendering `<Outlet />`, as the parent route of its pages. Providers go around `RouterProvider` in `App.tsx` |
| `loading.tsx`, `error.tsx`, `not-found.tsx` | `isPending` and `error` from `useQuery`; the route's `errorElement`; a `*` route |
| `"use client"` | Delete the line. Everything runs in the browser |
| Server components or `getServerSideProps` / `getStaticProps` fetching data | Move the fetching into a FastAPI route; the page calls it with `useQuery` through `frontend/src/lib/api.ts`. Data that never changes can be imported directly |
| `app/api/**/route.ts`, `pages/api/**` | FastAPI routes in `api_service/api/` at the same paths under `/api`, rewritten in Python. Request and response bodies become Pydantic models |
| Server actions (`"use server"`) | A POST route in FastAPI, called with `useMutation` |
| `next/link` | `Link` from `react-router-dom`, `href` → `to` |
| `next/navigation`, `next/router` | `useNavigate`, `useParams`, `useSearchParams`, `useLocation` |
| `next/image` | `<img>` with `width`, `height` and `loading="lazy"` |
| `next/head`, `metadata` exports | `<title>` and `<meta>` in the page component (React 19 hoists them) |
| `next/font` | The font's Google Fonts `<link>` in `frontend/index.html`, or `@font-face` over files in `frontend/public/fonts/` |
| `next/dynamic` | `React.lazy` with `Suspense` |
| `middleware.ts` | Sign-in redirects: the chosen sign-in. Rewrites and headers: FastAPI middleware or routes |
| `NEXT_PUBLIC_*` | `VITE_*`, read with `import.meta.env.VITE_*` |
| `tailwind.config.*` (Tailwind 3) | `@theme` in `frontend/src/index.css` (Tailwind 4). `globals.css` content goes there too |
| shadcn/ui components | `frontend/src/components/ui/`, where the template keeps its own; keep the newer of any duplicate |
| `next-auth` / Auth.js, Clerk | The chosen sign-in; drop the package |
| Prisma, Drizzle, `pg`, Mongoose, Supabase client | Firestore through `gcp_services`; each table or collection becomes a Firestore collection and a Pydantic model. Drop the package and its schema files once the models exist |
| `vercel.json`, `next.config.*`, `next-env.d.ts`, `.eslintrc` with `next` config | Drop. Redirects in `next.config` become routes |

Drop from `package.json`: `next`, `eslint-config-next`, `@next/*`, `@vercel/*`, and whatever the table replaces.

## Other stacks

- **Create React App, Vite React, Remix:** like Next.js, minus whatever it doesn't use.
- **Plain HTML, CSS and JavaScript:** each page becomes a component in `frontend/src/pages/`, its content word for word. Scripts become React code; CSS goes to `index.css`.
- **Vue, Svelte, Angular:** the components have to be rewritten in React. Move styles, assets, content and API calls as they are, and rebuild each component to match.
- **Express, Nest or another Node server:** routes rewritten as FastAPI routes; business logic ported to Python next to them.

## Needs a decision

These change what the app does for its users, so the person chooses. Ask about each one the code has, one at a time, in plain words, with the recommended option first. Keep their answer in the move list; `create` follows it.

| The old code has | Why it doesn't fit as it is | Options to offer (first is recommended) |
|---|---|---|
| A table-style database (Postgres, MySQL, SQLite, through Prisma, Drizzle, Supabase or plain SQL) | Google's database keeps records as documents, not tables joined together | **(a)** Reshape the records onto Google's database (best for small apps: lists, orders, bookings). **(b)** Keep their current database and connect to it with a key (best when it's large or shared with other apps). **(c)** Leave saving out for now |
| Sign-in with existing accounts (NextAuth/Auth.js, Clerk, Auth0, Supabase Auth) | The accounts can't come across on their own | Public site with staff pages: **(a)** a staff area (question 5(b)): staff sign in with Google, the public pages stay open. Whole site for staff only: **(a)** Google sign-in in front of everything (5(c)). Customers who come back to their own things: **(a)** customer accounts (5(d)); people make a new account the first time, or whoever puts it online imports them. **(b)** Keep their current sign-in service, connected with a key |
| Pages that must be found in search engines (a public blog, marketing pages, rendered on the server) | stackkit's page is built in the visitor's browser | **(a)** Keep them as normal pages; search engines read most of them, and it's simplest. **(b)** Keep the most important ones as plain pages in `frontend/public/` |
| Live updates (websockets, live chat, server-sent events) | Only Cloud Run sends replies as they happen | **(a)** Host on Cloud Run (Google's web address). **(b)** Own web address; updates arrive when the page refreshes |
| Scheduled jobs (Vercel cron, a worker, a queue) | stackkit doesn't run anything on a timer | **(a)** Move the job to a server route plus a make target; a timer at Google runs it once it's online. **(b)** Leave it out for now |
| Files kept elsewhere (S3, Cloudinary, Vercel Blob, UploadThing) | stackkit keeps files in Google's storage | **(a)** Use Google's storage; whoever puts it online copies the existing files across. **(b)** Keep their current service, connected with a key |
| AI from another company (OpenAI, Mistral) | Claude and Gemini are built in with no key | **(a)** Switch to Claude or Gemini. **(b)** Keep theirs, connected with a key |
| A Vue, Svelte or Angular page | stackkit's page is React | **(a)** Rebuild the screens in React, keeping content, styles and pictures (takes longer). **(b)** Move the content and pictures now, rebuild the screens after |
| A server in another language (Node, Go, Ruby, PHP) with many endpoints | stackkit's server is Python | **(a)** Move every endpoint. **(b)** Move the ones the page uses now (list them), the rest later |
| Several apps in one repo | stackkit makes one project per run | Ask which comes first; offer the rest after |
| A phone app | stackkit makes web projects | **(a)** Build the server the phone app talks to. **(b)** A web page that does the same job |

Not on this list but still doesn't fit? Ask the same way: what it does now, why it can't come across as it is, and two or three options. Payments, email and other services with a key fit as they are: a server route and a secret name, no question needed.

## What doesn't move

- Live data and the old app's hosting and web address: handled outside stackkit when the new one goes online.
- The old CI, deploy configs and host settings. The new project has its own.
- `.env` files and key values. Secret names only.
