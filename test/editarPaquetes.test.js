/**
 * @jest-environment jsdom
 */

const {
    initializeUnidadesValidation,
    formSubmitHandler
} = require('../static/js/editarpaquetes');

describe('Validación de Paquetes', () => {

    beforeEach(() => {
        document.body.innerHTML = `
            <form>
                <select id="TipoPaquete">
                    <option value="6">6</option>
                    <option value="12">12</option>
                </select>

                <input id="UnidadesSobrantes" type="number" />
                <div id="unidades-error"></div>

                <button type="submit">Guardar</button>
            </form>
        `;
    });

    test('Debe actualizar max según tipo seleccionado', () => {
        initializeUnidadesValidation();

        const tipo = document.getElementById('TipoPaquete');
        const unidades = document.getElementById('UnidadesSobrantes');

        tipo.value = '12';
        tipo.dispatchEvent(new Event('change'));

        expect(unidades.max).toBe('12');
    });

    test('Debe mostrar error si unidades exceden el tipo', () => {
        initializeUnidadesValidation();

        const tipo = document.getElementById('TipoPaquete');
        const unidades = document.getElementById('UnidadesSobrantes');
        const error = document.getElementById('unidades-error');
        const button = document.querySelector('button');

        tipo.value = '6';
        unidades.value = '10';

        unidades.dispatchEvent(new Event('input'));

        expect(error.textContent).toContain('No pueden sobrar');
        expect(unidades.classList.contains('is-invalid')).toBe(true);
        expect(button.disabled).toBe(true);
    });

    test('Debe limpiar error si valores son válidos', () => {
        initializeUnidadesValidation();

        const tipo = document.getElementById('TipoPaquete');
        const unidades = document.getElementById('UnidadesSobrantes');
        const error = document.getElementById('unidades-error');
        const button = document.querySelector('button');

        tipo.value = '12';
        unidades.value = '5';

        unidades.dispatchEvent(new Event('input'));

        expect(error.textContent).toBe('');
        expect(unidades.classList.contains('is-invalid')).toBe(false);
        expect(button.disabled).toBe(false);
    });

    test('Debe prevenir submit si hay error', () => {
        const preventDefault = jest.fn();

        document.body.innerHTML = `
            <form>
                <select id="TipoPaquete">
                    <option value="6" selected>6</option>
                </select>

                <input id="UnidadesSobrantes" value="10" />
            </form>
        `;

        global.alert = jest.fn();

        formSubmitHandler({ preventDefault });

        expect(preventDefault).toHaveBeenCalled();
        expect(global.alert).toHaveBeenCalled();
    });

    test('No debe fallar si faltan elementos', () => {
        document.body.innerHTML = `<div></div>`;

        expect(() => {
            initializeUnidadesValidation();
        }).not.toThrow();
    });

});