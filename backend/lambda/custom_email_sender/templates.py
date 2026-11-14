"""
COGNITO-EMAIL-1 — Branded email templates for the Cognito Custom Email Sender.

Design: dev-docs/architecture-design/batch-designs/batch-cognito-email-1-design.md
        §F (templates table) + §G.5 (inline, platform-branded, tracking-free).

Three flows, each with HTML + plaintext:
  - verification_code  — SignUp, ResendCode, VerifyUserAttribute, UpdateUserAttribute
  - forgot_password    — ForgotPassword
  - admin_invite       — AdminCreateUser (future-proofing; not exercised by current flows)

Brand tokens mirror the ``team_invite`` template (Arial stack, ``#5B3FF0``).
Inline styles only — no external CSS, no external images. The only link is the
``https://pilotfortrades.com`` footer. The code is rendered large (≥28 px,
letter-spaced, monospace-friendly) so it is scannable at a glance.

These templates are **inline in the Lambda package** (not DB ``email_template``
rows) by deliberate design (design §B): the auth-critical delivery path must not
depend on RDS availability, and Cognito auth emails are platform-owned (not
tenant-branded, not tenant-editable).
"""

from dataclasses import dataclass

# ── Brand constants ──────────────────────────────────────────────────────────
_BRAND_COLOR = "#5B3FF0"
_FONT_STACK = "Arial, Helvetica, sans-serif"
_FOOTER_URL = "https://pilotfortrades.com"
_EXPIRY_HINT = "This code expires shortly."

# ── Shared HTML scaffolding ──────────────────────────────────────────────────


