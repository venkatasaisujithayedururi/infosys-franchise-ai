# FranchiseOps AI: Milestone 2

Infosys Springboard Internship 7.0, Batch 4. **Milestone 2 turns the single-operator FranchiseOps AI demo into a multi-user product**: the Milestone 1 login is attached, every person has a role, an Admin manages users and roles, the Copilot answers 23 more kinds of questions from SQL, and the whole front end was redesigned.

**Stack:** FastAPI, SQLite, JWT (PyJWT), bcrypt, role-based access control, Google Colab, ngrok. The Copilot uses SQL only: no language model, no invented numbers.

| What | Where |
|---|---|
| Colab notebook (run this) | [`Milestone2_FranchiseOps.ipynb`](Milestone2_FranchiseOps.ipynb) |
| Source files | [`app/`](app) (the notebook is generated from them: `python Milestone2/tools/build_notebook.py`) |
| Access control | [`app/rbac.py`](app/rbac.py), [`docs/RBAC.md`](docs/RBAC.md) |
| Login, users, admin API | [`app/accounts.py`](app/accounts.py) |
| Copilot question patterns | [`app/intents.py`](app/intents.py) |
| Tests | [`tests/`](tests): 266 tests |
| Screenshots | [`screenshots/`](screenshots) |

## Team

| Member | Area | What this area delivers in the final product |
|---|---|---|
| **Nishanth** | RBAC | The five roles and the page access matrix, **server-side 403** on every page and action, and the one-outlet scope for Store Manager and Staff (`app/rbac.py`). Also integrated the parts into one application, wrote the automated tests and the notebook build, and the documentation. |
| **Akshay** | UI / UX | The redesigned interface: login, sign-up, recovery, profile and admin screens, light and dark themes, phone layout, loading and error states (`app/static/`). |
| **Sidhesh** | Auth and security | Sign-up, login, JWT sessions, bcrypt password hashing, lock after 5 wrong passwords, and password recovery by e-mail code and by security question (`app/accounts.py`). |
| **Sujitha** | Admin dashboard and profile | The Admin Dashboard (users table, add, delete with confirmation, promote and demote, lock and unlock, activity log, KPI cards, privilege table) and the Profile page (details, photo, change username and password, security question). |
| **Varsha** | Copilot fine-tuning and agents | The Copilot's 23 SQL question patterns with spelling tolerance, the SQL and row count under every answer, the polite fallback with three valid questions, and the six agent pages (`app/intents.py`). |

---

## 1. How to run

### In Google Colab (recommended)

