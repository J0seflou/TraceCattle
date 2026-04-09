/* ══════════ Auditoría y Consulta ══════════ */

function showAuditTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.audit-tab').forEach(t => {
        t.classList.remove('active');
        t.classList.add('hidden');
    });
    const tab = document.getElementById(tabId);
    tab.classList.remove('hidden');
    tab.classList.add('active');

    if (tabId === 'audit-log') loadBitacora();
    if (tabId === 'audit-alerts') loadAlerts();
}

// ── Historial de animal ──

async function loadAnimalsForAudit() {
    try {
        const res = await apiFetch('/animales');
        if (!res.ok) return;
        const animals = await res.json();
        const select = document.getElementById('audit-animal-select');
        const current = select.value;
        select.innerHTML = '<option value="">Seleccionar...</option>';
        animals.forEach(a => {
            select.innerHTML += `<option value="${a.id_animales}">${a.codigo_unico} - ${a.nombre || a.especie}</option>`;
        });
        if (current) select.value = current;
    } catch (e) { /* silent */ }
}

async function loadAnimalAudit() {
    const animalId = document.getElementById('audit-animal-select').value;
    if (!animalId) return;

    const container = document.getElementById('audit-animal-report');
    container.innerHTML = '<p class="text-muted">Cargando...</p>';

    try {
        const res = await apiFetch(`/auditoria/animal/${animalId}`);
        if (!res.ok) {
            container.innerHTML = '<p class="text-muted">Error cargando auditoría</p>';
            return;
        }
        const data = await res.json();
        renderAnimalAudit(data, container);
    } catch (e) {
        container.innerHTML = '<p class="text-muted">Error de conexión</p>';
    }
}

