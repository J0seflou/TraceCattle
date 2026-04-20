/* ══════════ Gestión de Animales ══════════ */

function showAnimalForm() {
    document.getElementById('animal-form-container').classList.remove('hidden');
    loadParentSelects();
}

function hideAnimalForm() {
    document.getElementById('animal-form-container').classList.add('hidden');
    document.getElementById('form-animal').reset();
    // Restaurar visibilidad de campos genealógicos al cerrar
    document.getElementById('campos-genealogicos').style.display = 'block';
    document.getElementById('campo-padre').style.display = 'block';
    document.getElementById('campo-pajilla').style.display = 'none';
}

function togglePadreField(inseminadaChecked) {
    document.getElementById('campo-pajilla').style.display = inseminadaChecked ? 'block' : 'none';
    if (!inseminadaChecked) {
        document.getElementById('animal-pajilla').value = '';
    }
}

function toggleOrigenDesconocido(checked) {
    const campos = document.getElementById('campos-genealogicos');
    campos.style.display = checked ? 'none' : 'block';
    if (checked) {
        document.getElementById('animal-madre').value = '';
        document.getElementById('animal-padre').value = '';
        document.getElementById('animal-inseminada').checked = false;
        document.getElementById('campo-pajilla').style.display = 'none';
        document.getElementById('animal-pajilla').value = '';
    }
}

async function loadParentSelects() {
    try {
        const fp = typeof adminFincaParam === 'function' ? adminFincaParam() : '';
        const res = await apiFetch(`/animales/${fp}`);
        if (!res.ok) return;
        const animals = await res.json();

        const madreSelect = document.getElementById('animal-madre');
        const padreSelect = document.getElementById('animal-padre');

        madreSelect.innerHTML = '<option value="">Sin registrar</option>';
        padreSelect.innerHTML = '<option value="">Sin registrar</option>';

        animals.forEach(a => {
            const label = `${a.codigo_unico} - ${a.nombre || a.especie}`;
            // Hembras para madre
            if (a.sexo === 'H' || !a.sexo) {
                madreSelect.innerHTML += `<option value="${a.id_animales}">${label}</option>`;
            }
            // Machos para padre
            if (a.sexo === 'M' || !a.sexo) {
                padreSelect.innerHTML += `<option value="${a.id_animales}">${label}</option>`;
            }
        });
    } catch (e) { /* silent */ }
}

