
"""Email CI test results and attach the JSON report."""

import json
import os
import smtplib
import sys
from pathlib import Path
from email.message import EmailMessage


def send_report():
    # Read the generated test report
    report_path = Path("results/report.json")

    if not report_path.exists():
        raise FileNotFoundError(
            f"Test report not found: {report_path}"
        )

    with report_path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    summary = report["summary"]

    # Read SMTP configuration
    smtp_host = os.environ.get("SMTP_HOST", "").strip() or "smtp.gmail.com"
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
    email_to = os.environ.get("EMAIL_TO", "").strip()

    # Validate required settings
    missing = []

    if not smtp_user:
        missing.append("SMTP_USER")

    if not smtp_password:
        missing.append("SMTP_PASSWORD")

    if not email_to:
        missing.append("EMAIL_TO")

    if missing:
        raise ValueError(
            "Missing GitHub Secrets: " + ", ".join(missing)
        )

    # Prepare email content
    lines = [
        f"Repository: {report['repository']}",
        f"Branch: {report['branch']}",
        f"Commit: {report['commit_sha']}",
        f"Pipeline Run: {report['pipeline_run_id']}",
        f"Overall Status: {report['overall_status'].upper()}",
        "",
        f"Total Tests: {summary['total']}",
        f"Passed Tests: {summary['passed']}",
        f"Failed Tests: {summary['failed']}",
        "",
        "Individual Test Results:"
    ]

    for test in report["tests"]:
        lines.append(
            f"- [{test['result'].upper()}] {test['name']}"
        )

        if test.get("failure_message"):
            lines.append(
                f"  Failure: {test['failure_message']}"
            )

    # Create email
    msg = EmailMessage()

    msg["Subject"] = (
        f"[CI {report['overall_status'].upper()}] "
        f"{report['repository']} "
        f"{report['commit_sha'][:7]}"
    )

    msg["From"] = smtp_user
    msg["To"] = email_to

    msg.set_content("\n".join(lines))

    # Attach JSON report
    msg.add_attachment(
        json.dumps(report, indent=2).encode("utf-8"),
        maintype="application",
        subtype="json",
        filename="test-report.json"
    )

    # Connect and send email
    print(f"Connecting to SMTP server: {smtp_host}:{smtp_port}")

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=30
    ) as server:

        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)

    print(f"SUCCESS: Email sent to {email_to}")


if __name__ == "__main__":
    try:
        send_report()
    except Exception as error:
        print(f"EMAIL ERROR: {error}", file=sys.stderr)
        sys.exit(1)
