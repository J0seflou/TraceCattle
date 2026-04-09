/* ══════════ Trace Cattle - App Principal ══════════ */

const API_URL = 'http://localhost:8000/api';

// ── Estado global ──
const state = {
    token: localStorage.getItem('tc_token'),
    user: JSON.parse(localStorage.getItem('tc_user') || 'null'),
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

// ── Inicialización ──
function initApp() {
    if (state.token && state.user) {
        showPage('page-dashboard');
        document.getElementById('nav-user-name').textContent =
            `${state.user.nombre} ${state.user.apellido}`;
        document.getElementById('nav-user-role').textContent = state.user.rol_nombre;
        loadDashboardStats();
    } else {
        showPage('page-login');
    }
}

function logout() {
    localStorage.removeItem('tc_token');
    localStorage.removeItem('tc_user');
    state.token = null;
    state.user = null;
    showPage('page-login');
}

async function loadDashboardStats() {
    try {
        const [animalsRes, eventsRes] = await Promise.all([
            apiFetch('/animales'),
            apiFetch('/eventos'),
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
        if (!fincaCard) return;

        // Intentar obtener finca de los datos del usuario o del API
        const fincaRes = await apiFetch('/fincas/mi-finca');
        if (fincaRes.ok) {
            const finca = await fincaRes.json();
            fincaCard.style.display = 'block';
            document.getElementById('finca-nombre').textContent = finca.nombre;
            document.getElementById('finca-ubicacion').textContent = finca.ubicacion || 'Sin ubicación';
            document.getElementById('finca-codigo').textContent = finca.codigo_acceso;

            // Cargar miembros
            const miembrosRes = await apiFetch('/fincas/mi-finca/miembros');
            if (miembrosRes.ok) {
                const miembros = await miembrosRes.json();
                const miembrosDiv = document.getElementById('finca-miembros');
                miembrosDiv.innerHTML = '<strong>Miembros:</strong> ' +
                    miembros.map(m => `${m.nombre} ${m.apellido} (${m.rol})`).join(' &bull; ');
            }
        } else {
            fincaCard.style.display = 'none';
        }
    } catch (e) {
        // Finca info is non-critical
    }
}

// ── Arranque ──
document.addEventListener('DOMContentLoaded', initApp);
