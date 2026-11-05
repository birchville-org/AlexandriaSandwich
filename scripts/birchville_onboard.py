#!/usr/bin/env python3
"""
birchville_onboard.py — Administration CLI for Birchville Onboarding & Staging

Automates user provisioning for Authelia 2FA and AlexandriaSandwich job assignment:
  1. Generates Argon2id password hashes for Authelia users_database.yml.
  2. Creates bilingual invitation email drafts (DE & EN).
  3. Stages and assigns pre-formulated jobs to users.
  4. Inspects and audits staged jobs in data/input/.

Usage:
  python3 scripts/birchville_onboard.py create --username scholar1 --display-name "Dr. Scholar" --email "scholar@example.org"
  python3 scripts/birchville_onboard.py create --username scholar1 --display-name "Dr. Scholar" --email "scholar@example.org" --job boethlingk_sample
  python3 scripts/birchville_onboard.py stage --job boethlingk_sample --user scholar1
  python3 scripts/birchville_onboard.py unstage --job boethlingk_sample
  python3 scripts/birchville_onboard.py list
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent
DATA_INPUT = ROOT / "data" / "input"
DATA_OUTPUT = ROOT / "data" / "output"


def generate_argon2_hash(password: str, synology_host: Optional[str] = "synology.local") -> str:
    """
    Generates an Argon2id hash compatible with Authelia.
    First tries local argon2 library; if unavailable, attempts remote Authelia docker CLI.
    """
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16
        )
        return ph.hash(password)
    except ImportError:
        pass

    # Fallback via SSH to Authelia container on Synology host
    if synology_host:
        try:
            cmd = [
                "ssh", synology_host,
                f'/usr/local/bin/docker exec authelia authelia crypto hash generate argon2 --password "{password}"'
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            for line in res.stdout.splitlines():
                if line.startswith("Digest: "):
                    return line.replace("Digest: ", "").strip()
        except Exception as e:
            sys.stderr.write(f"SSH Authelia hash fallback failed: {e}\n")

    raise RuntimeError(
        "Could not generate Argon2id hash. Please install 'argon2-cffi' locally: pip install argon2-cffi"
    )


def load_job_options(job_id: str) -> Dict[str, Any]:
    options_file = DATA_INPUT / job_id / "job_options.json"
    if options_file.exists():
        try:
            return json.loads(options_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_job_options(job_id: str, opts: Dict[str, Any]) -> None:
    job_dir = DATA_INPUT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    options_file = job_dir / "job_options.json"
    options_file.write_text(json.dumps(opts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stage_job(job_id: str, username: str) -> bool:
    job_dir = DATA_INPUT / job_id
    if not job_dir.exists():
        sys.stderr.write(f"Fehler: Auftrag '{job_id}' existiert nicht unter {DATA_INPUT}\n")
        return False

    opts = load_job_options(job_id)
    opts["assigned_to"] = username
    opts["is_staged"] = True
    save_job_options(job_id, opts)
    return True


def unstage_job(job_id: str) -> bool:
    job_dir = DATA_INPUT / job_id
    if not job_dir.exists():
        sys.stderr.write(f"Fehler: Auftrag '{job_id}' existiert nicht unter {DATA_INPUT}\n")
        return False

    opts = load_job_options(job_id)
    opts["is_staged"] = False
    save_job_options(job_id, opts)
    return True


def render_invitation_email(
    username: str,
    display_name: str,
    email: str,
    password: str,
    job_id: Optional[str] = None
) -> str:
    """
    Renders bilingual invitation email ready to dispatch to user.
    """
    job_section_de = ""
    job_section_en = ""

    if job_id:
        job_section_de = f"""
Vorformulierter Auftrag:
Für Sie wurde der Digitalisierungsauftrag '{job_id}' bereits vorformuliert und zugewiesen.
Sobald Sie eingeloggt sind, können Sie den Auftrag unter folgendem Link mit einem Klick auslösen:
  https://alex.birchville.org/jobs/{job_id}
