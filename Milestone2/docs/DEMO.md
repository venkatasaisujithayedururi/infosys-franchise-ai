# Presentation script (about 8 minutes)

Before you start: add the Colab Secrets, run all cells, open the app link. Have a second browser window (or a private window) ready.

1. **Sign-up with a role (RBAC at sign-up).** *Create an account* -> pick **Store Manager** and an outlet. Point out that **Admin is not in the list**. Create a second account as **Staff**.
2. **Login rules.** Wrong password -> *"Invalid email/username or password."* (same text for an unknown user). Five wrong passwords lock the account.
3. **Roles in action.** Sign in as the Staff user: only **Copilot** and **Profile** in the menu. Sign in as the Store Manager: no **Marketing**, and **Outlets shows only their own outlet**.
4. **403 on the server.** As the Staff user, type `/api/page/audit` in the address bar of a new tab: **403 Forbidden**. (The menu hides it, the server enforces it.)
5. **Admin Dashboard.** Sign in as **admin**. Show the KPI cards, the users table, **promote the Staff user to Franchise Owner** with the drop-down, and show that the other window gets new pages on its next click (no new login). **Lock** a user and show they are signed out at once. **Delete** needs a confirmation. Try to delete or lock **yourself**: refused. Show the **Activity log** (who, what, when) and the **privilege table**.
6. **Profile.** Change the username; change the password (current password asked first).
7. **Forgot password.** Enter the e-mail -> 6-digit code arrives by Gmail -> verify -> new password.
8. **AI Copilot.** *hello*; then *Which outlet has the lowest customer satisfaction?*; open **Show the exact query** and point at the **row count**. Try a typo: *which campain has the best ROI?* and an out-of-scope question (*what is the weather in Paris?*): polite answer with three valid questions. As the Store Manager, ask about **another outlet**: refused.
9. **Design.** Click **Dark mode**; shrink the window to show the phone layout.

If something goes wrong: the numbers in the Copilot come from generated demo data, so they differ from run to run; the recovery code is also printed in `server.log` if Gmail is not configured.
