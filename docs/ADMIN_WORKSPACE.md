# RiceAI Admin workspace

## Access

The management link appears only after `/api/auth/me` confirms a verified Firebase user whose database role is `admin` or `employee`. The backend checks the database role on every protected request, so changing a role takes effect without issuing a new JWT. The old local password login and registration endpoints return HTTP 410.

| Function | Admin | Employee |
| --- | --- | --- |
| View aggregate diagnoses and mobile activity | Yes | Yes |
| View account names on recent diagnoses | Yes | No (anonymized) |
| Edit drafts for the seven-class library | Yes | Yes |
| Publish a draft to the public library | Yes | No |
| Invite staff or change roles | Yes | No |
| View the management audit log | Yes | No |

Initial staff accounts must already be email-verified in Firebase and assigned roles in the backend database. No password is stored in repository code.

## Content flow

The management editor only accepts the seven slugs in `seven_class_model.CLASSES`. Employees save drafts; an Admin publishes a draft. Public `GET /api/disease-library` merges the published text over the bundled library JSON. Both the React library page and Flutter guide read that API. An unpublished draft never changes public content.

The Flutter guide fetches on app start. Close and reopen the app to see newly published text in an already installed version. A guide content edit does not require a new IPA. The diagnosis model and structured severity-specific IPM response remain separate from this guide editor.

## Mobile release visibility

New Flutter builds report iOS/Android and the native app version when an authenticated session opens and send platform/version headers on API calls. The Admin/Employee mobile tab summarizes the 500 latest activity events. No device identifier or location is collected. Previously installed builds cannot report their version until they receive an IPA built with the telemetry code. This dashboard observes adoption; it cannot install or update an iOS app remotely. With the current unsigned sideload workflow, app code changes require building a new IPA and installing it on the iPhone.

## Local checks

- `cd frontend && npm run build && npm run lint`
- `cd backend && python -m tests.test_admin_workspace`
- With the API running on port 8015: `cd backend && python -m tests.smoke_live_admin`
- The live publish check `python -m tests.smoke_live_publish` writes a temporary marker and restores the public text in a `finally` block.
