function actualizarInventarios() {

    const select =
        document.getElementById('paquete_id');

    const selected =
        select.options[select.selectedIndex];

    const inventarioPaq =
        selected.getAttribute('data-paquetes');

    const inventarioUnd =
        selected.getAttribute('data-unidades');

    const inventario =
        selected.getAttribute('data-inventario');

    document.getElementById('inventario-actual').textContent =
        'Inventario: ' + (inventario ?? '');

    document.getElementById('inventario-paq').textContent =
        'Inventario en paquetes: ' + (inventarioPaq ?? '');

    document.getElementById('inventario-und').textContent =
        'Inventario en unidades: ' + (inventarioUnd ?? '');
}


function inicializarEventos() {

    const paqueteSelect =
        document.getElementById('paquete_id');

    if (paqueteSelect) {

        paqueteSelect.addEventListener(
            'change',
            actualizarInventarios
        );
    }
}


function cargarInventarioInicial() {

    actualizarInventarios();
}


if (typeof module !== "undefined") {

    module.exports = {
        actualizarInventarios,
        inicializarEventos,
        cargarInventarioInicial
    };
}