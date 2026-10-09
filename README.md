# Analytics Wall — shared Netlify deployment

This project keeps the existing Analytics Wall UI and embedded dashboards, while storing newly uploaded dashboards and JSON update packages in shared Netlify Blobs. A dashboard uploaded by an authorized admin is visible to every visitor of the deployed site.

## What is included

- `public/index.html` — the existing Analytics Wall with shared-storage integration.
- `netlify/functions/dashboards.mjs` — API for listing, uploading, reading, deleting dashboards, and syncing JSON update packages.
- `netlify.toml` — Netlify publish directory, Functions directory, and `/api/dashboards` route.
- `package.json` — Netlify Blobs dependency.
- `.env.example` — example admin secret variable.

## Deploy it (recommended: GitHub + Netlify)

1. Extract this project ZIP on your computer.
2. Create a private GitHub repository and upload the **contents** of this folder (the `public` and `netlify` folders, `netlify.toml`, and `package.json`).
3. Open Netlify and choose **Add new site → Import an existing project**. Connect the repository.
4. Build settings should be:
   - Build command: leave blank
   - Publish directory: `public`
   - Functions directory: `netlify/functions` (already set in `netlify.toml`)
5. Deploy the site.
6. In Netlify, open **Site configuration → Environment variables** and add `ADMIN_KEY`. Set a long, unique secret (at least 24 random characters). Do not put the secret into `index.html` or GitHub.
7. Redeploy after adding the variable.
8. In the deployed site, click **Upload New Dashboard** and enter the exact `ADMIN_KEY` when prompted. The key is remembered only for the current browser session. Use the same key for shared JSON updates and deletions.
9. Open the public site in a different browser/device. The uploaded dashboard should appear there too.

## Netlify Blobs

The function uses Netlify Blobs. On a site deployed to Netlify, the Blobs store is provisioned/connected through the Netlify runtime. If the function reports a Blobs/configuration error, check the site deploy logs and ensure the site is deployed in a Netlify environment that supports Blobs, then redeploy.

## Local preview

This is a server-backed project, so do **not** double-click `public/index.html` and expect shared storage to work. For a local preview, install Node.js LTS, run `npm install`, then run `npx netlify dev` from this folder. Set `ADMIN_KEY` in a local `.env` file (copy `.env.example` to `.env` and change the value). The local preview requires Netlify CLI and a working Netlify Blobs context; production deployment is the most reliable test for shared storage.

## Important notes

- The original built-in dashboards are preserved in the HTML.
- Uploaded dashboards are stored as chunks, so larger HTML dashboards do not need to fit in one serverless request.
- Uploaded dashboards and their deletions are shared for all site visitors.
- JSON update packages for the dashboard IDs already supported by the existing update engine are mirrored to shared storage and downloaded by other visitors.
- This version does not add user accounts or role-based permissions. The shared write API is protected by the `ADMIN_KEY`; anyone who knows that key can add, update, or delete shared content. Keep it private and rotate it if it is exposed.
- If a dashboard contains private/customer data, do not upload it to a publicly accessible site unless access control is added to the site itself.
