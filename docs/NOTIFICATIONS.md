# Notification delivery

In-app notifications remain available without browser push. Farmer interest, purchase requests/status changes, FPO submissions and FPO acceptance now record a notification and an optional delivery queue in the same database transaction.

## Setup

1. Use the existing Firebase project and backend service account. Enable its Cloud Messaging API and set public `VITE_FIREBASE_VAPID_KEY` and `VITE_FIREBASE_MESSAGING_SENDER_ID` in the frontend build environment.
2. Apply the additive `backend/migrations/002_push_deliveries.sql` to an existing PostgreSQL database. `init_db.py` also creates this new table when absent. It does not delete or rebuild any existing table or backfill sends for old notifications.
3. Serve the frontend over HTTPS. A signed-in user explicitly chooses **Enable notifications** in their profile and grants browser permission. Only that account's registered devices receive its events.
4. The existing FastAPI service runs the queue loop while active when database/Firebase configuration exists. `PUSH_DELIVERY_ENABLED=false` pauses push delivery; in-app notifications continue. The default poll interval is 15 seconds. A sleeping/stopped backend cannot deliver until it resumes; no separate paid worker is provisioned.

## Behavior

- **Mark as read** updates only the owning account's notification. Already-read events awaiting delivery are cancelled.
- **Disable notifications** removes this device's server subscription and revokes its Firebase browser token. Signing out attempts the same cleanup before Firebase sign-out. If services are offline, cleanup is best effort; lock-screen messages contain only a generic account-update notice.
- Delivery claims use PostgreSQL row locks and a ten-minute lease. Network sending happens after committing the claim. A crashed worker's lease can be retried.
- Transient failures back off from 60 seconds up to one hour, with at most six attempts. Unregistered Firebase tokens are removed. Permanent argument/permission failures stop retries. Events over seven days old are cancelled.
- Delivery is **at least once**, not exactly once: a crash after Firebase accepts a send can cause a retry. A stable notification tag replaces repeated visible notifications for the same event. No contact details or sale terms are put in push payloads, logs or the lock screen.
- Clicking a notification opens the account profile through the existing role-aware routing. It never follows a destination supplied by the push message.

Real Firebase delivery still needs staging verification: grant permission, create a permitted account event, receive the notification, open it, mark it read, disable notifications and sign out. Automated tests use a mocked sender and never contact Firebase or notify real people. SQLite tests do not validate PostgreSQL worker concurrency.

References: [Firebase Admin sending](https://firebase.google.com/docs/cloud-messaging/send/admin-sdk), [token management](https://firebase.google.com/docs/cloud-messaging/manage-tokens), [Python messaging API](https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging).