"""
        job_section_en = f"""
Pre-formulated Job:
The digitization job '{job_id}' has been pre-configured and assigned to your account.
Once signed in, you can launch it with one click at:
  https://alex.birchville.org/jobs/{job_id}
"""

    return f"""================================================================================
EINLADUNGS-E-MAIL / INVITATION EMAIL (DEUTSCH)
================================================================================
Betreff: Ihr Zugang zu den Birchville-Forschungsdiensten & AlexandriaSandwich

Liebe/r {display_name},

Ihr Benutzerkonto für die geschützten Birchville-Dienste wurde erfolgreich eingerichtet.

Zugangsdaten:
  • Authelia-Portal: https://auth.birchville.org
  • Alexandria-Portal: https://alex.birchville.org
  • Benutzername: {username}
  • Initialpasswort: {password}
{job_section_de}
Erste Schritte (2-Faktor-Authentifizierung):
1. Öffnen Sie https://auth.birchville.org im Browser.
2. Melden Sie sich mit Ihrem Benutzernamen '{username}' und dem Initialpasswort an.
3. Scannen Sie den angezeigten QR-Code mit Ihrer bevorzugten 2FA/TOTP-App
   (z.B. Bitwarden, Aegis Authenticator, 1Password, Google Authenticator).
4. Ändern Sie Ihr Passwort im Portal auf ein persönliches Kennwort.
5. Besuchen Sie anschliessend https://alex.birchville.org – Sie sind nun authentifiziert.

Dokumentation & Handbuch:
  https://birchville-org.github.io/AlexandriaSandwich/BENUTZERHANDBUCH/

Bei Rückfragen stehe ich Ihnen gerne zur Verfügung.

Beste Grüsse,
Marco Demarmels
Birchville Administration (webmaster@birchville.org)

================================================================================
EINLADUNGS-E-MAIL / INVITATION EMAIL (ENGLISH)
================================================================================
Subject: Your access credentials for Birchville Scholarly Services & AlexandriaSandwich

Dear {display_name},

Your user account for protected Birchville services has been provisioned.

Access details:
  • Authelia Portal: https://auth.birchville.org
  • Alexandria Portal: https://alex.birchville.org
  • Username: {username}
  • Initial Password: {password}
{job_section_en}
Getting Started (2-Factor Authentication):
1. Open https://auth.birchville.org in your browser.
2. Sign in using your username '{username}' and initial password.
3. Scan the QR code with your preferred 2FA/TOTP app
   (e.g., Bitwarden, Aegis Authenticator, 1Password, Google Authenticator).
4. Update your password to a personal one in the portal.
5. Navigate to https://alex.birchville.org – you are now fully authenticated.

Documentation & User Guide:
  https://birchville-org.github.io/AlexandriaSandwich/BENUTZERHANDBUCH/

Feel free to reach out if you have any questions.

Best regards,
Marco Demarmels
Birchville Administration (webmaster@birchville.org)
================================================================================
"""


def cmd_create(args: argparse.Namespace) -> int:
    username = args.username.strip().lower()
    display_name = args.display_name.strip()
    email = args.email.strip()
    groups = [g.strip() for g in args.groups.split(",") if g.strip()]

    # Password generation
    password = args.password
    if not password:
        password = secrets.token_urlsafe(12)

    print(f"\nGeneriere Argon2id-Kennwort-Hash für Benutzer '{username}'...")
    try:
        pw_hash = generate_argon2_hash(password, synology_host=args.synology_host)
    except Exception as e:
        sys.stderr.write(f"Fehler bei Hash-Generierung: {e}\n")
        return 1

    # Stage job if requested
    if args.job:
        print(f"Verknüpfe vorformulierten Auftrag '{args.job}' mit Benutzer '{username}'...")
        if not stage_job(args.job, username):
            print(f"Warnung: Auftrag '{args.job}' konnte nicht gestaged werden.")
        else:
            print(f"✓ Auftrag '{args.job}' erfolgreich als vorformuliert markiert (assigned_to: {username}).")

    # Authelia YAML snippet
    groups_yaml = "\n".join(f"        - {g}" for g in groups)
    authelia_snippet = f"""
