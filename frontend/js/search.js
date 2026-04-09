/* ══════════ Búsqueda Global de Animales y Eventos ══════════ */

// Estado de búsqueda
const searchState = {
    lastResults: null,
    lastType: null,
};

// Inicializar filtros dinámicos basado en tipo de búsqueda
function initializeSearchFilters() {
    const searchType = document.getElementById('search-type');
    updateSearchFiltersVisibility();
    searchType.addEventListener('change', updateSearchFiltersVisibility);
}

// Mostrar/ocultar filtros según el tipo de búsqueda
function updateSearchFiltersVisibility() {
    const searchType = document.getElementById('search-type').value;
    const animalFilters = document.getElementById('search-animal-filters');
    const eventFilters = document.getElementById('search-event-filters');
    const dateFilters = document.getElementById('search-date-filters');

    if (searchType === 'animales') {
        animalFilters.classList.remove('hidden');
        eventFilters.classList.add('hidden');
        dateFilters.classList.add('hidden');
    } else if (searchType === 'eventos') {
        animalFilters.classList.add('hidden');
        eventFilters.classList.remove('hidden');
        dateFilters.classList.remove('hidden');
    } else {
        // todos
        animalFilters.classList.remove('hidden');
        eventFilters.classList.remove('hidden');
        dateFilters.classList.remove('hidden');
    }
}

// Realizar búsqueda
async function performSearch(event) {
    event.preventDefault();

    const searchType = document.getElementById('search-type').value;
    const searchQuery = document.getElementById('search-query').value.trim();
    const resultsContainer = document.getElementById('search-results');

    if (!searchQuery) {
        showToast('Ingrese un término de búsqueda', 'warning');
        return;
    }

    // Limpiar resultados previos
    resultsContainer.innerHTML = '<p class="text-muted">Buscando...</p>';

    try {
        let results = [];

        if (searchType === 'animales' || searchType === 'todos') {
            const animalResults = await searchAnimals();
            if (animalResults) {
                results.push({ type: 'animales', data: animalResults });
            }
        }

        if (searchType === 'eventos' || searchType === 'todos') {
            const eventResults = await searchEvents();
            if (eventResults) {
                results.push({ type: 'eventos', data: eventResults });
            }
        }

        searchState.lastResults = results;
        searchState.lastType = searchType;

        if (results.length === 0 || results.every(r => r.data.length === 0)) {
            resultsContainer.innerHTML = '<p class="text-muted">No se encontraron resultados.</p>';
            return;
        }

        renderSearchResults(results);
    } catch (e) {
        console.error('Error en búsqueda:', e);
        showToast('Error al realizar la búsqueda', 'error');
        resultsContainer.innerHTML = '<p class="text-danger">Error al realizar la búsqueda.</p>';
    }
}

// Buscar animales
async function searchAnimals() {
    const q = document.getElementById('search-query').value.trim();
    const especie = document.getElementById('search-especie').value.trim();
    const raza = document.getElementById('search-raza').value.trim();

    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (especie) params.append('especie', especie);
    if (raza) params.append('raza', raza);

    try {
        const res = await apiFetch(`/busqueda/animales?${params.toString()}`);
        if (!res.ok) {
            if (res.status === 404) return [];
            throw new Error('Error en búsqueda de animales');
        }
        return await res.json();
    } catch (e) {
        console.error('Error buscando animales:', e);
        showToast('Error al buscar animales', 'error');
        return [];
    }
}

// Buscar eventos
async function searchEvents() {
    const q = document.getElementById('search-query').value.trim();
    const tipoEvento = document.getElementById('search-tipo-evento').value.trim();
    const fechaDesde = document.getElementById('search-fecha-desde').value;
    const fechaHasta = document.getElementById('search-fecha-hasta').value;

    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (tipoEvento) params.append('tipo_evento', tipoEvento);
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);

    try {
        const res = await apiFetch(`/busqueda/eventos?${params.toString()}`);
        if (!res.ok) {
            if (res.status === 404) return [];
            throw new Error('Error en búsqueda de eventos');
        }
        return await res.json();
    } catch (e) {
        console.error('Error buscando eventos:', e);
        showToast('Error al buscar eventos', 'error');
        return [];
    }
}

// Renderizar resultados de búsqueda
function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    let html = '';

    for (const group of results) {
        if (group.type === 'animales') {
            html += renderAnimalResults(group.data);
        } else if (group.type === 'eventos') {
            html += renderEventResults(group.data);
        }
    }

    container.innerHTML = html;
}

// Renderizar resultados de animales como tarjetas
function renderAnimalResults(animals) {
    if (!animals || animals.length === 0) {
        return '<h3>Animales</h3><p class="text-muted">No se encontraron animales.</p>';
    }

    const cards = animals.map(a => `
        <div class="animal-card">
            <h4>${a.nombre || 'Sin nombre'} - ${a.codigo_unico}</h4>
            <div class="animal-info">
                <div><strong>Especie:</strong> ${a.especie}</div>
                <div><strong>Raza:</strong> ${a.raza || 'N/A'}</div>
                <div><strong>Sexo:</strong> ${a.sexo === 'M' ? 'Macho' : a.sexo === 'H' ? 'Hembra' : 'N/A'}</div>
                <div><strong>Peso:</strong> ${a.peso_kg ? a.peso_kg + ' kg' : 'N/A'}</div>
                <div><strong>Color:</strong> ${a.color || 'N/A'}</div>
                <div><strong>Propietario:</strong> ${a.propietario_nombre || 'N/A'}</div>
                <div><strong>Estado:</strong> ${a.activo ? '<span style="color:var(--success)">Activo</span>' : '<span style="color:var(--danger)">Inactivo</span>'}</div>
                <div><strong>Registrado:</strong> ${new Date(a.registrado_en).toLocaleDateString('es-ES')}</div>
            </div>
            <div class="animal-actions">
                <button class="btn btn-sm btn-outline" onclick="viewAnimalHistory('${a.id_animales}')">Ver historial</button>
            </div>
        </div>
    `).join('');

    return `<h3>Animales (${animals.length})</h3><div class="cards-grid">${cards}</div>`;
}

// Renderizar resultados de eventos como tabla
function renderEventResults(eventos) {
    if (!eventos || eventos.length === 0) {
        return '<h3>Eventos</h3><p class="text-muted">No se encontraron eventos.</p>';
    }

    const rows = eventos.map(e => `
        <tr>
            <td>${e.animal_info}</td>
            <td>${e.tipo_evento}</td>
            <td>${e.ubicacion || 'N/A'}</td>
            <td>${e.actor_nombre || 'N/A'}</td>
            <td>${new Date(e.registrado_en).toLocaleDateString('es-ES')}</td>
            <td><small title="${e.hash_evento}">${e.hash_evento?.substring(0, 8)}...</small></td>
        </tr>
    `).join('');

    return `
        <h3>Eventos (${eventos.length})</h3>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Animal</th>
                        <th>Tipo de evento</th>
                        <th>Ubicación</th>
                        <th>Actor</th>
                        <th>Fecha</th>
                        <th>Hash</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    `;
}
