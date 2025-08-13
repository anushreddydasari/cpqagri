import smtplib
from email.message import EmailMessage
from typing import Iterable
import os


def send_pdf_via_gmail(
	gmail_user: str,
	app_password: str,
	to_emails: Iterable[str],
	subject: str,
	body: str,
	pdf_bytes: bytes,
	filename: str,
) -> None:
	"""Send a PDF attachment via Gmail SMTP over SSL.

	- Requires a Gmail App Password if 2FA is enabled (recommended).
	- to_emails can be any iterable of email strings.
	"""
	msg = EmailMessage()
	msg["From"] = gmail_user
	msg["To"] = ", ".join([e for e in to_emails if e])
	msg["Subject"] = subject
	msg.set_content(body)
	msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

	with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
		smtp.login(gmail_user, app_password)
		smtp.send_message(msg)


def send_gmail_pdf_env(
	to_emails: Iterable[str],
	subject: str,
	body: str,
	pdf_bytes: bytes,
	filename: str,
	gmail_user: str | None = None,
	app_password: str | None = None,
) -> None:
	"""Send PDF via Gmail using provided creds or environment variables (GMAIL_USER/GMAIL_APP_PW)."""
	user = gmail_user or os.environ.get("GMAIL_USER")
	pw = app_password or os.environ.get("GMAIL_APP_PW")
	if not user or not pw:
		raise ValueError("Gmail user/app password not provided. Set fields or env vars GMAIL_USER/GMAIL_APP_PW.")
	send_pdf_via_gmail(user, pw, to_emails, subject, body, pdf_bytes, filename)


