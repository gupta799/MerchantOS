# Local Kernel Tunnel (SSH)

Use this when you want Kernel browsers to reach your local dev server without ngrok.

## 1) Start local dev server

```bash
npm run dev
```

Notes:
- Frontend defaults to http://localhost:5173
- Backend defaults to http://localhost:8000

## 2) Create a Kernel browser with longer timeout

```bash
kernel browsers create --timeout 600
```

This returns a session id (example: sess_abc123).

## 3) Forward your local port into the browser VM

Frontend example:

```bash
kernel browsers ssh sess_abc123 -R 5173:localhost:5173
```

Backend example:

```bash
kernel browsers ssh sess_abc123 -R 8000:localhost:8000
```

You can open two terminals if you need both forwards at the same time.

## 4) Open the site inside the browser live view

In the browser live view, visit:
- http://localhost:5173

If you forwarded the backend too, the frontend should be able to reach it at:
- http://localhost:8000

## Troubleshooting

- If the live view cannot load localhost, confirm the SSH reverse tunnel is still active.
- If ports differ, update the -R arguments to match your local dev server.
