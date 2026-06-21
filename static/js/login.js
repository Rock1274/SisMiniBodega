// MOSTRAR / OCULTAR CONTRASEÑA
function togglePasswordVisibility(passwordInput, toggleIcon) {

    const type =
        passwordInput.getAttribute('type') === 'password'
            ? 'text'
            : 'password';

    passwordInput.setAttribute('type', type);

    toggleIcon.classList.toggle('fa-eye');
    toggleIcon.classList.toggle('fa-eye-slash');

    return type;
}


// VERIFICAR CHECKBOX
function verificarRecuerdame(checkbox) {

    if (!checkbox) return false;

    return checkbox.checked;
}


// INICIALIZADOR
function initLogin() {

    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('contrasena');

    if (togglePassword && passwordInput) {

        togglePassword.addEventListener('click', () => {
            togglePasswordVisibility(passwordInput, togglePassword);
        });
    }

    const form = document.querySelector('form');

    if (form) {

        form.addEventListener('submit', function () {

            const checkbox = document.getElementById('Recuerdame');

            const recuerdameChecked =
                verificarRecuerdame(checkbox);

            console.log(
                '🔐 Enviando formulario con "Recuérdame":',
                recuerdameChecked
            );
        });
    }
}


// EXPORTAR PARA TEST
if (typeof module !== "undefined") {

    module.exports = {
        togglePasswordVisibility,
        verificarRecuerdame
    };
}