function renderAnimalAudit(data, container) {
    const integridad = data.integridad;
    const cadenaOk = integridad.cadena_completa_integra;

    let html = `
        <div class="info-card mt-1">
            <h3>Animal: ${data.animal.codigo_unico} - ${data.animal.nombre || data.animal.especie}</h3>
            <p><strong>Propietario:</strong> ${data.animal.propietario || 'N/A'}</p>
            <p><strong>Total eventos:</strong> ${data.total_eventos}</p>
            <p><strong>Integridad de cadena:</strong>
                <span class="${cadenaOk ? 'integrity-ok' : 'integrity-fail'}">
                    ${cadenaOk ? '\u2705 CADENA ÍNTEGRA' : '\u274C CADENA COMPROMETIDA'}
                </span>
            </p>
        </div>

        <h3 class="mt-2">Línea de tiempo de eventos</h3>
        <div class="timeline">
    `;

    if (data.eventos.length === 0) {
        html += '<p class="text-muted">No hay eventos registrados para este animal.</p>';
    }

    data.eventos.forEach((e, i) => {
        const integridadEvento = integridad.detalle && integridad.detalle[i];
        const eventoOk = integridadEvento ? integridadEvento.cadena_integra : true;
        const val = e.validacion;

        html += `
            <div class="timeline-item ${eventoOk ? '' : 'integrity-error'}">
                <div style="display:flex; justify-content:space-between; flex-wrap:wrap;">
                    <strong><span class="badge">${e.tipo_evento}</span></strong>
                    <small>${new Date(e.registrado_en).toLocaleString('es')}</small>
                </div>
                <div class="mt-1" style="font-size:0.9rem;">
                    <div><strong>Actor:</strong> ${e.actor_nombre || 'N/A'}</div>
                    <div><strong>Ubicación:</strong> ${e.ubicacion || 'N/A'}</div>
                    <div><strong>Datos:</strong> ${JSON.stringify(e.datos_evento)}</div>
                </div>
                <div class="mt-1">
                    <div><strong>Hash:</strong> <span class="hash-display">${e.hash_evento}</span></div>
                    <div><strong>Hash anterior:</strong> <span class="hash-display">${e.hash_evento_pasado || 'GENESIS'}</span></div>
                    <div><strong>Integridad:</strong>
                        <span class="${eventoOk ? 'integrity-ok' : 'integrity-fail'}">
                            ${eventoOk ? '\u2705 OK' : '\u274C HASH NO COINCIDE'}
                        </span>
                    </div>
                </div>
                ${val ? `
                <div class="mt-1" style="font-size:0.85rem;">
                    <strong>Validación biométrica:</strong>
                    Firma: ${val.firma_ok ? '\u2705' : '\u274C'} |
                    Rostro: ${val.rostro_ok ? '\u2705' : '\u274C'} |
                    Voz: ${val.voz_ok ? '\u2705' : '\u274C'} |
                    <strong>${val.aprobado ? 'APROBADO' : 'RECHAZADO'}</strong>
                </div>
                ` : ''}
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// ── Integridad global ──

async function checkGlobalIntegrity() {
    const container = document.getElementById('integrity-results');
    container.innerHTML = '<p class="text-muted">Verificando integridad de todos los animales...</p>';

    try {
        const res = await apiFetch('/auditoria/integridad-global');
        if (!res.ok) {
            const err = await res.json();
            container.innerHTML = `<p class="text-muted">${err.detail || 'Error al verificar'}</p>`;
            return;
        }
        const data = await res.json();

        let html = `
            <div class="info-card mt-1">
                <h3>Resultado de Integridad Global</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">${data.total_animales}</div>
                        <div class="stat-label">Animales verificados</div>
                    </div>
                    <div class="stat-card" style="border-left-color:var(--success)">
                        <div class="stat-number" style="color:var(--success)">${data.cadenas_integras}</div>
                        <div class="stat-label">Cadenas íntegras</div>
                    </div>
                    <div class="stat-card" style="border-left-color:var(--danger)">
                        <div class="stat-number" style="color:var(--danger)">${data.cadenas_con_error}</div>
                        <div class="stat-label">Cadenas con error</div>
                    </div>
                </div>
            </div>
            <table class="mt-1">
                <thead>
                    <tr>
                        <th>Animal</th>
                        <th>Código</th>
                        <th>Eventos</th>
                        <th>Integridad</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.detalle.map(d => `
                        <tr>
                            <td>${d.nombre || 'Sin nombre'}</td>
                            <td>${d.codigo_unico}</td>
                            <td>${d.total_eventos}</td>
                            <td class="${d.cadena_integra ? 'integrity-ok' : 'integrity-fail'}">
                                ${d.cadena_integra ? '\u2705 Íntegra' : '\u274C Error'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<p class="text-muted">Error de conexión</p>';
    }
}

// ── Bitácora ──

async function loadBitacora() {
    const container = document.getElementById('bitacora-list');
    try {
        const res = await apiFetch('/auditoria/bitacora');
        if (!res.ok) {
            const err = await res.json();
            container.innerHTML = `<p class="text-muted">${err.detail || 'Sin acceso a bitácora'}</p>`;
            return;
        }
        const data = await res.json();

        if (data.length === 0) {
            container.innerHTML = '<p class="text-muted">No hay registros en la bitácora.</p>';
            return;
        }

        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Usuario</th>
                        <th>Acción</th>
                        <th>Resultado</th>
                        <th>IP</th>
                        <th>Detalle</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(e => `
                        <tr>
                            <td>${new Date(e.ocurrido_en).toLocaleString('es')}</td>
                            <td>${e.usuario_nombre || 'Sistema'}</td>
                            <td>${e.accion}</td>
                            <td>
                                <span class="badge" style="background:${e.resultado === 'exitoso' ? 'var(--success)' : e.resultado === 'rechazado' ? 'var(--danger)' : 'var(--warning)'}; color:white;">
                                    ${e.resultado}
                                </span>
                            </td>
                            <td>${e.ip_origen || 'N/A'}</td>
                            <td><small>${e.detalle ? JSON.stringify(e.detalle).substring(0, 50) + '...' : 'N/A'}</small></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        container.innerHTML = '<p class="text-muted">Error de conexión</p>';
    }
}

// ── Alertas ──

async function loadAlerts() {
    const container = document.getElementById('alerts-list');
    try {
        const res = await apiFetch('/auditoria/alertas');
        if (!res.ok) {
            const err = await res.json();
            container.innerHTML = `<p class="text-muted">${err.detail || 'Sin acceso a alertas'}</p>`;
            return;
        }
        const data = await res.json();

        if (data.length === 0) {
            container.innerHTML = '<p class="text-muted" style="color:var(--success)">No hay alertas de validación biométrica fallida.</p>';
            return;
        }

        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Usuario</th>
                        <th>Rol</th>
                        <th>IP</th>
                        <th>Detalle</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(a => `
                        <tr style="background:#fff5f5;">
                            <td>${new Date(a.ocurrido_en).toLocaleString('es')}</td>
                            <td>${a.usuario}</td>
                            <td>${a.rol}</td>
                            <td>${a.ip_origen || 'N/A'}</td>
                            <td><small>${a.detalle ? JSON.stringify(a.detalle) : 'N/A'}</small></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        container.innerHTML = '<p class="text-muted">Error de conexión</p>';
    }
}
