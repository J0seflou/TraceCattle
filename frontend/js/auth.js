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

/* ── Mostrar/ocultar campos según el rol seleccionado ── */
document.getElementById('reg-rol').addEventListener('change', function () {
    const rol = this.value;
    const fincaFields = document.getElementById('finca-fields');
    const codigoFields = document.getElementById('codigo-finca-fields');
    const carnetFields = document.getElementById('carnet-senasa-fields');

    // Resetear todos
    fincaFields.style.display = 'none';
    codigoFields.style.display = 'none';
    carnetFields.style.display = 'none';
    document.getElementById('reg-finca-nombre').required = false;
    document.getElementById('reg-codigo-finca').required = false;
    document.getElementById('reg-carnet-senasa').required = false;

    if (rol === 'ganadero') {
        fincaFields.style.display = 'block';
        document.getElementById('reg-finca-nombre').required = true;
    } else if (rol === 'auditor') {
        carnetFields.style.display = 'block';
        codigoFields.style.display = 'block';
        document.getElementById('reg-carnet-senasa').required = true;
        document.getElementById('reg-codigo-finca').required = true;
    } else {
        codigoFields.style.display = 'block';
        document.getElementById('reg-codigo-finca').required = true;
    }
});

/* ── Validación en tiempo real del carné SENASA ── */
let _carnetDebounce = null;
function validarCarnetSenasa(valor) {
    const feedback = document.getElementById('carnet-senasa-feedback');
    const carnet = valor.trim().toUpperCase();

    clearTimeout(_carnetDebounce);
    if (carnet.length < 3) {
        feedback.textContent = 'Ingresa tu número de carné para verificarlo.';
        feedback.style.color = '#666';
        return;
    }

    feedback.textContent = 'Verificando...';
    feedback.style.color = '#888';

    _carnetDebounce = setTimeout(async () => {
        try {
            const res = await fetch(`${API_URL}/senasa/auditores/verificar/${encodeURIComponent(carnet)}`);
            const data = await res.json();
            if (data.valido && data.disponible) {
                feedback.textContent = '✓ ' + data.mensaje;
                feedback.style.color = '#16a34a';
            } else {
                feedback.textContent = '✗ ' + data.mensaje;
                feedback.style.color = '#dc2626';
            }
        } catch {
            feedback.textContent = 'No se pudo verificar el carné.';
            feedback.style.color = '#888';
        }
    }, 600);
}

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
    }

    // Si es auditor, incluir el carné SENASA
    if (rolNombre === 'auditor') {
        body.carnet_senasa = document.getElementById('reg-carnet-senasa').value.trim().toUpperCase();
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
            showToast(data.detail || 'Error al registrarse', 'error');
        }
    } catch (err) {
        showToast('Error de conexión con el servidor', 'error');
    }
});
