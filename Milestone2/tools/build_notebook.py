"""Builds Milestone2/Milestone2_FranchiseOps.ipynb from the files in Milestone2/app.

The notebook is a GENERATED file: edit the source files, then run

    python Milestone2/tools/build_notebook.py

Every file becomes one `%%writefile` cell (so Colab re-creates the project), the vendor JavaScript travels as one base64 archive, and the last
cells start the server and print the link. Outputs are empty and no secret is written: secrets are read from Colab Secrets at run time."""
import base64, io, json, os, sys, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "..", "app")
OUT = os.path.join(HERE, "..", "Milestone2_FranchiseOps.ipynb")
SKIP_DIRS = {"__pycache__", "runtime_data", "vendor"}
SKIP_FILES = {"server.log", ".env"}

def lines(s): return s.splitlines(keepends=True)
def code(src): return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(src)}
def md(src): return {"cell_type": "markdown", "metadata": {}, "source": lines(src)}

def project_files():
    out = []
    for root, dirs, files in os.walk(APP):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f in SKIP_FILES or f.endswith((".pyc", ".db", ".log")): continue
            rel = os.path.relpath(os.path.join(root, f), APP).replace(os.sep, "/")
            out.append(rel)
    return sorted(out, key=lambda r: (r.startswith("static/"), r))          # Python modules first, then the front end

def vendor_bundle():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t: t.add(os.path.join(APP, "static", "vendor"), arcname="vendor")
    b = base64.b64encode(buf.getvalue()).decode()
    return "\n".join("'" + b[i:i + 100] + "'" for i in range(0, len(b), 100))

INTRO = """# FranchiseOps AI - Milestone 2

A multi-user franchise operations platform: **FastAPI + SQLite + JWT + RBAC**, six working agents and a SQL-only AI Copilot.

**How to run:** add the secrets below in the Colab sidebar (key icon, *Notebook access* ON), then **Runtime -> Run all**. The last cell prints **Open the app** (an ngrok link) and a backup Colab link.

| Secret | Used for |
|---|---|
| `JWT_SECRET` | signing login tokens (required) |
| `ADMIN_PASSWORD` | password of the first Admin account (required) |
| `ADMIN_EMAIL_ID` | e-mail of the first Admin (optional, default `admin@infosys.com`) |
| `EMAIL_ADDRESS`, `EMAIL_PASSWORD` | Gmail sender and app password for password-recovery codes (from Milestone 1) |
| `NGROK_AUTHTOKEN` | the public link (recommended: Colab's own link is sometimes blocked) |

Sign in as `admin` (or the Admin e-mail) with your `ADMIN_PASSWORD`. Everyone else creates an account on the sign-up page and picks their own role; an Admin can promote or demote them in the Admin Dashboard.
Never type a password or token into a cell."""

SECRETS = '''# Colab Secrets -> environment variables (the server runs as a separate process and cannot read Colab Secrets itself)
import os
NAMES = ["JWT_SECRET", "ADMIN_PASSWORD", "ADMIN_EMAIL_ID", "EMAIL_ADDRESS", "EMAIL_PASSWORD", "NGROK_AUTHTOKEN"]
try:
    from google.colab import userdata
    for n in NAMES:
        try:
            v = userdata.get(n)
        except Exception:
            v = None
        if v:
            os.environ[n] = str(v).strip(); print(f"[OK]      secret {n} is set")
        else:
            print(f"[MISSING] secret {n}" + ("  <- required" if n in ("JWT_SECRET", "ADMIN_PASSWORD") else ""))
except ImportError:
    print("Not running in Colab: using the environment variables that are already set.")
if not os.environ.get("ADMIN_PASSWORD"):
    print("\\nNo ADMIN_PASSWORD secret: the server will create a random Admin password and print it in the server log (server.log).")'''

RUN = '''import os, subprocess, sys, time, urllib.request
os.chdir('/content/app')
os.environ['APP_KIND'] = 'Franchise'
os.environ['RATE_LIMIT_OFF'] = '1'
subprocess.run('fuser -k 8000/tcp', shell=True, capture_output=True)
log = open('/content/app/server.log', 'w')
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server:app', '--host', '0.0.0.0', '--port', '8000'], stdout=log, stderr=log, cwd='/content/app')
for _ in range(90):
    try:
        urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2); print('FranchiseOps AI is running'); break
    except Exception: time.sleep(2)
else:
    print(open('/content/app/server.log').read()[-3000:])'''

OPEN = '''import os
from IPython.display import HTML, display
links = []
# 1) ngrok: a normal public https link that works in any browser (Colab's own link is often blocked or answers 404)
try:
    from pyngrok import ngrok
    token = os.environ.get('NGROK_AUTHTOKEN')
    if not token:
        from google.colab import userdata
        token = userdata.get('NGROK_AUTHTOKEN')
    token = (token or '').strip()
    ngrok.kill()
    from pyngrok import conf
    conf.get_default().auth_token = token          # used when ngrok starts
    try:
        ngrok.set_auth_token(token)
    except Exception as e:                           # pyngrok raises here even when ngrok saved the token, so carry on and connect
        print('ngrok token note (usually harmless):', str(e)[:90])
    links.append(("Open the app", ngrok.connect(8000).public_url, "ngrok link. If ngrok shows a notice page, click Visit Site."))
except Exception as e:
    print('ngrok link unavailable (add the NGROK_AUTHTOKEN secret):', e)
# 2) Colab's own proxy link as a backup
try:
    from google.colab import output
    links.append(("Backup: Colab link", output.eval_js("google.colab.kernel.proxyPort(8000, {'cache': false})"), "Works only in a browser signed in to the same Google account."))
except Exception as e:
    print('Colab proxy link unavailable:', e)
for label, url, note in links:
    display(HTML(f'<p><a href="{url}" target="_blank" style="font-size:18px">{label}</a><br><small>{url}<br>{note}</small></p>'))'''

def build():
    cells = [md(INTRO),
             code("!pip install -q fastapi 'uvicorn[standard]' python-multipart pandas numpy scikit-learn scipy matplotlib vaderSentiment requests pyngrok bcrypt pyjwt pdfplumber"),
             code("import os\nos.makedirs('/content/app/static', exist_ok=True)\nos.chdir('/content/app')"),
             code(SECRETS)]
    for rel in project_files():
        with open(os.path.join(APP, rel), encoding="utf-8", newline="") as f: body = f.read().replace("\r\n", "\n")
        if not body.endswith("\n"): body += "\n"
        cells.append(code(f"%%writefile /content/app/{rel}\n{body}"))
    cells.append(code("import base64, io, tarfile\nB64 = (\n" + vendor_bundle() + "\n)\ntarfile.open(fileobj=io.BytesIO(base64.b64decode(B64)), mode='r:gz').extractall('/content/app/static')\nprint('vendor files ready')"))
    cells += [code(RUN), code(OPEN)]
    nb = {"cells": cells, "metadata": {"colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 0}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f: json.dump(nb, f, indent=1, ensure_ascii=False); f.write("\n")
    print(f"wrote {os.path.normpath(OUT)}: {len(cells)} cells, {len(project_files())} files, {os.path.getsize(OUT) // 1024} KB")

if __name__ == "__main__":
    build()
