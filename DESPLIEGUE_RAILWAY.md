# Desplegar Trace Cattle en Railway

Guía para publicar la app con un link que cualquiera pueda abrir. El proyecto ya incluye `railway.toml` y `nixpacks.toml`, así que Railway detecta todo automáticamente.

## Requisitos

- Cuenta en [railway.com](https://railway.com) (puedes entrar con GitHub)
- El proyecto subido a un repositorio de GitHub (privado o público)

## Paso 1 — Subir el código a GitHub

```bash
cd TraceCattleV5
git init
git add .
git commit -m "Trace Cattle v5"
# Crea un repo en github.com y luego:
git remote add origin https://github.com/TU_USUARIO/trace-cattle.git
git push -u origin main
```

> El `.gitignore` ya excluye el archivo `.env` — verifica que no aparezca en el repo.

## Paso 2 — Crear el proyecto en Railway

1. En Railway: **New Project → Deploy from GitHub repo** → selecciona tu repo.
2. En el mismo proyecto: **+ New → Database → PostgreSQL**. Railway crea la base de datos y la variable `DATABASE_URL` queda disponible.

## Paso 3 — Variables de entorno

En el servicio de la app (no en el de la base de datos) → pestaña **Variables**, agrega:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referencia al plugin) |
| `SECRET_KEY` | genera una: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `AES_KEY` | genera otra distinta con el mismo comando |
| `ADMIN_EMAIL` | correo del administrador |
| `ADMIN_PASSWORD` | contraseña fuerte nueva (no reutilices la de desarrollo) |
| `ALLOWED_ORIGINS` | tu dominio de Railway, ej. `https://trace-cattle-production.up.railway.app` |
| `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | (opcional) para el envío real de códigos por correo |

## Paso 4 — Generar el dominio

En el servicio de la app → **Settings → Networking → Generate Domain**. Railway te da un link tipo:

```
https://trace-cattle-production.up.railway.app
```

Al arrancar, la app crea las tablas, los roles y el usuario admin automáticamente. Ese link es el que compartes.

## Verificación rápida

1. Abre `https://TU-DOMINIO/api/health` → debe responder `{"status":"ok"}`.
2. Abre el link principal → pantalla de login.
3. Entra con el `ADMIN_EMAIL` / `ADMIN_PASSWORD` que configuraste.
4. Regístrate como ganadero de prueba, crea una finca y un animal.

## Notas

- **Cámara y micrófono:** los navegadores solo permiten cámara/micrófono en HTTPS — Railway ya sirve HTTPS, así que la biometría funciona sin configuración extra.
- **Costo:** el plan Hobby de Railway es suficiente para una demo.
- **Auditores de prueba:** los carnets `SENASA-AUD-001` y `SENASA-AUD-002` vienen precargados para demostrar el registro de auditores.