def _html_wrapper(title: str, body_inner: str) -> str:
    """Wrap flow-specific body inner HTML in the shared branded scaffolding."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f8;font-family:{_FONT_STACK};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f8;">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;max-width:600px;width:100%;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          <tr>
            <td style="padding:32px 40px 8px 40px;">
              <h1 style="margin:0 0 8px 0;font-size:22px;font-weight:bold;color:{_BRAND_COLOR};font-family:{_FONT_STACK};">Pilot for Trades</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 32px 40px;font-family:{_FONT_STACK};">
{body_inner}
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 24px 40px;border-top:1px solid #eeeeee;font-family:{_FONT_STACK};">
              <p style="margin:16px 0 0 0;font-size:12px;color:#999999;line-height:1.5;">
                This is an automated security email from Pilot for Trades.<br>
                Visit <a href="{_FOOTER_URL}" style="color:{_BRAND_COLOR};text-decoration:none;">{_FOOTER_URL}</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _code_block_html(code: str) -> str:
    """Render the code large, letter-spaced, monospace-friendly (≥28 px)."""
    return f"""\
              <p style="margin:0 0 24px 0;font-size:16px;color:#333333;line-height:1.5;">
                Your verification code is:
              </p>
              <p style="margin:0 0 8px 0;text-align:center;">
                <span style="display:inline-block;font-size:32px;font-weight:bold;letter-spacing:8px;font-family:'Courier New',Courier,monospace;color:{_BRAND_COLOR};background-color:#f4f4f8;padding:16px 24px;border-radius:6px;">{code}</span>
              </p>
              <p style="margin:0 0 24px 0;font-size:13px;color:#999999;text-align:center;">
                {_EXPIRY_HINT}
              </p>"""


# ── RenderedEmail dataclass ──────────────────────────────────────────────────


@dataclass(frozen=True)
class RenderedEmail:
    """The rendered output for one email flow: subject + HTML + plaintext."""

    subject: str
    html: str
    text: str


# ── Flow: verification_code ──────────────────────────────────────────────────

_VERIFICATION_SUBJECT = "Your Pilot for Trades verification code"
_VERIFICATION_TEXT = (
    "Pilot for Trades\n\n"
    "Your verification code is: {code}\n\n"
    f"{_EXPIRY_HINT}\n\n"
    f"Visit {_FOOTER_URL}"
)


def _render_verification_code(code: str, email: str) -> RenderedEmail:
    body_inner = _code_block_html(code)
    html = _html_wrapper(_VERIFICATION_SUBJECT, body_inner)
    text = _VERIFICATION_TEXT.format(code=code)
    return RenderedEmail(subject=_VERIFICATION_SUBJECT, html=html, text=text)


# ── Flow: forgot_password ────────────────────────────────────────────────────

_FORGOT_SUBJECT = "Reset your Pilot for Trades password"
_FORGOT_TEXT = (
    "Pilot for Trades\n\n"
    "We received a request to reset your password. "
    "Use the code below to complete the reset:\n\n"
    "{code}\n\n"
    f"{_EXPIRY_HINT}\n\n"
    "If you didn't request this, ignore this email — your password has not been changed.\n\n"
    f"Visit {_FOOTER_URL}"
)


def _render_forgot_password(code: str, email: str) -> RenderedEmail:
    body_inner = f"""\
              <p style="margin:0 0 24px 0;font-size:16px;color:#333333;line-height:1.5;">
                We received a request to reset your password.
                Use the code below to complete the reset:
              </p>
{_code_block_html(code)}
              <p style="margin:0 0 24px 0;font-size:14px;color:#666666;line-height:1.5;">
                If you didn't request this, ignore this email &mdash; your password has not been changed.
              </p>"""
    html = _html_wrapper(_FORGOT_SUBJECT, body_inner)
    text = _FORGOT_TEXT.format(code=code)
    return RenderedEmail(subject=_FORGOT_SUBJECT, html=html, text=text)


# ── Flow: admin_invite ───────────────────────────────────────────────────────
# Not exercised by current flows (ADR-0011 self-SignUp). Future-proofing per
# design §G.5. The "code" here is the temporary password set by AdminCreateUser.

_ADMIN_INVITE_SUBJECT = "You've been invited to Pilot for Trades"
_ADMIN_INVITE_TEXT = (
    "Pilot for Trades\n\n"
    "You've been invited to join Pilot for Trades.\n\n"
    "Your temporary password is: {code}\n\n"
    "Please sign in and set a new password.\n\n"
    f"{_EXPIRY_HINT}\n\n"
    f"Visit {_FOOTER_URL}"
)


def _render_admin_invite(code: str, email: str) -> RenderedEmail:
    body_inner = f"""\
              <p style="margin:0 0 24px 0;font-size:16px;color:#333333;line-height:1.5;">
                You've been invited to join Pilot for Trades.
              </p>
              <p style="margin:0 0 8px 0;font-size:16px;color:#333333;line-height:1.5;">
                Your temporary password is:
              </p>
              <p style="margin:0 0 8px 0;text-align:center;">
                <span style="display:inline-block;font-size:28px;font-weight:bold;letter-spacing:6px;font-family:'Courier New',Courier,monospace;color:{_BRAND_COLOR};background-color:#f4f4f8;padding:16px 24px;border-radius:6px;">{code}</span>
              </p>
              <p style="margin:0 0 24px 0;font-size:14px;color:#666666;line-height:1.5;">
                Please sign in and set a new password.
              </p>
              <p style="margin:0 0 24px 0;font-size:13px;color:#999999;text-align:center;">
                {_EXPIRY_HINT}
              </p>"""
    html = _html_wrapper(_ADMIN_INVITE_SUBJECT, body_inner)
    text = _ADMIN_INVITE_TEXT.format(code=code)
    return RenderedEmail(subject=_ADMIN_INVITE_SUBJECT, html=html, text=text)


# ── Public render dispatcher ─────────────────────────────────────────────────

# Flow name → renderer. Kept module-level so handler.py can look up by string.
_RENDERERS = {
    "verification_code": _render_verification_code,
    "forgot_password": _render_forgot_password,
    "admin_invite": _render_admin_invite,
}


def render(flow: str, code: str, email: str) -> RenderedEmail:
    """
    Render the email for the given flow.

    Args:
        flow: One of ``verification_code``, ``forgot_password``, ``admin_invite``.
        code: The decrypted code / temporary password.
        email: The recipient email (currently unused in templates but accepted
            for future personalization; kept in the signature per design §F).

    Returns:
        A ``RenderedEmail`` (subject, html, text).

    Raises:
        ValueError: If ``flow`` is not a recognized flow name.
    """
    renderer = _RENDERERS.get(flow)
    if renderer is None:
        raise ValueError(f"Unknown email flow: {flow!r}")
    return renderer(code, email)
