function actualizarInventario(paqueteSelect) {

    const selected = paqueteSelect.options[paqueteSelect.selectedIndex];

    const inventarioPaq = selected.getAttribute('dv-data-paquetes');
    const inventarioUnd = selected.getAttribute('dv-data-unidades');
    const inventario = selected.getAttribute('dv-data-inventario');

    document.getElementById('dv-inventario-actual').textContent =
        'Inventario: ' + inventario;

    document.getElementById('dv-inventario-paq').textContent =
        'Inventario en paquetes: ' + inventarioPaq;

    document.getElementById('dv-inventario-und').textContent =
        'Inventario en unidades: ' + inventarioUnd;

    document.getElementById('dv_paquetes_finales').max =
        inventarioPaq;
}


function validateUnidades(
    paqueteSelect,
    unidadesInput,
    unidadesError,
    submitButton
) {

    const selectedOption =
        paqueteSelect.options[paqueteSelect.selectedIndex];

    const tipoPaquete =
        selectedOption
            ? parseInt(selectedOption.getAttribute('dv-data-tipo')) || 0
            : 0;

    const unidades =
        parseInt(unidadesInput.value) || 0;

    unidadesInput.max = tipoPaquete;

    if (unidades > tipoPaquete) {

        unidadesError.textContent =
            `No pueden sobrar ${unidades} unidades en un paquete de ${tipoPaquete} unidades`;

        unidadesInput.classList.add('is-invalid');

        submitButton.disabled = true;

        return false;
    }

    unidadesError.textContent = '';

    unidadesInput.classList.remove('is-invalid');

    submitButton.disabled = false;

    return true;
}


function resetFormulario() {

    const form =
        document.querySelector('#crearDetVentaModal form');

    if (form) {
        form.reset();
    }

    const errorContainer =
        document.getElementById('error-container');

    if (errorContainer) {
        errorContainer.innerHTML = '';
    }

    const inventarioActual =
        document.getElementById('dv-inventario-actual');

    if (inventarioActual) {
        inventarioActual.textContent =
            'Seleccione un paquete para ver el inventario.';
    }

    const inventarioPaq =
        document.getElementById('dv-inventario-paq');

    if (inventarioPaq) {
        inventarioPaq.textContent = '';
    }

    const inventarioUnd =
        document.getElementById('dv-inventario-und');

    if (inventarioUnd) {
        inventarioUnd.textContent = '';
    }
}


if (typeof module !== "undefined") {

    module.exports = {
        actualizarInventario,
        validateUnidades,
        resetFormulario
    };
}