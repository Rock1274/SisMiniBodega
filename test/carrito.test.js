/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

// Simular HTML
document.body.innerHTML = `
<div id="carrito_container" data-id="1"></div>
<table id="carrito_tabla"><tbody></tbody></table>
<input id="cant_10" value="2">
`;

// Importar funciones (si usas módulos)
const carritoJS = fs.readFileSync(
    path.resolve(__dirname, "../static/js/carrito.js"),
    "utf8"
);

// Ejecutar el script en este contexto
eval(carritoJS);


//MOCK FETCH
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        text: () => Promise.resolve(`
            <table id="carrito_tabla">
                <tbody>
                    <tr><td>Producto Test</td></tr>
                </tbody>
            </table>
        `)
    })
);


// =========================
// TESTS
// =========================

test("agregarProducto hace fetch correcto", async () => {

    await agregarProducto(10);

    expect(fetch).toHaveBeenCalledWith(
        "/carrito/1/agregar",
        expect.objectContaining({
            method: "POST"
        })
    );
});


test("eliminarProducto hace fetch correcto", async () => {

    await eliminarProducto(5);

    expect(fetch).toHaveBeenCalledWith(
        "/carrito/1/eliminar/5",
        expect.objectContaining({
            method: "DELETE"
        })
    );
});


test("actualizarCarrito actualiza el DOM", async () => {

    await actualizarCarrito(1);

    const tabla = document.querySelector("#carrito_tabla");

    expect(tabla.innerHTML).toContain("Producto Test");
});