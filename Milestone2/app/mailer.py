"""One place that sends e-mail (OTP codes, reports, alerts). Gmail SMTP with an app password: set EMAIL_ADDRESS + EMAIL_PASSWORD (Colab secrets or env)."""
import os, ssl, smtplib
from email.message import EmailMessage
def creds(): return os.environ.get("EMAIL_ADDRESS") or os.environ.get("EMAIL_ID") or "", (os.environ.get("EMAIL_PASSWORD") or os.environ.get("EMAIL_APP_PASSWORD") or "").replace(" ", "")
def configured(): a, b = creds(); return bool(a and b)
def send(to, subject, body, attachments=(), html=None):
    """attachments: [(filename, bytes, mimetype)]. Returns (ok, message)."""
    em, pw = creds()
    if not (em and pw): return False, "E-mail is not configured (set EMAIL_ADDRESS and EMAIL_PASSWORD)."
    try:
        m = EmailMessage(); m["Subject"] = subject; m["From"] = em; m["To"] = to; m.set_content(body)
        if html: m.add_alternative(html, subtype="html")
        for fn, data, mt in attachments: m.add_attachment(data, maintype=mt.split("/")[0], subtype=mt.split("/")[1], filename=fn)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=20) as s: s.login(em, pw); s.send_message(m)
        return True, f"Sent to {to}"
    except Exception as e: return False, f"Could not send: {e}"

def otp_text(code, minutes, name=""):
    return (f"Hello {name or 'there'},\n\nYour FranchiseOps AI verification code is {code}.\nIt is valid for {minutes} minutes and works once.\n\n"
            "If you did not ask to reset your password, ignore this e-mail: your password has not been changed.\n\nFranchiseOps AI")
def otp_html(code, minutes, name=""):
    """The verification e-mail: branded header, the code in large spaced digits, the expiry and a safety note (inline styles: e-mail clients ignore style sheets)."""
    import html as _h
    digits = "".join(f'<span style="display:inline-block;min-width:38px;margin:0 3px;padding:12px 0;border-radius:10px;background:#e6f4f1;color:#0f172a;font:700 28px/1 Consolas,Menlo,monospace;text-align:center">{_h.escape(c)}</span>' for c in str(code))
    return f"""<!doctype html><html><body style="margin:0;padding:0;background:#f1f5f9">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:28px 12px"><tr><td align="center">
<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0;font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#0f172a">
<tr><td style="background:#0f172a;padding:22px 28px"><span style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:.2px">FranchiseOps</span><span style="color:#5eead4;font-size:18px;font-weight:700"> AI</span></td></tr>
<tr><td style="padding:30px 28px 8px"><div style="font-size:12px;font-weight:700;letter-spacing:.12em;color:#0f766e;text-transform:uppercase">Password recovery</div>
<h1 style="margin:8px 0 10px;font-size:22px;line-height:1.3;color:#0f172a">Your verification code</h1>
<p style="margin:0 0 6px;font-size:14px;line-height:1.6;color:#334155">Hello {_h.escape(name or 'there')}, use this code to reset your password.</p></td></tr>
<tr><td align="center" style="padding:14px 28px 6px">{digits}</td></tr>
<tr><td style="padding:14px 28px 4px"><p style="margin:0;font-size:14px;line-height:1.6;color:#334155">The code is valid for <b>{int(minutes)} minutes</b> and works only once. Three wrong codes pause recovery for 15 minutes.</p></td></tr>
<tr><td style="padding:18px 28px 28px"><div style="border-left:4px solid #f59e0b;background:#fff8e6;padding:12px 14px;border-radius:6px;font-size:13px;line-height:1.55;color:#7c5a00"><b>Did not ask for this?</b> Ignore this e-mail. Your password has not been changed, and nobody can use the code without your account.</div></td></tr>
<tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:16px 28px;font-size:12px;color:#64748b">Sent by FranchiseOps AI. Never share this code with anyone.</td></tr>
</table></td></tr></table></body></html>"""
