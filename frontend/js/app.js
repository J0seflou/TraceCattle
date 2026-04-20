/* ══════════ Trace Cattle - App Principal ══════════ */

// Detecta automáticamente si corre local o en la nube
const API_URL = `${window.location.origin}/api`;

// ── Tipos de evento permitidos por rol ──
const ROLE_EVENT_TYPES = {
    ganadero: [
        { value: 'nacimiento', label: 'Nacimiento' },
        { value: 'vacunacion', label: 'Vacunación' },
        { value: 'desparacitacion', label: 'Desparasitación' },
        { value: 'cambio_propietario', label: 'Cambio de propietario' },
        { value: 'muerte', label: 'Muerte' },
        { value: 'venta', label: 'Venta' },
    ],
    veterinario: [
        { value: 'nacimiento', label: 'Nacimiento' },
        { value: 'vacunacion', label: 'Vacunación' },
        { value: 'desparacitacion', label: 'Desparasitación' },
        { value: 'muerte', label: 'Muerte' },
    ],
    transportista: [
        { value: 'traslado', label: 'Traslado' },
    ],
    auditor: [
        { value: 'auditoria', label: 'Auditoría' },
        { value: 'certificacion_sanitaria', label: 'Certificación sanitaria' },
    ],
    admin: [
        { value: 'nacimiento', label: 'Nacimiento' },
        { value: 'vacunacion', label: 'Vacunación' },
        { value: 'desparacitacion', label: 'Desparasitación' },
        { value: 'traslado', label: 'Traslado' },
        { value: 'cambio_propietario', label: 'Cambio de propietario' },
        { value: 'certificacion_sanitaria', label: 'Certificación sanitaria' },
        { value: 'muerte', label: 'Muerte' },
        { value: 'venta', label: 'Venta' },
        { value: 'auditoria', label: 'Auditoría' },
    ],
};

// ── Estado global ──
const state = {
    token: localStorage.getItem('tc_token'),
    user: JSON.parse(localStorage.getItem('tc_user') || 'null'),
    adminFincaId: null,       // Finca seleccionada por el admin (null = ninguna)
    adminFincaNombre: null,
};

// ── Fetch con autenticación ──
async function apiFetch(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    // Si options.body es FormData, no establecer Content-Type
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }
    const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    if (res.status === 401) {
        logout();
        throw new Error('Sesión expirada');
    }
    return res;
}

// ── Navegación SPA ──
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById(pageId);
    if (page) page.classList.add('active');
}

function showSection(btn) {
    const target = btn.getAttribute('data-target');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const section = document.getElementById(target);
    if (section) section.classList.add('active');

    // Cargar datos al cambiar de sección
    if (target === 'section-animals') loadAnimals();
    if (target === 'section-search') initializeSearchFilters();
    if (target === 'section-events') { loadAnimalsForSelect(); loadRecentEvents(); }
    if (target === 'section-biometrics') checkBiometricStatus();
    if (target === 'section-audit') { loadAnimalsForAudit(); }
    if (target === 'section-users') { loadUsersSection(); }
    if (target === 'section-home') loadDashboardStats();
}

// ── Toast notifications ──
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Permisos por rol en la UI ──
function applyRolePermissions() {
    const rol = state.user ? state.user.rol_nombre : null;
    if (!rol) return;

    // Auditoría: auditor y admin tienen acceso
    const navAudit = document.getElementById('nav-btn-audit');
    if (navAudit) navAudit.style.display = (rol === 'auditor' || rol === 'admin') ? '' : 'none';

    // Usuarios por finca: solo admin
    const navUsers = document.getElementById('nav-btn-users');
    if (navUsers) navUsers.style.display = (rol === 'admin') ? '' : 'none';

    // Registrar animal: ganadero y admin
    const btnRegistrar = document.getElementById('btn-registrar-animal');
    if (btnRegistrar) btnRegistrar.style.display = (rol === 'ganadero' || rol === 'admin') ? '' : 'none';

    // Tipos de evento: filtrar por rol
    const eventoSelect = document.getElementById('event-tipo');
    if (eventoSelect) {
        const tipos = ROLE_EVENT_TYPES[rol] || [];
        eventoSelect.innerHTML = '<option value="">Seleccionar tipo...</option>' +
            tipos.map(t => `<option value="${t.value}">${t.label}</option>`).join('');
    }
}