# ─────────────────────────────────────────────────────────────────────────────
# In Authelia 'users_database.yml' (z.B. auf synology.local) einfügen:
# ─────────────────────────────────────────────────────────────────────────────
    {username}:
      displayname: "{display_name}"
      password: "{pw_hash}"
      email: "{email}"
      groups:
{groups_yaml}
"""
    print(authelia_snippet)

    # Email
    email_text = render_invitation_email(
        username=username,
        display_name=display_name,
        email=email,
        password=password,
        job_id=args.job
    )
    print(email_text)
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    if stage_job(args.job, args.user.strip().lower()):
        print(f"✓ Auftrag '{args.job}' ist nun zugewiesen an '{args.user}' (is_staged: true).")
        return 0
    return 1


def cmd_unstage(args: argparse.Namespace) -> int:
    if unstage_job(args.job):
        print(f"✓ Vorformulierter Status von Auftrag '{args.job}' wurde aufgehoben (is_staged: false).")
        return 0
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    if not DATA_INPUT.exists():
        print(f"Kein Input-Verzeichnis gefunden unter {DATA_INPUT}")
        return 0

    jobs = sorted([d.name for d in DATA_INPUT.iterdir() if d.is_dir() and not d.name.startswith(".")])
    if not jobs:
        print("Keine Aufträge in data/input/ vorhanden.")
        return 0

    print(f"\n{'AUFTRAGS-ID':<30} | {'VORFORMULIERT':<13} | {'BENUTZER':<18} | {'STATUS':<12}")
    print("-" * 80)
    for job in jobs:
        opts = load_job_options(job)
        is_staged = "JA (staged)" if opts.get("is_staged") else "Nein"
        assigned = opts.get("assigned_to", "—")

        # Check output report
        report_file = DATA_OUTPUT / job / "job_report.json"
        status = "Bereit"
        if report_file.exists():
            try:
                rep = json.loads(report_file.read_text(encoding="utf-8"))
                status = rep.get("status", "Abgeschlossen")
            except Exception:
                status = "Ausgeführt"

        print(f"{job:<30} | {is_staged:<13} | {assigned:<18} | {status:<12}")
    print("")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Birchville Onboarding & Staging Tool for AlexandriaSandwich & Authelia"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Neuen Benutzer generieren (Hash + YAML + Einladungsmail)")
    p_create.add_argument("--username", required=True, help="Authelia Benutzername (z.B. scholar1)")
    p_create.add_argument("--display-name", required=True, help="Vollständiger Name / Titel")
    p_create.add_argument("--email", required=True, help="E-Mail-Adresse des Benutzers")
    p_create.add_argument("--groups", default="scholars,users", help="Komma-getrennte Gruppen (Standard: scholars,users)")
    p_create.add_argument("--password", help="Optionales Wunschpasswort (sonst zufällig erzeugt)")
    p_create.add_argument("--job", help="Optionaler vorformulierter Auftrag in data/input/")
    p_create.add_argument("--synology-host", default="synology.local", help="SSH-Host für Authelia Fallback")
    p_create.set_defaults(func=cmd_create)

    # stage
    p_stage = subparsers.add_parser("stage", help="Bestehenden Auftrag einem Benutzer als vorformuliert zuweisen")
    p_stage.add_argument("--job", required=True, help="Auftrags-ID in data/input/")
    p_stage.add_argument("--user", required=True, help="Benutzername")
    p_stage.set_defaults(func=cmd_stage)

    # unstage
    p_unstage = subparsers.add_parser("unstage", help="Vorformulierten Status eines Auftrags entfernen")
    p_unstage.add_argument("--job", required=True, help="Auftrags-ID in data/input/")
    p_unstage.set_defaults(func=cmd_unstage)

    # list
    p_list = subparsers.add_parser("list", help="Aufträge, Staging- und Zuweisungsstatus anzeigen")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
