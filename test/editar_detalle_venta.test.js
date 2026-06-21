/**
 * @jest-environment jsdom
 */

const {
    actualizarInventarios,
    inicializarEventos,
    cargarInventarioInicial
} = require('../static/js/editar_detalle_venta');


test("actualizarInventarios actualiza el DOM", () => {

    document.body.innerHTML = `
        <select id="paquete_id">
            <option
                data-paquetes="20"
                data-unidades="8"
                data-inventario="200"
                selected>
                Coca Cola
            </option>
        </select>

        <small id="inventario-actual"></small>
        <small id="inventario-paq"></small>
        <small id="inventario-und"></small>
    `;

    actualizarInventarios();

    expect(
        document.getElementById('inventario-actual').textContent
    ).toBe('Inventario: 200');

    expect(
        document.getElementById('inventario-paq').textContent
    ).toBe('Inventario en paquetes: 20');

    expect(
        document.getElementById('inventario-und').textContent
    ).toBe('Inventario en unidades: 8');
});


test("cargarInventarioInicial ejecuta actualizarInventarios", () => {

    document.body.innerHTML = `
        <select id="paquete_id">
            <option
                data-paquetes="10"
                data-unidades="5"
                data-inventario="100"
                selected>
                Pepsi
            </option>
        </select>

        <small id="inventario-actual"></small>
        <small id="inventario-paq"></small>
        <small id="inventario-und"></small>
    `;

    cargarInventarioInicial();

    expect(
        document.getElementById('inventario-actual').textContent
    ).toContain('100');
});


test("inicializarEventos ejecuta actualización al cambiar producto", () => {

    document.body.innerHTML = `
        <select id="paquete_id">
            <option
                data-paquetes="50"
                data-unidades="12"
                data-inventario="500"
                selected>
                Fanta
            </option>
        </select>

        <small id="inventario-actual"></small>
        <small id="inventario-paq"></small>
        <small id="inventario-und"></small>
    `;

    inicializarEventos();

    const select =
        document.getElementById('paquete_id');

    select.dispatchEvent(new Event('change'));

    expect(
        document.getElementById('inventario-paq').textContent
    ).toBe('Inventario en paquetes: 50');
});