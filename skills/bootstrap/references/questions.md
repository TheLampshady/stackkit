# Interview questions

Ask in this order, one at a time, in these words or close to them. Each comes with the default to offer. Skip any question the brief already answered, and say what you assumed.

| # | Ask | Default to offer | Sets |
|---|-----|------------------|------|
| 1 | "In a sentence or two, what should this do, and who is it for?" | none; this is the brief | everything below |
| 2 | "What should we call it?" | a two- or three-word name from their answer, e.g. **Bakery Orders** | `--display-name`; `--name` is its kebab-case form (`bakery-orders`) |
| 3 | "Will people use it by opening a page in their web browser?" | yes, if the brief mentions people, customers, a site, a page or a dashboard | no → remove `frontend` |
| 4 | "Should it have an AI assistant that works on its own, like answering questions or doing tasks for people?" | no, unless the brief asks for AI that acts or chats | no → remove `agents` |
| 5 | "Who should be able to sign in: anyone with a Google account, or only people with an email at your organization?" | anyone | organization → `VALID_DOMAINS=<their domain>`; anyone → empty |
| 6 | "Do you already have a Google Cloud project for this? If you're not sure, that's fine, we'll set it up later." | not yet | yes → `PROJECT_ID=<id>`, `USE_EMULATOR=false`; no → `PROJECT_ID=` empty, `USE_EMULATOR=true` (everything runs on this computer) |
| 7 | "Where should I put it on your computer?" | `~/projects/<kebab-name>` | `--dest` |

## Always, without asking

- Remove `notebooks` and `http_tests`. They're developer tools. Keep them only if the person turns out to be a developer and asks.
- `NAMESPACE=<kebab-name>`.

## Reading the brief

- **"Just an API" / "backend for an app someone else builds" / a phone app:** no frontend.
- **A chatbot or assistant people talk to in the browser:** keep both frontend and agents.
- **Internal team tool:** suggest organization-only sign-in at question 5, but let them choose.
- **Something this stack can't do** (a phone app, a game, hardware): say so plainly, and offer the closest thing it can do (for example, the backend a phone app would talk to) before going on.
