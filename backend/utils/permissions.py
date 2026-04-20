"""
Control de permisos por rol para tipos de evento ganadero.
"""

ROLE_PERMISSIONS = {
    "ganadero": ["nacimiento", "cambio_propietario", "venta", "muerte", "desparacitacion", "vacunacion"],
    "veterinario": ["nacimiento", "vacunacion", "desparacitacion", "muerte"],
    "transportista": ["traslado"],
    "auditor": ["auditoria", "certificacion_sanitaria"],
    "admin": [
        "nacimiento", "cambio_propietario", "venta", "muerte", "desparacitacion",
        "vacunacion", "traslado", "certificacion_sanitaria", "auditoria",
    ],
}


def check_permission(role: str, event_type: str) -> bool:
    """Verifica si un rol puede registrar un tipo de evento."""
    return event_type in ROLE_PERMISSIONS.get(role, [])


def get_allowed_events(role: str) -> list[str]:
    """Retorna los tipos de evento permitidos para un rol."""
    return ROLE_PERMISSIONS.get(role, [])
