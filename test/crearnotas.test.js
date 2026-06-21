/**
 * @jest-environment jsdom
 */

const {
    filtrarNotas,
    actualizarEstadoNota
} = require("../static/js/crearnota");


// TEST FILTRO
test("filtrarNotas muestra solo pendientes", () => {

    document.body.innerHTML = `
        <div class="nota-item" data-estado="pendiente"></div>
        <div class="nota-item" data-estado="completada"></div>
    `;

    const notas = document.querySelectorAll(".nota-item");

    filtrarNotas("pendientes", notas);

    expect(notas[0].style.display).toBe("block");
    expect(notas[1].style.display).toBe("none");
});


// TEST ACTUALIZAR ESTADO
test("actualizarEstadoNota marca como completada", () => {

    document.body.innerHTML = `
        <div class="nota-item" data-estado="pendiente">
            <h6></h6>
        </div>
    `;

    const nota = document.querySelector(".nota-item");

    actualizarEstadoNota(nota, true);

    expect(nota.classList.contains("nota-completada")).toBe(true);
    expect(nota.getAttribute("data-estado")).toBe("completada");
});


// TEST DESMARCAR
test("actualizarEstadoNota vuelve a pendiente", () => {

    document.body.innerHTML = `
        <div class="nota-item nota-completada" data-estado="completada">
            <h6 class="text-decoration-line-through text-muted"></h6>
        </div>
    `;

    const nota = document.querySelector(".nota-item");

    actualizarEstadoNota(nota, false);

    expect(nota.classList.contains("nota-completada")).toBe(false);
    expect(nota.getAttribute("data-estado")).toBe("pendiente");
});