// FILTRAR NOTAS
function filtrarNotas(filtro, notas) {
    notas.forEach(nota => {
        const estado = nota.getAttribute('data-estado');

        if (filtro === 'todas') {
            nota.style.display = 'block';
        } else if (filtro === 'pendientes' && estado === 'pendiente') {
            nota.style.display = 'block';
        } else if (filtro === 'completadas' && estado === 'completada') {
            nota.style.display = 'block';
        } else {
            nota.style.display = 'none';
        }
    });
}


// CAMBIAR ESTADO VISUAL
function actualizarEstadoNota(notaItem, completada) {
    const titulo = notaItem.querySelector('h6');

    if (completada) {
        notaItem.classList.add('nota-completada');
        notaItem.setAttribute('data-estado', 'completada');
        titulo.classList.add('text-decoration-line-through', 'text-muted');
    } else {
        notaItem.classList.remove('nota-completada');
        notaItem.setAttribute('data-estado', 'pendiente');
        titulo.classList.remove('text-decoration-line-through', 'text-muted');
    }
}


// PETICIÓN PARA MARCAR NOTA
function marcarNota(notaId, completada) {
    return fetch('/marcar_nota', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            nota_id: notaId,
            completada: completada
        })
    }).then(res => res.json());
}


// ELIMINAR NOTA
function eliminarNotaRequest(notaId) {
    return fetch('/eliminar_nota', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ nota_id: notaId })
    }).then(res => res.json());
}


// INICIALIZADOR (para usar en HTML)
function initNotas() {

    const filtroSelect = document.getElementById('filtroEstado');

    if (filtroSelect) {
        filtroSelect.addEventListener('change', function () {
            const notas = document.querySelectorAll('.nota-item');
            filtrarNotas(this.value, notas);
        });
    }

    document.addEventListener('change', function (e) {
        if (e.target.classList.contains('nota-checkbox')) {

            const notaId = e.target.getAttribute('data-nota-id');
            const completada = e.target.checked;
            const notaItem = e.target.closest('.nota-item');

            marcarNota(notaId, completada)
                .then(data => {
                    if (data.success) {
                        actualizarEstadoNota(notaItem, completada);
                    }
                })
                .catch(() => {
                    e.target.checked = !completada;
                });
        }
    });
}


// EXPORT PARA TEST
if (typeof module !== "undefined") {
    module.exports = {
        filtrarNotas,
        actualizarEstadoNota,
        marcarNota,
        eliminarNotaRequest
    };
}