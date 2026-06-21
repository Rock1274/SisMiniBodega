function validarUnidades(tipo, unidades, errorDiv, boton) {

    const tipoSeleccionado = parseInt(tipo.value) || 0;
    const unidadesValor = parseInt(unidades.value) || 0;

    unidades.max = tipoSeleccionado;

    if (unidadesValor > tipoSeleccionado) {
        errorDiv.textContent =
            `No pueden sobrar ${unidadesValor} unidades en un paquete de ${tipoSeleccionado} unidades`;

        unidades.classList.add("is-invalid");
        boton.disabled = true;

        return false;
    } else {
        errorDiv.textContent = "";
        unidades.classList.remove("is-invalid");
        boton.disabled = false;

        return true;
    }
}

module.exports = { validarUnidades };