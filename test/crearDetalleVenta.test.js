/**
 * @jest-environment jsdom
 */

const {
    actualizarInventario,
    validateUnidades,
    resetFormulario
} = require('../static/js/crearDetalleVenta');


test("actualizarInventario actualiza textos correctamente", () => {

    document.body.innerHTML = `
        <select id="dv_paquete_id">
            <option
                dv-data-paquetes="10"
                dv-data-unidades="5"
                dv-data-inventario="125"
                selected>
                Coca Cola
            </option>
        </select>

        <small id="dv-inventario-actual"></small>
        <small id="dv-inventario-paq"></small>
        <small id="dv-inventario-und"></small>

        <input id="dv_paquetes_finales">
    `;

    const paqueteSelect =
        document.getElementById("dv_paquete_id");

    actualizarInventario(paqueteSelect);

    expect(
        document.getElementById("dv-inventario-actual").textContent
    ).toBe("Inventario: 125");

    expect(
        document.getElementById("dv-inventario-paq").textContent
    ).toBe("Inventario en paquetes: 10");

    expect(
        document.getElementById("dv-inventario-und").textContent
    ).toBe("Inventario en unidades: 5");

    expect(
        document.getElementById("dv_paquetes_finales").max
    ).toBe("10");
});


test("validateUnidades bloquea cantidades inválidas", () => {

    document.body.innerHTML = `
        <select id="dv_paquete_id">
            <option
                dv-data-tipo="12"
                selected>
                Coca Cola
            </option>
        </select>

        <input id="dv_unidades_finales" value="20">

        <div id="dv-unidades-error"></div>

        <button class="btn_guardar_dv"></button>
    `;

    const paquete =
        document.getElementById("dv_paquete_id");

    const unidades =
        document.getElementById("dv_unidades_finales");

    const error =
        document.getElementById("dv-unidades-error");

    const boton =
        document.querySelector(".btn_guardar_dv");

    const resultado =
        validateUnidades(
            paquete,
            unidades,
            error,
            boton
        );

    expect(resultado).toBe(false);

    expect(error.textContent)
        .toContain("No pueden sobrar");

    expect(boton.disabled).toBe(true);
});


test("resetFormulario limpia formulario y mensajes", () => {

    document.body.innerHTML = `
        <div id="crearDetVentaModal">
            <form>
                <input value="123">
            </form>
        </div>

        <div id="error-container">
            Error
        </div>

        <small id="dv-inventario-actual">
            Inventario: 100
        </small>

        <small id="dv-inventario-paq">
            Inventario en paquetes: 10
        </small>

        <small id="dv-inventario-und">
            Inventario en unidades: 5
        </small>
    `;

    resetFormulario();

    expect(
        document.getElementById("error-container").innerHTML
    ).toBe("");

    expect(
        document.getElementById("dv-inventario-actual").textContent
    ).toBe("Seleccione un paquete para ver el inventario.");

    expect(
        document.getElementById("dv-inventario-paq").textContent
    ).toBe("");

    expect(
        document.getElementById("dv-inventario-und").textContent
    ).toBe("");
});