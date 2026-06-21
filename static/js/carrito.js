document.addEventListener("DOMContentLoaded", () => {

    const carrito = document.getElementById("carrito_container");

    // ⚠️ Validación por si no existe el contenedor
    if (!carrito) return;

    const idCompra = carrito.dataset.id;

    // 🔥 Detectar salida de la página (cerrar, recargar, etc.)
    window.addEventListener("beforeunload", function () {
        navigator.sendBeacon(`/carrito/${idCompra}/cancelar_exit`);
    });

    // 🔥 Detectar navegación (links)
    document.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", function () {
            const href = this.getAttribute("href");

            if (
                href &&
                !href.includes("finalizar") &&
                !href.includes("cancelar") &&
                !href.includes("#")
            ) {
                fetch(`/carrito/${idCompra}/cancelar_exit`, {
                    method: "POST"
                });
            }
        });
    });

});


// 🔄 Actualizar solo la tabla del carrito
function actualizarCarrito(idCompra) {

    fetch(`/carrito/${idCompra}?partial=1`, {
        headers: { 'X-Custom-Ajax-Navigation': 'true' }
    })
    .then(res => res.text())
    .then(html => {

        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        const nuevo = doc.querySelector("#carrito_tabla");
        const actual = document.querySelector("#carrito_tabla");

        if (nuevo && actual) {
            actual.innerHTML = nuevo.innerHTML;
        }
    })
    .catch(err => console.error("Error al actualizar carrito:", err));
}


// ➕ Agregar producto
function agregarProducto(idPaquete) {

    const contenedor = document.getElementById("carrito_container");
    const idCompra = contenedor.dataset.id;

    const input = document.getElementById(`cant_${idPaquete}`);
    const cantidad = input ? input.value : 1;

    fetch(`/carrito/${idCompra}/agregar`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            'X-Custom-Ajax-Navigation': 'true'
        },
        body: `id_paquete=${idPaquete}&cantidad=${cantidad}`
    })
    .then(res => {
        if (!res.ok) throw new Error("Error al agregar producto");
        actualizarCarrito(idCompra);
    })
    .catch(err => console.error(err));
}


// ❌ Eliminar producto
function eliminarProducto(idDetalle) {

    const contenedor = document.getElementById("carrito_container");
    const idCompra = contenedor.dataset.id;

    fetch(`/carrito/${idCompra}/eliminar/${idDetalle}`, {
        method: "DELETE",
        headers: { 'X-Custom-Ajax-Navigation': 'true' }
    })
    .then(res => {
        if (!res.ok) throw new Error("Error al eliminar producto");
        actualizarCarrito(idCompra);
    })
    .catch(err => console.error(err));
}