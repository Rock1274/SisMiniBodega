/**
 * @jest-environment jsdom
 */

const {
    togglePasswordVisibility,
    verificarRecuerdame
} = require("../static/js/login");


// 🔥 TEST MOSTRAR PASSWORD
test("togglePasswordVisibility cambia password a text", () => {

    document.body.innerHTML = `
        <input type="password" id="contrasena">
        <i class="fa-eye"></i>
    `;

    const input = document.getElementById("contrasena");
    const icono = document.querySelector("i");

    const resultado =
        togglePasswordVisibility(input, icono);

    expect(resultado).toBe("text");
    expect(input.type).toBe("text");
});


// 🔥 TEST OCULTAR PASSWORD
test("togglePasswordVisibility vuelve text a password", () => {

    document.body.innerHTML = `
        <input type="text" id="contrasena">
        <i class="fa-eye-slash"></i>
    `;

    const input = document.getElementById("contrasena");
    const icono = document.querySelector("i");

    const resultado =
        togglePasswordVisibility(input, icono);

    expect(resultado).toBe("password");
    expect(input.type).toBe("password");
});


// 🔥 TEST CHECKBOX ACTIVADO
test("verificarRecuerdame devuelve true", () => {

    document.body.innerHTML = `
        <input type="checkbox" id="Recuerdame" checked>
    `;

    const checkbox =
        document.getElementById("Recuerdame");

    expect(
        verificarRecuerdame(checkbox)
    ).toBe(true);
});


// 🔥 TEST CHECKBOX DESACTIVADO
test("verificarRecuerdame devuelve false", () => {

    document.body.innerHTML = `
        <input type="checkbox" id="Recuerdame">
    `;

    const checkbox =
        document.getElementById("Recuerdame");

    expect(
        verificarRecuerdame(checkbox)
    ).toBe(false);
});