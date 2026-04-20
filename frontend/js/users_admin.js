/* ══════════ Usuarios por Finca (Admin) ══════════ */

async function loadUsersSection() {
    const container = document.getElementById('users-finca-container');
    const titulo = document.getElementById('users-section-title');

    if (!state.adminFincaId) {
        container.innerHTML = '<p class="text-muted">No hay una finca seleccionada.</p>';
        return;
    }

    if (titulo && state.adminFincaNombre) {
        titulo.textContent = `Usuarios de "${state.adminFincaNombre}"`;
    }

    container.innerHTML = '<p class="text-muted">Cargando...</p>';
    try {
        const res = await apiFetch(`/fincas/admin/${state.adminFincaId}/usuarios`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            container.innerHTML = `<p style="color:var(--danger);">${err.detail || 'Error cargando usuarios'}</p>`;
            return;
        }
        const usuarios = await res.json();
        renderUsersFinca(usuarios);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--danger);">Error de conexión.</p>';
    }
}

function renderUsersFinca(usuarios) {
    const container = document.getElementById('users-finca-container');

    if (usuarios.length === 0) {
        container.innerHTML = '<p class="text-muted">Esta finca no tiene usuarios registrados.</p>';
        return;
    }

    const ROL_LABELS = {
        ganadero: 'Ganadero',
        veterinario: 'Veterinario',
        transportista: 'Transportista',
        auditor: 'Auditor',
        admin: 'Administrador',
    };

    const ROL_COLORS = {
        ganadero: '#2d5016',
        veterinario: '#1d4ed8',
        transportista: '#b45309',
        auditor: '#6d28d9',
        admin: '#991b1b',
    };

    container.innerHTML = `
        <div class="table-container">
            <p style="color:var(--text-muted); font-size:0.88rem; margin-bottom:0.8rem;">
                ${usuarios.length} usuario${usuarios.length !== 1 ? 's' : ''} en esta finca
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
                <thead>
                    <tr style="background:var(--primary); color:#fff;">
                        <th style="padding:0.7rem 1rem; text-align:left; border-radius:8px 0 0 0;">Nombre</th>
                        <th style="padding:0.7rem 1rem; text-align:left;">Correo</th>
                        <th style="padding:0.7rem 1rem; text-align:left;">Rol</th>
                        <th style="padding:0.7rem 1rem; text-align:left;">Estado</th>
                        <th style="padding:0.7rem 1rem; text-align:left; border-radius:0 8px 0 0;">Miembro desde</th>
                    </tr>
                </thead>
                <tbody>
                    ${usuarios.map((u, i) => {
                        const bg = i % 2 === 0 ? '#fff' : '#f8faf5';
                        const rolColor = ROL_COLORS[u.rol] || '#555';
                        const rolLabel = ROL_LABELS[u.rol] || u.rol;
                        const propBadge = u.es_propietario
                            ? '<span style="background:#2d5016;color:#fff;padding:1px 6px;border-radius:8px;font-size:0.75rem;margin-left:5px;">Propietario</span>'
                            : '';
                        const estadoBadge = u.activo
                            ? '<span style="color:var(--success);font-weight:600;">Activo</span>'
                            : '<span style="color:var(--danger);font-weight:600;">Inactivo</span>';
                        const fecha = u.creado_en
                            ? new Date(u.creado_en).toLocaleDateString('es-CR', { year:'numeric', month:'short', day:'numeric' })
                            : 'N/A';
                        return `
                            <tr style="background:${bg}; border-bottom:1px solid var(--border);">
                                <td style="padding:0.7rem 1rem; font-weight:500;">
                                    ${u.nombre} ${u.apellido}${propBadge}
                                </td>
                                <td style="padding:0.7rem 1rem; color:var(--text-muted);">${u.email}</td>
                                <td style="padding:0.7rem 1rem;">
                                    <span style="background:${rolColor}22; color:${rolColor};
                                                 padding:2px 8px; border-radius:8px; font-size:0.82rem; font-weight:600;">
                                        ${rolLabel}
                                    </span>
                                </td>
                                <td style="padding:0.7rem 1rem;">${estadoBadge}</td>
                                <td style="padding:0.7rem 1rem; color:var(--text-muted);">${fecha}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}
