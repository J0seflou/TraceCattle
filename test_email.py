"""
Script de diagnóstico SMTP para TraceCattle.
Ejecutar desde la carpeta raíz del proyecto:

    python test_email.py

Muestra exactamente qué error ocurre al intentar enviar un correo.
"""
import smtplib
import sys
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER

print("=" * 55)
print("  Diagnóstico SMTP — TraceCattle")
print("=" * 55)
print(f"  Host     : {SMTP_HOST}:{SMTP_PORT}")
print(f"  Usuario  : {SMTP_USER}")
print(f"  Password : {'*' * len(SMTP_PASSWORD)} ({len(SMTP_PASSWORD)} caracteres)")
print(f"  From     : {SMTP_FROM}")
print("=" * 55)

if not SMTP_USER or not SMTP_PASSWORD:
    print("\n❌ SMTP_USER o SMTP_PASSWORD vacíos en el .env")
    sys.exit(1)

if len(SMTP_PASSWORD) < 16:
    print(f"\n⚠️  La contraseña tiene solo {len(SMTP_PASSWORD)} caracteres.")
    print("   Las Contraseñas de aplicación de Gmail tienen exactamente 16.")
    print("   Asegúrate de copiarla completa y sin espacios.")

DESTINATARIO = input(f"\nIngresa el correo donde enviar la prueba [{SMTP_USER}]: ").strip()
if not DESTINATARIO:
    DESTINATARIO = SMTP_USER

print(f"\nIntentando enviar correo de prueba a {DESTINATARIO} ...")

msg = MIMEText("Este es un correo de prueba de TraceCattle.", "plain", "utf-8")
msg["Subject"] = "TraceCattle – Prueba SMTP"
msg["From"] = f"TraceCattle <{SMTP_FROM}>"
msg["To"] = DESTINATARIO

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        print("  [1/4] Conectado al servidor SMTP ✓")
        server.ehlo()
        print("  [2/4] EHLO enviado ✓")
        server.starttls()
        print("  [3/4] TLS activado ✓")
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("  [4/4] Autenticación exitosa ✓")
        server.sendmail(SMTP_FROM, [DESTINATARIO], msg.as_string())
    print(f"\n✅ Correo enviado correctamente a {DESTINATARIO}")
    print("   Si no aparece en la bandeja, revisa Spam.")

except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ Error de autenticación: {e}")
    print("\n   Posibles causas:")
    print("   1. La contraseña de aplicación está mal copiada (deben ser 16 chars sin espacios)")
    print("   2. La verificación en 2 pasos no está activa en la cuenta Google")
    print("   3. La cuenta no tiene habilitadas las contraseñas de aplicación")
    print("\n   Cómo crear la contraseña de aplicación:")
    print("   → myaccount.google.com → Seguridad → Verificación en 2 pasos")
    print("     → Contraseñas de aplicaciones → Correo → Otro → 'TraceCattle'")

except smtplib.SMTPRecipientsRefused as e:
    print(f"\n❌ Destinatario rechazado: {e}")

except smtplib.SMTPSenderRefused as e:
    print(f"\n❌ Remitente rechazado: {e}")
    print(f"   SMTP_FROM ({SMTP_FROM}) debe coincidir con SMTP_USER ({SMTP_USER}) en Gmail.")

except smtplib.SMTPException as e:
    print(f"\n❌ Error SMTP: {e}")

except OSError as e:
    print(f"\n❌ Error de red: {e}")
    print("   Verifica que el servidor backend tenga acceso a Internet.")
