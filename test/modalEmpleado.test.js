/**
 * @jest-environment jsdom
 */

const { initModalEmpleadoDetalles } = require('../static/js/modalempleado');

describe('Modal Empleado Detalles', () => {

    beforeEach(() => {
        document.body.innerHTML = `
            <div id="modalEmpleadoDetalles"></div>
            <div id="modalEmpleadoBody"></div>
        `;
    });

    test('Debe llenar el modal con datos correctos', () => {
        initModalEmpleadoDetalles();

        const modal = document.getElementById('modalEmpleadoDetalles');

        const button = document.createElement('button');
        button.setAttribute('data-nombres', 'Juan');
        button.setAttribute('data-apellidos', 'Perez');
        button.setAttribute('data-edad', '30');
        button.setAttribute('data-fecha-fin', '2025-12-01');
        button.setAttribute('data-supervisor-nombre', 'Carlos');
        button.setAttribute('data-supervisor-apellido', 'Lopez');
        button.setAttribute('data-estado', 'Activo');

        const event = new Event('show.bs.modal');
        event.relatedTarget = button;

        modal.dispatchEvent(event);

        const body = document.getElementById('modalEmpleadoBody');

        expect(body.innerHTML).toContain('Juan Perez');
        expect(body.innerHTML).toContain('30 años');
        expect(body.innerHTML).toContain('Activo ✅');
        expect(body.innerHTML).toContain('2025-12-01');
        expect(body.innerHTML).toContain('Carlos Lopez');
    });

    test('Debe mostrar "No especificada" si fechaFin es null', () => {
        initModalEmpleadoDetalles();

        const modal = document.getElementById('modalEmpleadoDetalles');

        const button = document.createElement('button');
        button.setAttribute('data-nombres', 'Ana');
        button.setAttribute('data-apellidos', 'Gomez');
        button.setAttribute('data-edad', '25');
        button.setAttribute('data-fecha-fin', '');
        button.setAttribute('data-supervisor-nombre', '');
        button.setAttribute('data-supervisor-apellido', '');
        button.setAttribute('data-estado', 'Inactivo');

        const event = new Event('show.bs.modal');
        event.relatedTarget = button;

        modal.dispatchEvent(event);

        const body = document.getElementById('modalEmpleadoBody');

        expect(body.innerHTML).toContain('No especificada');
        expect(body.innerHTML).toContain('Nadie');
        expect(body.innerHTML).toContain('Inactivo ❌');
    });

    test('No debe fallar si el modal no existe', () => {
        document.body.innerHTML = `<div></div>`;

        expect(() => {
            initModalEmpleadoDetalles();
        }).not.toThrow();
    });

});