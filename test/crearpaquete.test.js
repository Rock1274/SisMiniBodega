/**
 * @jest-environment jsdom
 */

const { validarUnidades } = require("../static/js/crearPaquete.testable");

test("unidades válidas → sin error", () => {

    document.body.innerHTML = `
        <select id="tipo">
            <option value="12" selected>12</option>
        </select>

        <input id="UnidadesSobrantes" value="5">
        <div id="unidades-error"></div>
        <button type="submit"></button>
    `;

    const tipo = document.getElementById("tipo");
    const unidades = document.getElementById("UnidadesSobrantes");
    const error = document.getElementById("unidades-error");
    const boton = document.querySelector("button");

    const resultado = validarUnidades(tipo, unidades, error, boton);

    expect(resultado).toBe(true);
    expect(error.textContent).toBe("");
    expect(boton.disabled).toBe(false);
});