async function loadAnimals() {
    try {
        const fp = typeof adminFincaParam === 'function' ? adminFincaParam() : '';
        const res = await apiFetch(`/animales/${fp}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || 'Error cargando animales', 'error');
            return;
        }
        const animals = await res.json();
        renderAnimalsList(animals);
    } catch (e) {
        showToast('Error cargando animales', 'error');
    }
}

function renderAnimalsList(animals) {
    const container = document.getElementById('animals-list');
    if (animals.length === 0) {
        const sinFinca = state.user && !state.user.finca;
        container.innerHTML = sinFinca
            ? '<p class="text-muted">No perteneces a ninguna finca. No tienes animales visibles.</p>'
            : '<p class="text-muted">No hay animales registrados.</p>';
        return;
    }
    container.innerHTML = animals.map(a => `
        <div class="animal-card">
            <h4>${a.nombre || 'Sin nombre'} - ${a.codigo_unico}</h4>
            <div class="animal-info">
                <div><strong>Especie:</strong> ${a.especie}</div>
                <div><strong>Raza:</strong> ${a.raza || 'N/A'}</div>
                <div><strong>Sexo:</strong> ${a.sexo === 'M' ? 'Macho' : a.sexo === 'H' ? 'Hembra' : 'N/A'}</div>
                <div><strong>Peso:</strong> ${a.peso_kg ? a.peso_kg + ' kg' : 'N/A'}</div>
                <div><strong>Propietario:</strong> ${a.propietario_nombre || 'N/A'}</div>
                <div><strong>Estado:</strong> ${a.activo ? '<span style="color:var(--success)">Activo</span>' : '<span style="color:var(--danger)">Inactivo</span>'}</div>
                ${a.origen_desconocido
                    ? '<div><strong>Origen:</strong> <span style="color:#b45309;">Desconocido</span></div>'
                    : `<div><strong>Madre:</strong> ${a.madre_nombre || 'No registrada'}</div>
                       <div><strong>Padre:</strong> ${a.padre_nombre || 'No registrado'}</div>
                       ${a.es_inseminada ? `<div><strong>Inseminación artificial:</strong> Sí${a.info_pajilla ? ` — <em>${a.info_pajilla}</em>` : ''}</div>` : ''}`
                }
            </div>
            <div class="animal-actions">
                ${state.user && (state.user.rol_nombre === 'auditor' || state.user.rol_nombre === 'admin') ? `<button class="btn btn-sm btn-outline" onclick="viewAnimalHistory('${a.id_animales}')">Ver historial</button>` : ''}
                <button class="btn btn-sm btn-outline" onclick="viewAnimalDetail('${a.id_animales}')">Ver detalle</button>
            </div>
        </div>
    `).join('');
}

async function viewAnimalDetail(animalId) {
    try {
        const res = await apiFetch(`/animales/${animalId}`);
        if (!res.ok) return;
        const a = await res.json();

        let hermanos_html = '';
        if (a.hermanos && a.hermanos.length > 0) {
            hermanos_html = `
                <div class="mt-1">
                    <strong>Hermanos:</strong>
                    <ul style="margin:0.5rem 0; padding-left:1.5rem;">
                        ${a.hermanos.map(h => `<li>${h.nombre} (${h.relacion})</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        const container = document.getElementById('animals-list');
        container.innerHTML = `
            <div class="info-card">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                    <h3>${a.nombre || 'Sin nombre'} - ${a.codigo_unico}</h3>
                    <button class="btn btn-sm btn-outline" onclick="loadAnimals()">Volver a lista</button>
                </div>
                <div class="mt-1" style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;">
                    <div><strong>Especie:</strong> ${a.especie}</div>
                    <div><strong>Raza:</strong> ${a.raza || 'N/A'}</div>
                    <div><strong>Sexo:</strong> ${a.sexo === 'M' ? 'Macho' : a.sexo === 'H' ? 'Hembra' : 'N/A'}</div>
                    <div><strong>Peso:</strong> ${a.peso_kg ? a.peso_kg + ' kg' : 'N/A'}</div>
                    <div><strong>Color:</strong> ${a.color || 'N/A'}</div>
                    <div><strong>Fecha nacimiento:</strong> ${a.fecha_nacimiento || 'N/A'}</div>
                    <div><strong>Propietario:</strong> ${a.propietario_nombre || 'N/A'}</div>
                    <div><strong>Estado:</strong> ${a.activo ? 'Activo' : 'Inactivo'}</div>
                </div>
                <div class="mt-1" style="border-top:1px solid var(--border); padding-top:1rem;">
                    <h4 style="color:var(--primary-dark);">Trazabilidad Genealógica</h4>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem; margin-top:0.5rem;">
                        <div><strong>Madre:</strong> ${a.madre_nombre || 'No registrada'}</div>
                        <div><strong>Padre:</strong> ${a.padre_nombre || 'No registrado'}</div>
                        <div><strong>Inseminación artificial:</strong> ${a.es_inseminada ? 'Sí' : 'No'}</div>
                        ${a.es_inseminada && a.info_pajilla ? `<div><strong>Pajilla:</strong> ${a.info_pajilla}</div>` : ''}
                    </div>
                    ${hermanos_html}
                </div>
                ${state.user && (state.user.rol_nombre === 'auditor' || state.user.rol_nombre === 'admin') ? `
                <div class="mt-1" style="display:flex; gap:0.5rem;">
                    <button class="btn btn-sm btn-primary" onclick="viewAnimalHistory('${a.id_animales}')">Ver historial de eventos</button>
                </div>` : ''}
            </div>
        `;
    } catch (e) {
        showToast('Error cargando detalle del animal', 'error');
    }
}

async function viewAnimalHistory(animalId) {
    // Cambiar a sección de auditoría y cargar historial
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('[data-target="section-audit"]').classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById('section-audit').classList.add('active');

    showAuditTab(null, 'audit-history');
    await loadAnimalsForAudit();
    document.getElementById('audit-animal-select').value = animalId;
    loadAnimalAudit();
}

document.getElementById('form-animal').addEventListener('submit', async (e) => {
    e.preventDefault();

    const origenDesconocido = document.getElementById('animal-origen-desconocido').checked;
    const madreId = document.getElementById('animal-madre').value || null;
    const padreId = document.getElementById('animal-padre').value || null;
    const esInseminada = document.getElementById('animal-inseminada').checked;

    // Validar trazabilidad genealógica
    if (!origenDesconocido && !madreId && !padreId && !esInseminada) {
        showToast('La trazabilidad genealógica es obligatoria: indique la madre, el padre, si es inseminada, o marque "Se desconoce el origen del animal".', 'error');
        document.getElementById('campos-genealogicos').scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
    }

    const body = {
        codigo_unico: document.getElementById('animal-codigo').value.trim(),
        especie: document.getElementById('animal-especie').value.trim(),
        raza: document.getElementById('animal-raza').value.trim(),
        nombre: document.getElementById('animal-nombre').value.trim(),
        fecha_nacimiento: document.getElementById('animal-fecha').value,
        sexo: document.getElementById('animal-sexo').value,
        peso_kg: parseFloat(document.getElementById('animal-peso').value),
        color: document.getElementById('animal-color').value.trim(),
        marcas: document.getElementById('animal-marcas').value || null,
        madre_id: madreId,
        padre_id: padreId,
        es_inseminada: esInseminada,
        info_pajilla: esInseminada ? (document.getElementById('animal-pajilla').value.trim() || null) : null,
        origen_desconocido: origenDesconocido,
    };

    try {
        const res = await apiFetch('/animales/', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        const data = await res.json();

        if (res.ok) {
            showToast('Animal registrado exitosamente', 'success');
            hideAnimalForm();
            await loadAnimals();
            document.getElementById('animals-list').scrollIntoView({ behavior: 'smooth', block: 'start' });
            loadDashboardStats();
        } else {
            const msg = Array.isArray(data.detail)
                ? data.detail.map(d => d.msg).join(', ')
                : (data.detail || 'Error al registrar animal');
            showToast(msg, 'error');
        }
    } catch (err) {
        showToast('Error de conexión', 'error');
    }
});
