function initModalEmpleadoDetalles() {
    const modal = document.getElementById('modalEmpleadoDetalles');
    if (!modal) return;

    modal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;

        const nombres = button.getAttribute('data-nombres');
        const apellidos = button.getAttribute('data-apellidos');
        const edad = button.getAttribute('data-edad');
        const fechaNacimiento = button.getAttribute('data-fecha-nacimiento');
        const fechaContrato = button.getAttribute('data-fecha-contrato');
        const fechaFin = button.getAttribute('data-fecha-fin');
        const direccion = button.getAttribute('data-direccion');
        const supervisorNombre = button.getAttribute('data-supervisor-nombre');
        const supervisorApellido = button.getAttribute('data-supervisor-apellido');
        const estado = button.getAttribute('data-estado');
        const cedula = button.getAttribute('data-cedula');
        const estadoCivil = button.getAttribute('data-estado-civil');
        const sexo = button.getAttribute('data-sexo');
        const inss = button.getAttribute('data-inss');
        const ruc = button.getAttribute('data-ruc');
        const salario = button.getAttribute('data-salario');

        const body = document.getElementById('modalEmpleadoBody');

        body.innerHTML = `
            <h5>${nombres} ${apellidos}</h5>
            <p>${edad} años</p>
            <p>${estado === 'Activo' ? 'Activo ✅' : 'Inactivo ❌'}</p>
            <p>${(fechaFin && fechaFin !== 'None' && fechaFin.trim() !== '') ? fechaFin : 'No especificada'}</p>
            <p>${supervisorNombre && supervisorApellido ? supervisorNombre + ' ' + supervisorApellido : 'Nadie'}</p>
        `;
    });
}

module.exports = { initModalEmpleadoDetalles };