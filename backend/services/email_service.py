"""
Servicio de envío de correos electrónicos para TraceCattle.
Utiliza smtplib estándar con soporte TLS (STARTTLS).
Si las credenciales SMTP no están configuradas, imprime el código en consola
para facilitar el desarrollo/pruebas.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.config import settings

logger = logging.getLogger(__name__)


def _smtp_configurado() -> bool:
    """Verifica que las variables de SMTP estén configuradas."""
    return bool(settings.SMTP_USER and settings.SMTP_PASSWORD)


def enviar_codigo_cambio_biometrico(
    destinatario_email: str,
    destinatario_nombre: str,
    codigo: str,
    tipo_credencial: str,
) -> bool:
    """
    Envía un correo con el código de verificación para cambiar una credencial biométrica.

    Parámetros:
        destinatario_email: Correo del usuario.
        destinatario_nombre: Nombre del usuario para personalizar el mensaje.
        codigo: Código de 6 dígitos generado.
        tipo_credencial: "firma", "rostro" o "voz".

    Retorna True si el correo se envió (o se simuló en modo dev), False ante error grave.
    """
    nombres_credencial = {
        "firma": "Firma Manuscrita",
        "rostro": "Reconocimiento Facial",
        "voz": "Verificación de Voz",
    }
    nombre_legible = nombres_credencial.get(tipo_credencial, tipo_credencial.capitalize())

    asunto = f"TraceCattle – Código de verificación para cambiar {nombre_legible}"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <style>
        body {{ font-family: Arial, sans-serif; background:#f5f5f5; margin:0; padding:0; }}
        .container {{ max-width:480px; margin:40px auto; background:#fff;
                      border-radius:8px; overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,.12); }}
        .header {{ background:#2e7d32; color:#fff; padding:24px 32px; }}
        .header h1 {{ margin:0; font-size:20px; }}
        .body {{ padding:32px; color:#333; }}
        .code-box {{ background:#f0f4f0; border:2px dashed #2e7d32; border-radius:8px;
                     text-align:center; padding:20px; margin:24px 0; }}
        .code {{ font-size:36px; font-weight:bold; letter-spacing:8px; color:#2e7d32; }}
        .expires {{ color:#888; font-size:13px; margin-top:8px; }}
        .warning {{ background:#fff3e0; border-left:4px solid #ff9800;
                    padding:12px 16px; border-radius:4px; font-size:13px; color:#555; }}
        .footer {{ padding:16px 32px; background:#fafafa;
                   color:#aaa; font-size:12px; text-align:center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🐄 TraceCattle</h1>
          <p style="margin:4px 0 0;">Seguridad de Credenciales Biométricas</p>
        </div>
        <div class="body">
          <p>Hola, <strong>{destinatario_nombre}</strong>.</p>
          <p>Recibimos una solicitud para cambiar tu credencial de
             <strong>{nombre_legible}</strong>.</p>
          <p>Usa el siguiente código de verificación. Es válido por
             <strong>{settings.CODIGO_CAMBIO_EXPIRA_MINUTOS} minutos</strong>:</p>

          <div class="code-box">
            <div class="code">{codigo}</div>
            <div class="expires">Expira en {settings.CODIGO_CAMBIO_EXPIRA_MINUTOS} min</div>
          </div>

          <div class="warning">
            ⚠️ Si no solicitaste este cambio, ignora este correo.
            Tu credencial biométrica <strong>no será modificada</strong> a menos que
            ingreses este código.
          </div>
        </div>
        <div class="footer">
          Este es un mensaje automático de TraceCattle. No respondas a este correo.
        </div>
      </div>
    </body>
    </html>
    """

    texto_plano = (
        f"TraceCattle – Verificación biométrica\n\n"
        f"Hola {destinatario_nombre},\n\n"
        f"Tu código para cambiar la credencial '{nombre_legible}' es:\n\n"
        f"  {codigo}\n\n"
        f"Válido por {settings.CODIGO_CAMBIO_EXPIRA_MINUTOS} minutos.\n\n"
        f"Si no solicitaste este cambio, ignora este correo.\n"
    )

    if not _smtp_configurado():
        # Modo desarrollo: mostrar código en consola
        logger.warning(
            "[EMAIL-DEV] SMTP no configurado. "
            "Código para %s (%s): %s",
            destinatario_email,
            tipo_credencial,
            codigo,
        )
        print(
            f"\n{'='*50}\n"
            f"[DEV] Código de cambio biométrico\n"
            f"Usuario : {destinatario_nombre} <{destinatario_email}>\n"
            f"Tipo    : {nombre_legible}\n"
            f"Código  : {codigo}\n"
            f"{'='*50}\n"
        )
        return True

    # Construcción del mensaje MIME
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = f"TraceCattle <{settings.SMTP_FROM}>"
    mensaje["To"] = destinatario_email

    mensaje.attach(MIMEText(texto_plano, "plain", "utf-8"))
    mensaje.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [destinatario_email], mensaje.as_string())
        logger.info("Correo de verificación enviado a %s", destinatario_email)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "Error de autenticación SMTP (usuario: %s): %s. "
            "Para Gmail debes usar una 'Contraseña de aplicación' de 16 caracteres, "
            "no tu contraseña normal. Actívala en: "
            "Cuenta Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones.",
            settings.SMTP_USER, exc,
        )
    except smtplib.SMTPException as exc:
        logger.error("Error SMTP al enviar correo a %s: %s", destinatario_email, exc)
    except OSError as exc:
        logger.error(
            "Error de red al conectar con %s:%s — %s",
            settings.SMTP_HOST, settings.SMTP_PORT, exc,
        )

    return False