// ── Selector de finca para admin ──
async function loadAdminFincaSelector() {
    const grid = document.getElementById('admin-fincas-grid');
    grid.innerHTML = '<p style="color:var(--text-muted);">Cargando fincas...</p>';
    try {
        const res = await apiFetch('/fincas/admin/todas');
        if (!res.ok) { grid.innerHTML = '<p style="color:var(--danger);">Error cargando fincas.</p>'; return; }
        const fincas = await res.json();

        if (fincas.length === 0) {
            grid.innerHTML = '<p style="color:var(--text-muted); text-align:center;">No hay fincas registradas aún.</p>';
            return;
        }

        grid.innerHTML = fincas.map(f => `
            <div onclick="seleccionarFincaAdmin('${f.id_finca}', '${f.nombre.replace(/'/g, "\\'")}' )"
                 style="background:#fff; border:2px solid var(--border); border-radius:12px; padding:1.5rem;
                        cursor:pointer; transition:border-color .2s, box-shadow .2s;"
                 onmouseover="this.style.borderColor='var(--primary)'; this.style.boxShadow='0 4px 16px rgba(45,80,22,.12)'"
                 onmouseout="this.style.borderColor='var(--border)'; this.style.boxShadow='none'">
                <h3 style="margin:0 0 0.4rem; color:var(--primary-dark); font-size:1.1rem;">${f.nombre}</h3>
                <p style="margin:0 0 0.8rem; color:var(--text-muted); font-size:0.85rem;">&#128205; ${f.ubicacion}</p>
                <div style="display:flex; flex-direction:column; gap:0.3rem; font-size:0.88rem;">
                    <span><strong>Propietario:</strong> ${f.propietario_nombre}</span>
                    <span><strong>Animales:</strong> ${f.total_animales}</span>
                    <span><strong>Miembros:</strong> ${f.total_miembros}</span>
                </div>
                <div style="margin-top:1rem; text-align:right;">
                    <span style="background:var(--primary); color:#fff; padding:0.3rem 0.9rem;
                                 border-radius:6px; font-size:0.82rem; font-weight:600;">Seleccionar →</span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        grid.innerHTML = '<p style="color:var(--danger);">Error de conexión.</p>';
    }
}

function seleccionarFincaAdmin(fincaId, fincaNombre) {
    state.adminFincaId = fincaId;
    state.adminFincaNombre = fincaNombre;
    showDashboard();
}

function cambiarFincaAdmin() {
    state.adminFincaId = null;
    state.adminFincaNombre = null;
    loadAdminFincaSelector().then(() => showPage('page-admin-selector'));
}

function showDashboard() {
    showPage('page-dashboard');

    // Siempre volver a la pestaña Inicio
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const homeBtn = document.querySelector('[data-target="section-home"]');
    if (homeBtn) homeBtn.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const homeSection = document.getElementById('section-home');
    if (homeSection) homeSection.classList.add('active');

    document.getElementById('nav-user-name').textContent =
        `${state.user.nombre} ${state.user.apellido}`;
    document.getElementById('nav-user-role').textContent = state.user.rol_nombre;

    // Mostrar finca seleccionada y botón "Cambiar finca" si es admin
    const adminFincaInfo = document.getElementById('nav-admin-finca-info');
    const btnCambiar = document.getElementById('btn-cambiar-finca');
    if (state.user.rol_nombre === 'admin' && state.adminFincaId) {
        document.getElementById('nav-admin-finca-nombre').textContent = state.adminFincaNombre;
        if (adminFincaInfo) adminFincaInfo.style.display = 'inline';
        if (btnCambiar) btnCambiar.style.display = 'inline-block';
    } else {
        if (adminFincaInfo) adminFincaInfo.style.display = 'none';
        if (btnCambiar) btnCambiar.style.display = 'none';
    }

    applyRolePermissions();
    loadDashboardStats();
}

// ── Inicialización ──
async function initApp() {
    if (state.token && state.user) {
        // Refrescar perfil del servidor para obtener datos actualizados (finca, rol, etc.)
        try {
            const res = await fetch(`${window.location.origin}/api/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`,
                    'Content-Type': 'application/json',
                },
            });
            if (res.status === 401) { logout(); return; }
            if (res.ok) {
                const freshUser = await res.json();
                state.user = freshUser;
                localStorage.setItem('tc_user', JSON.stringify(freshUser));
            }
        } catch (e) { /* Sin conexión: continuar con datos en caché */ }

        // Admin debe seleccionar finca antes de entrar
        if (state.user.rol_nombre === 'admin' && !state.adminFincaId) {
            await loadAdminFincaSelector();
            showPage('page-admin-selector');
            return;
        }

        showDashboard();
    } else {
        showPage('page-login');
    }
}

function logout() {
    localStorage.removeItem('tc_token');
    localStorage.removeItem('tc_user');
    window.location.reload();
}

// Devuelve el sufijo ?finca_id=xxx cuando el admin tiene una finca seleccionada
function adminFincaParam(prefix = '?') {
    return (state.user && state.user.rol_nombre === 'admin' && state.adminFincaId)
        ? `${prefix}finca_id=${state.adminFincaId}`
        : '';
}

async function loadDashboardStats() {
    try {
        const fp = adminFincaParam();
        const [animalsRes, eventsRes] = await Promise.all([
            apiFetch(`/animales/${fp}`),
            apiFetch(`/eventos/${fp}`),
        ]);
        if (animalsRes.ok) {
            const animals = await animalsRes.json();
            document.getElementById('stat-animals').textContent = animals.length;
        }
        if (eventsRes.ok) {
            const events = await eventsRes.json();
            document.getElementById('stat-events').textContent = events.length;
        }
        // Check biometric status
        if (state.user) {
            const bioRes = await apiFetch(`/biometria/estado/${state.user.id_users}`);
            if (bioRes.ok) {
                const bio = await bioRes.json();
                document.getElementById('stat-bio').textContent = bio.registrado ? 'Registrada' : 'Pendiente';
            }
        }
        // Cargar info de finca
        loadFincaInfo();
    } catch (e) {
        // Dashboard stats are non-critical
    }
}

async function loadFincaInfo() {
    try {
        const fincaCard = document.getElementById('finca-info-card');
        const sinFincaCard = document.getElementById('sin-finca-card');
        if (!fincaCard) return;

        // Admin tiene su propia lógica de finca (panel selector); no usar mi-finca
        if (state.user && state.user.rol_nombre === 'admin') {
            if (sinFincaCard) sinFincaCard.style.display = 'none';
            fincaCard.style.display = 'none';
            return;
        }

        const fincaRes = await apiFetch('/fincas/mi-finca');
        if (!fincaRes.ok) {
            // Sin finca: limpiar tarjeta y lista de animales
            fincaCard.style.display = 'none';
            const animalesList = document.getElementById('animals-list');
            if (animalesList) animalesList.innerHTML = '<p class="text-muted">No perteneces a ninguna finca. No tienes animales visibles.</p>';
            document.getElementById('stat-animals').textContent = '0';
            // Actualizar caché local: quitar finca del usuario
            if (state.user && state.user.finca) {
                state.user.finca = null;
                localStorage.setItem('tc_user', JSON.stringify(state.user));
            }
            if (sinFincaCard && state.user && state.user.rol_nombre !== 'admin') {
                sinFincaCard.style.display = 'block';
            }
            return;
        }
        if (sinFincaCard) sinFincaCard.style.display = 'none';

        const finca = await fincaRes.json();
        fincaCard.style.display = 'block';
        document.getElementById('finca-nombre').textContent = finca.nombre;
        document.getElementById('finca-ubicacion').textContent = finca.ubicacion || 'Sin ubicación';
        document.getElementById('finca-codigo').textContent = finca.codigo_acceso;

        const miembrosRes = await apiFetch('/fincas/mi-finca/miembros');
        if (!miembrosRes.ok) return;

        const miembros = await miembrosRes.json();
        const miembrosDiv = document.getElementById('finca-miembros');
        const countEl = document.getElementById('finca-miembros-count');
        if (countEl) countEl.textContent = `${miembros.length} miembro${miembros.length !== 1 ? 's' : ''}`;

        const rol = state.user ? state.user.rol_nombre : '';
        const puedeGestionar = rol === 'admin' || rol === 'ganadero';

        miembrosDiv.innerHTML = miembros.map(m => {
            const esPropietario = m.es_propietario;
            const esMismoUsuario = state.user && m.id_users === state.user.id_users;
            const mostrarMenu = puedeGestionar && !esPropietario && !esMismoUsuario;

            const badge = esPropietario
                ? '<span style="background:rgba(255,255,255,0.3);padding:1px 7px;border-radius:10px;font-size:0.75rem;margin-left:6px;">Propietario</span>'
                : '';

            const menuKebab = mostrarMenu
                ? `<div style="position:relative;display:inline-block;">
                     <button onclick="toggleMenuMiembro(event,'menu-${m.id_users}')"
                             style="background:transparent;border:none;color:white;font-size:1.2rem;
                                    cursor:pointer;padding:2px 6px;border-radius:4px;line-height:1;
                                    opacity:0.8;" title="Opciones">&#8942;</button>
                     <div id="menu-${m.id_users}"
                          style="display:none;position:absolute;right:0;top:100%;z-index:100;
                                 background:#fff;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.18);
                                 min-width:140px;overflow:hidden;">
                         <button onclick="expulsarMiembro('${m.id_users}','${m.nombre} ${m.apellido}')"
                                 style="display:block;width:100%;padding:0.55rem 1rem;text-align:left;
                                        background:transparent;border:none;color:#dc3545;font-size:0.88rem;
                                        cursor:pointer;white-space:nowrap;"
                                 onmouseover="this.style.background='#fff5f5'"
                                 onmouseout="this.style.background='transparent'">
                             &#128683; Expulsar de la finca
                         </button>
                     </div>
                   </div>`
                : '';

            return `<div style="display:flex;justify-content:space-between;align-items:center;
                                background:rgba(255,255,255,0.12);padding:0.45rem 0.75rem;
                                border-radius:8px;gap:0.5rem;">
                        <span style="font-size:0.88rem;">
                            ${m.nombre} ${m.apellido}
                            <span style="opacity:0.75;font-size:0.8rem;">(${m.rol})</span>
                            ${badge}
                        </span>
                        ${menuKebab}
                    </div>`;
        }).join('');
    } catch (e) {
        // Finca info is non-critical
    }
}

function toggleMenuMiembro(event, menuId) {
    event.stopPropagation();
    // Cerrar cualquier otro menú abierto
    document.querySelectorAll('[id^="menu-"]').forEach(m => {
        if (m.id !== menuId) m.style.display = 'none';
    });
    const menu = document.getElementById(menuId);
    if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

// Cerrar menús al hacer clic fuera
document.addEventListener('click', () => {
    document.querySelectorAll('[id^="menu-"]').forEach(m => m.style.display = 'none');
});

async function expulsarMiembro(userId, nombreCompleto) {
    if (!confirm(`¿Estás seguro de que quieres expulsar a ${nombreCompleto} de la finca?\nPerderá acceso a todos los recursos de la finca.`)) return;

    try {
        const res = await apiFetch(`/fincas/mi-finca/miembros/${userId}`, { method: 'DELETE' });
        const data = await res.json();

        if (res.ok) {
            showToast(data.mensaje, 'success');
            loadFincaInfo();
        } else {
            showToast(data.detail || 'No se pudo expulsar al miembro', 'error');
        }
    } catch (e) {
        showToast('Error de conexión', 'error');
    }
}

async function unirseAFinca() {
    const input = document.getElementById('input-codigo-finca');
    const codigo = input ? input.value.trim().toUpperCase() : '';
    if (!codigo) { showToast('Ingresa el código de acceso', 'error'); return; }

    try {
        const res = await apiFetch('/fincas/unirse', {
            method: 'POST',
            body: JSON.stringify({ codigo_acceso: codigo }),
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.mensaje, 'success');
            loadFincaInfo();
            loadDashboardStats();
        } else {
            showToast(data.detail || 'No se pudo unir a la finca', 'error');
        }
    } catch (e) {
        showToast('Error de conexión', 'error');
    }
}

// ── Arranque ──
document.addEventListener('DOMContentLoaded', initApp);
