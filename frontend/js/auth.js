/* ══════════ Autenticación ══════════ */

document.getElementById('form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const contrasena = document.getElementById('login-password').value;

    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, contrasena }),
        });
        const data = await res.json();

        if (res.ok) {
            state.token = data.access_token;
            state.user = data.user;
            localStorage.setItem('tc_token', data.access_token);
            localStorage.setItem('tc_user', JSON.stringify(data.user));
            showToast('Bienvenido, ' + data.user.nombre, 'success');
            initApp();
        } else {
            showToast(data.detail || 'Error al iniciar sesión', 'error');
        }
    } catch (err) {
        showToast('Error de conexión con el servidor', 'error');
    }
});

/* ── Mostrar/ocultar campos de finca según el rol seleccionado ── */
document.getElementById('reg-rol').addEventListener('change', function () {
    const rol = this.value;
    const fincaFields = document.getElementById('finca-fields');
    const codigoFields = document.getElementById('codigo-finca-fields');
    const senasaFields = document.getElementById('senasa-fields');

    if (rol === 'ganadero') {
        fincaFields.style.display = 'block';
        codigoFields.style.display = 'none';
        senasaFields.style.display = 'none';
        document.getElementById('reg-finca-nombre').required = true;
        document.getElementById('reg-codigo-finca').required = false;
        document.getElementById('reg-numero-senasa').required = false;
    } else {
        fincaFields.style.display = 'none';
        codigoFields.style.display = 'block';
        document.getElementById('reg-finca-nombre').required = false;
        document.getElementById('reg-codigo-finca').required = true;

        if (rol === 'auditor') {
            senasaFields.style.display = 'block';
            document.getElementById('reg-numero-senasa').required = true;
        } else {
            senasaFields.style.display = 'none';
            document.getElementById('reg-numero-senasa').required = false;
        }
    }
});

document.getElementById('form-register').addEventListener('submit', async (e) => {
    e.preventDefault();

    const rolNombre = document.getElementById('reg-rol').value;

    const body = {
        nombre: document.getElementById('reg-nombre').value,
        apellido: document.getElementById('reg-apellido').value,
        email: document.getElementById('reg-email').value,
        telefono: document.getElementById('reg-telefono').value || null,
        contrasena: document.getElementById('reg-password').value,
        rol_nombre: rolNombre,
    };

    // Si es ganadero, enviar datos de finca nueva
    if (rolNombre === 'ganadero') {
        body.finca_nombre = document.getElementById('reg-finca-nombre').value;
        body.finca_ubicacion = document.getElementById('reg-finca-ubicacion').value || null;
    } else {
        // Si es otro rol, enviar código de finca
        body.codigo_finca = document.getElementById('reg-codigo-finca').value.toUpperCase();
        // Si es auditor, enviar número de carné SENASA
        if (rolNombre === 'auditor') {
            body.numero_senasa = document.getElementById('reg-numero-senasa').value || null;
        }
    }

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();

        if (res.ok) {
            state.token = data.access_token;
            state.user = data.user;
            localStorage.setItem('tc_token', data.access_token);
            localStorage.setItem('tc_user', JSON.stringify(data.user));
            showToast('Cuenta creada exitosamente', 'success');
            initApp();
        } else {
            let msg = 'Error al registrarse';
            if (data.detail) {
                if (typeof data.detail === 'string') {
                    msg = data.detail;
                } else if (Array.isArray(data.detail)) {
                    msg = data.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
                } else {
                    msg = JSON.stringify(data.detail);
                }
            }
            showToast(msg, 'error');
        }
    } catch (err) {
        showToast('Error de conexión con el servidor', 'error');
    }
});