1. Open `Milestone2_FranchiseOps.ipynb` in [Google Colab](https://colab.research.google.com/).
2. In the left sidebar open **Secrets** (key icon) and add these. Turn **Notebook access** ON for each. **Never type a password, token or key into a cell.**

| Secret | Used for |
|---|---|
| `JWT_SECRET` | Signs the login tokens. **Required.** Make it long and random. |
| `ADMIN_PASSWORD` | Password of the first Admin account. **Required.** |
| `ADMIN_EMAIL_ID` | E-mail of the first Admin (optional, default `admin@infosys.com`). |
| `EMAIL_ADDRESS`, `EMAIL_PASSWORD` | Gmail sender and 16-character app password for the password-recovery code (from Milestone 1). |
| `NGROK_AUTHTOKEN` | Fallback public link if Colab blocks the first one. |

3. **Runtime -> Run all.** The last cell prints **Open the app** (a Colab link). If Colab blocks it, the ngrok link is printed instead.
4. Sign in as **`admin`** (or the Admin e-mail) with your `ADMIN_PASSWORD`. Everyone else uses **Create an account** and picks their own role.

If `ADMIN_PASSWORD` is not set, the server creates a random one and prints it in `server.log` (nothing is hard-coded).
If Gmail is not configured, the recovery code is printed in `server.log` instead of being e-mailed.

### On your own computer

```bash
pip install fastapi "uvicorn[standard]" python-multipart pandas numpy scikit-learn scipy vaderSentiment requests bcrypt pyjwt
cd Milestone2/app
APP_KIND=Franchise JWT_SECRET=<long random string> ADMIN_PASSWORD=<your password> uvicorn server:app --port 8000
```

Open http://localhost:8000.

---

## 2. Login, sign-up and recovery (Milestone 1, now in FastAPI)

Routes: `POST /api/auth/signup`, `/login`, `/forgot`, `/verify`, `/reset`, `/security-question`, `/reset-with-answer`, `/logout` and `GET /api/auth/options`.

| Rule | How it works |
|---|---|
| Users table | SQLite table `users`: email, username, password hash, role, outlet, locked, created, last login. |
| Passwords | Hashed with **bcrypt**. A password or hash is never returned or displayed. |
| Sessions | A **JWT** (signed with `JWT_SECRET`) is sent in the `Authorization: Bearer` header on every API call. The live status stream also accepts the login cookie, because browsers cannot add a header to it. |
| `user_of(request)` | Reads the token, checks the user still exists and is **not locked**, and returns the real user. The role, outlet and lock flag are read from the database **on every request**, so a promotion, demotion or lock takes effect immediately. `localuser.py` was deleted. |
| Same error | An unknown user and a wrong password both answer *"Invalid email/username or password."* |
| Lockout | **5 wrong passwords lock the account.** Only an Admin can unlock it, and a password reset never unlocks it. The last active Admin is never auto-locked. |
| Email rule | At least 2 letters before `@`, 2 between `@` and the dot, 2 after it (from Milestone 1). |
| Password rule | At least 8 characters with an upper-case letter, a lower-case letter, a number and a special character; the two fields must match. |
| Recovery (two ways) | On *Forgot password* enter your **e-mail or username**, then either **(1)** get a **6-digit code by e-mail** (valid 5 minutes, works once, a new one after 60 seconds) or **(2)** **answer your security question**. **3 wrong codes (or 3 wrong answers) pause that route for 15 minutes.** Changing a password signs out the other sessions. |
| Locked accounts | A locked account **cannot** get a code, see its question or reset a password: the recovery screens stop with "This account is locked. Contact an administrator." |
| Security question | Chosen at sign-up from the Milestone 1 list of five, with an answer that is stored scrambled (bcrypt) and never shown. Capital letters and extra spaces do not matter. An Admin-created account sets its question in the Profile page. |
| Formatted e-mail | The code arrives in a branded HTML e-mail (large digit boxes, expiry, a "did not ask for this?" note) with a plain-text version. |

### Role is chosen at sign-up, Admin is not

The sign-up page asks for **your role**: Franchise Owner, Store Manager, Staff or Auditor, plus a **security question and answer**. A Store Manager or Staff member also picks their **outlet**. **Admin is not offered and the server refuses it**: only an Admin can promote someone to Admin. Anyone can be promoted or demoted later in the Admin Dashboard.

### Milestone 1 features carried over

| Milestone 1 feature | In Milestone 2 |
|---|---|
| Direct registration with username, e-mail, password, confirm password, security question and answer | Sign-up page (plus role and outlet) |
| Sign in with **username or e-mail**; generic error messages | Login page |
| JWT session; secure sign-out | Bearer token; **Sign out** button |
| Forgot password, two routes: security question and e-mail code (look-up by username or e-mail) | Forgot-password screens |
| 3 wrong codes pause recovery for 15 minutes; code lives 5 minutes; 60 second resend | Same limits |
| Strict validation: no empty fields, e-mail rule (2 + 2 + 2), password rule, confirmation | Same rules, on the page and on the server |
| User dashboard: welcome banner, profile details, registration date, active session status | **Profile page** (welcome banner, session expiry, joined date) |
| Admin console listing users, never showing hashes | **Admin Dashboard**, now with full user management |
| Secrets only in Colab Secrets; salted bcrypt hashes | Same |
| Automated tests | `tests/` |

---

## 3. Roles and privileges (RBAC)

Five roles. All rules live in one file, [`app/rbac.py`](app/rbac.py), and are **enforced on the server**: hiding a menu entry is only a convenience, and a user who types `/api/page/<id>` directly gets **403**. The same table is shown in the Admin Dashboard (generated from the same code, so it can never differ).

| Role | Copilot | Workforce | Outlets | Inventory | Marketing | Sentiment | Audit | Run agents | Users |
|---|---|---|---|---|---|---|---|---|---|
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Franchise Owner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Store Manager | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Staff | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Auditor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

Every role also has the **Profile** page. The Auditor is strictly **read-only**.

**Outlet scope.** A **Store Manager** and **Staff** member see **one outlet only** (`users.outlet`). Every page, KPI, ticket list, live number, detail view and Copilot answer is filtered by it, and a request that names another outlet is refused with 403. Chain-wide extras (agent scores and summaries, sentiment issue categories, stock-transfer suggestions that list other outlets) are hidden from these roles. Writes (a review, an inspection) must be for their own outlet.

**Fail closed.** An unknown role, or a Store Manager or Staff account with no outlet, gets 403 everywhere.

| Capability | Meaning | Admin | Owner | Manager | Staff | Auditor |
|---|---|:-:|:-:|:-:|:-:|:-:|
| `copilot` | Copilot and saved chats | ✓ | ✓ | ✓ | ✓ | ✓ |
| `view` | Agent pages and outlet detail | ✓ | ✓ | ✓ |  | ✓ |
| `run` | Run the agents | ✓ | ✓ |  |  |  |
| `resolve` | Log an inspection (own outlet for a Manager) | ✓ | ✓ | ✓ |  |  |
| `review` | Add a customer review (own outlet for a Manager) | ✓ | ✓ | ✓ |  |  |
| `users` | Admin Dashboard | ✓ |  |  |  |  |
| `profile` | Own profile | ✓ | ✓ | ✓ | ✓ | ✓ |

Team decisions you can change in `rbac.py`: the Franchise Owner sees all outlets; a Store Manager may log inspections and reviews for their own outlet; salary and personal data are hidden from Staff and Auditor in the Copilot.

---

## 4. Profile page

* **Welcome banner** with your role, outlet, member-since date and the **session status** (when your login expires, in IST).
* **Profile photo** for every role, Admin included: upload a PNG, JPEG or WebP; it is cropped to a small square, checked on the server (real image, size limit) and shown in the sidebar and in the Admin's user table. Remove it any time.
* Username, e-mail, role, outlet, joined date and last login (never the password hash).
* **Change username**, **change password** (the current password is asked first and the Milestone 1 password rules apply), and **set or change your security question**.

## 5. Admin Dashboard

Only the Admin role can open it, and every route behind it needs the `users` capability.

* **KPI cards:** total users, active users, locked users, roles in use; plus **users per role**.
* **Users table:** e-mail, username, role, outlet, status (Active / Locked), created, last login (all times in **IST**). Search box and each person's photo.
* **Add user:** e-mail, username, temporary password, role (and outlet for one-outlet roles). The sign-up rules apply.
* **Promote / demote:** a role drop-down per user. **Choosing a one-outlet role (Store Manager or Staff) always asks which outlet.** The change is effective on the person's very next request.
* **Lock / unlock:** a locked user cannot sign in and their existing token stops working immediately.
* **Delete** with a confirmation step.
* **Protections:** an Admin cannot delete, lock or change the role of **their own** account, and **the last Admin can never be removed**, locked or demoted.
* **Activity log:** every admin action (who, what, when, target) in the `audit_log` table; the latest 50 are shown.
* **Roles and privileges:** the permission table above.

---

## 6. AI Copilot (Step 7)

The Copilot understands greetings and **23 more question patterns**. Each pattern is an *intent* in [`app/intents.py`](app/intents.py) that runs **one fixed, read-only, parameterised SQL query**; the answer is built from the rows that query returns, so **nothing is invented**. Every answer shows **the SQL that produced it** ("Show the exact query") and **the number of rows**.

* **Spelling mistakes and other wordings:** words are normalised (store/shop/branch → outlet, employees/workers → staff, csat → satisfaction ...) and near-misses are corrected (`custmer`, `revanue`, `campain`, `reoder`, `audt`).
* **Outside the data:** a polite reply ("Sorry, I can only answer from the franchise database ...") with **three valid questions** to try. Every suggestion is checked by a test to be answerable.
* **RBAC:** the Copilot reads only what the role may see: one outlet for Store Manager and Staff (a question about another outlet is refused, and any answer that would mention one is blocked), and staff names are hidden from Staff and Auditor.

### The 23 new question patterns (tested, with the real answers)

The numbers come from the generated demo data and change with every fresh run.

| # | Question (as typed) | Intent | Answer from the database | Rows |
|--:|---|---|---|--:|
| 1 | Which outlet has the lowest customer satisfaction? | `lowest_csat` | OUT-047 (Franchise Outlet 047, Kochi) has the lowest customer satisfaction: 2.92 out of 5. | 5 |
| 2 | Which outlet has the best customer satisfaction? | `highest_csat` | OUT-009 (Franchise Outlet 009, Coimbatore) has the highest customer satisfaction: 4.89 out of 5. | 5 |
| 3 | Which outlet has the lowest revenue? | `lowest_revenue` | OUT-074 (Franchise Outlet 074) has the lowest revenue: 1,078,637. | 5 |
| 4 | Which outlet has the highest revenue? | `highest_revenue` | OUT-040 (Franchise Outlet 040) has the highest revenue: 7,588,463. | 5 |
| 5 | Who works the most overtime? | `highest_overtime` | The highest overtime is 44.8 hours (staff STF-0083, OUT-018). Top 10 below. | 10 |
| 6 | Which outlet has the most staff? | `highest_staff_count` | OUT-034 has the most staff: 19. | 5 |
| 7 | How many staff does OUT-010 have? | `staff_count` | OUT-010 has 10 staff members. | 1 |
| 8 | Which employees have a high attrition risk? | `high_attrition` | 229 employees have a high attrition risk (60% or more). The 10 highest are below. | 10 |
| 9 | How many inventory items need reordering? | `reorder_count` | 407 inventory items need reordering (stock at or below the reorder level). | 1 |
| 10 | List inventory items below reorder level | `below_reorder` | 407 inventory items are at or below their reorder level. The 15 most urgent are below. | 15 |
| 11 | Which inventory items have the highest stockout risk? | `stockout_risk` | Highest stock-out risk: Flour at OUT-037 (82%). Top 10 below. | 10 |
| 12 | Which campaign has the worst ROI? | `worst_campaign_roi` | The campaign with the lowest ROI is Campaign 020-1 (CMP-020-1, Social, OUT-020): ROI 1.22x. | 5 |
| 13 | What is the average campaign ROI? | `average_campaign_roi` | The average campaign ROI is 3.33x across 268 campaigns. Best channel: Social Media (4.15x). | 9 |
| 14 | Which campaign has the best ROI? | `best_campaign_roi` | The campaign with the best ROI is Campaign 027 (CMP-027, Local Print, OUT-049): ROI 5.40x. | 5 |
| 15 | Which outlet has the most negative reviews? | `most_negative_reviews` | OUT-046 has the most negative reviews: 8. | 5 |
| 16 | Show negative reviews this week | `negative_reviews` | 160 negative reviews (rating 1-2) in the last week of data. The latest 10 are below. | 10 |
| 17 | What is the average customer rating? | `average_rating` | The average customer rating is 3.84 out of 5, from 1,438 reviews. | 1 |
| 18 | Show failed audits | `failed_audits` | 3 audits failed (score below 60). The latest 3 are below. | 3 |
| 19 | Which outlet has the most audit violations? | `highest_violations` | OUT-012 has the most audit violations: 16 across 4 audits. | 5 |
| 20 | Which outlet has the highest operating costs? | `highest_operating_cost` | OUT-043 (Franchise Outlet 043) has the highest operating costs: 6,045,952. | 5 |
| 21 | Show critical open tickets | `open_critical_tickets` | 94 critical tickets are open. The 10 most severe are below. | 10 |
| 22 | Which purchase orders are still pending? | `pending_purchase_orders` | 674 purchase orders are still on their way. The 10 arriving first are below. | 10 |
| 23 | What were the total sales in the last 7 days? | `sales_last_7_days` | Sales over the last 7 days of data: 159,188,184. Best day 2026-11-02 (75,248,711). | 7 |
| 24 | How many outlets are there? | `total_outlets` | You can see 120 outlets in the franchise. | 1 |

### Spelling mistakes and different wordings (tested)

| Question as typed | Understood as | Answer |
|---|---|---|
| Which outlet has the lowest custmer satisfation? | `lowest_csat` | OUT-047 (Franchise Outlet 047, Kochi) has the lowest customer satisfaction: 2.92 out of 5. |
| Which outlet has the highest revanue? | `highest_revenue` | OUT-040 (Franchise Outlet 040) has the highest revenue: 7,588,463. |
| How many employes are in outlet OUT-001? | `staff_count` | OUT-001 has 13 staff members. |
| Which campain has the best ROI? | `best_campaign_roi` | The campaign with the best ROI is Campaign 027 (CMP-027, Local Print, OUT-049): ROI 5.40x. |
| How many inventry items need reoder? | `reorder_count` | 407 inventory items need reordering (stock at or below the reorder level). |
| show negative feeback this week | `negative_reviews` | 160 negative reviews (rating 1-2) in the last week of data. The latest 10 are below. |
| show failing audt results | `failed_audits` | 3 audits failed (score below 60). The latest 3 are below. |
| which shop has the most violatons | `highest_violations` | OUT-012 has the most audit violations: 16 across 4 audits. |
| who works the most overtime | `highest_overtime` | The highest overtime is 44.8 hours (staff STF-0083, OUT-018). Top 10 below. |
| which people are likely to quit | `high_attrition` | 229 employees have a high attrition risk (60% or more). The 10 highest are below. |

### Same question, different role

| Role | Question | Answer |
|---|---|---|
| Store Manager / Staff (OUT-010) | How many staff does OUT-010 have? | OUT-010 has 10 staff members. |
| Store Manager / Staff (OUT-010) | Which outlet has the lowest customer satisfaction? | Rankings compare outlets across the chain, so for your role this shows OUT-010 only. OUT-010 (Franchise Outlet 010, Ahmedabad) has the lowest customer |
| Store Manager / Staff (OUT-010) | Show failed audits | No failed audits (score below 60) found for OUT-010. |
| Store Manager / Staff (OUT-010) | Which campaign has the best ROI? | Rankings compare outlets across the chain, so for your role this shows OUT-010 only. The campaign with the best ROI is Campaign 009 (CMP-009, Social M |

---

## 7. Design (Step 8)

Every time on screen is shown in **Indian Standard Time (IST)**. A consistent **midnight navy and teal** colour theme in light mode (navy sidebar, white cards on cool slate, teal accents, amber for warnings), readable tables, responsive layout (a phone gets a bottom navigation bar), a **dark-mode switch**, loading states, and clear error messages (for example **"Access denied (403)"**). Designed login, sign-up, recovery, profile and admin pages.

---

## 8. Tests

```bash
pip install fastapi pandas numpy scikit-learn scipy vaderSentiment httpx python-multipart bcrypt pyjwt pytest
python -m pytest Milestone2/tests -v
```

**266 tests**, all passing:

| File | Covers |
|---|---|
| `test_rbac.py` | Every role against every page and action, allowed and denied (403). The expected matrix is **copied from the instructions**, not imported from `rbac.py`. Outlet scope, Copilot leak checks, unknown role, metrics endpoint. |
| `test_accounts.py` | **Real accounts, no simulated users:** sign-up validation (including the security question), no Admin sign-up, login, same error, 5-attempt lock, immediate effect of a lock, both recovery routes (look-up by username or e-mail, 3-try pause, locked accounts refused, unknown accounts indistinguishable), the formatted e-mail, profile and profile photo, IST time stamps, every Admin action, last-Admin protection, activity log. |
| `test_copilot.py` | Each of the 23 patterns, answers checked against independent queries, spelling and wording, SQL and row count, polite fallback with three answerable suggestions, scope and PII masking. |

To test by hand with real accounts: create one account per role on the sign-up page, sign in as each, open each page and try each action, and compare with the table in section 3.

---

## 9. Screenshots

All taken from the running application, signed in as the role named.

| | |
|---|---|
| **Login** ![Login](screenshots/01_login_page.png) | **Sign-up (role and outlet)** ![Sign-up](screenshots/02_signup_page.png) |
| **Forgot password: enter the code** ![Code](screenshots/21_forgot_password_code.png) | **Account locked after 5 wrong passwords** ![Locked](screenshots/22_account_locked.png) |

**Forgot password by security question**

![Security question](screenshots/21b_security_question_recovery.png)

**A locked account cannot start recovery: it is told so and never reaches the code or answer screen**

![Locked recovery](screenshots/22b_locked_account_recovery_blocked.png)

**Profile page: welcome banner with session status, profile photo, security question**

![Profile](screenshots/03_profile_page.png)

**Admin Dashboard: users table, KPI cards, role drop-downs, activity log**

![Admin](screenshots/04_admin_dashboard.png)

**Choosing the outlet when promoting or demoting to a one-outlet role**

![Outlet dialog](screenshots/05a_choose_outlet_dialog.png)

**Delete needs a confirmation**

![Delete](screenshots/05_admin_delete_confirmation.png)

**Role matrix and activity log in the Admin Dashboard**

![Matrix](screenshots/06_role_privilege_table.png)

**A denied (403) action: Staff opening the Audit page**

![403 Staff](screenshots/20_denied_403_staff.png)

**A denied (403) action: Store Manager opening Marketing**

![403 Manager](screenshots/20_denied_403_manager.png)

**An allowed page for a Store Manager: Outlets, own outlet only**

![Store Manager](screenshots/18_store_manager_own_outlet_only.png)

**AI Copilot: a greeting**

![Greeting](screenshots/08_copilot_greeting.png)

**AI Copilot: exact answers from SQL, with the exact query and the row count**

![Copilot](screenshots/07_copilot_exact_answer.png)

**Copilot as a Staff member: own outlet only**

![Staff Copilot](screenshots/19_staff_copilot_own_outlet.png)

**The six agents**

| | |
|---|---|
| **Agent 1: Workforce** ![Workforce](screenshots/09_agent_workforce.png) | **Agent 2: Outlets** ![Outlets](screenshots/10_agent_outlets.png) |
| **Agent 3: Inventory** ![Inventory](screenshots/11_agent_inventory.png) | **Agent 4: Marketing** ![Marketing](screenshots/12_agent_marketing.png) |
| **Agent 5: Sentiment** ![Sentiment](screenshots/13_agent_sentiment.png) | **Agent 6: Audit** ![Audit](screenshots/14_agent_audit.png) |

**Dark mode and the phone layout**

| | |
|---|---|
| ![Dark](screenshots/15_dark_mode.png) | ![Phone](screenshots/17_phone_layout.png) |
