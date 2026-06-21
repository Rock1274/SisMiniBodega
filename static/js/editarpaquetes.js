function initializeUnidadesValidation() {
    const tipoSelect = document.getElementById('TipoPaquete');
    const unidadesInput = document.getElementById('UnidadesSobrantes');
    const unidadesError = document.getElementById('unidades-error');
    const submitButton = document.querySelector('button[type="submit"]');

    if (!tipoSelect || !unidadesInput || !unidadesError || !submitButton) {
        return;
    }

    function validateUnidades() {
        const tipoSeleccionado = parseInt(tipoSelect.value) || 0;
        const unidades = parseInt(unidadesInput.value) || 0;

        unidadesInput.max = tipoSeleccionado;

        if (unidades > tipoSeleccionado) {
            unidadesError.textContent = `No pueden sobrar ${unidades} unidades en un paquete de ${tipoSeleccionado} unidades`;
            unidadesInput.classList.add('is-invalid');
            submitButton.disabled = true;
            return false;
        } else {
            unidadesError.textContent = '';
            unidadesInput.classList.remove('is-invalid');
            submitButton.disabled = false;
            return true;
        }
    }

    tipoSelect.removeEventListener('change', validateUnidades);
    unidadesInput.removeEventListener('input', validateUnidades);

    tipoSelect.addEventListener('change', validateUnidades);
    unidadesInput.addEventListener('input', validateUnidades);

    const form = document.querySelector('form');
    if (form) {
        form.removeEventListener('submit', formSubmitHandler);
        form.addEventListener('submit', formSubmitHandler);
    }

    validateUnidades();
}

function formSubmitHandler(e) {
    const tipoSelect = document.getElementById('TipoPaquete');
    const unidadesInput = document.getElementById('UnidadesSobrantes');

    if (!tipoSelect || !unidadesInput) return;

    const tipoSeleccionado = parseInt(tipoSelect.value) || 0;
    const unidades = parseInt(unidadesInput.value) || 0;

    if (unidades > tipoSeleccionado) {
        e.preventDefault();
        alert('Por favor, corrige los errores antes de enviar el formulario.');
    }
}

module.exports = {
    initializeUnidadesValidation,
    formSubmitHandler
};