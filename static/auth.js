function getCookieValue(name) {
    const prefix = name + '=';
    const parts = document.cookie.split(';');
    for (const rawPart of parts) {
        const part = rawPart.trim();
        if (part.startsWith(prefix)) {
            return decodeURIComponent(part.substring(prefix.length));
        }
    }
    return null;
}

async function cerrarSesion() {
    try {
        const csrfToken = getCookieValue('csrf_token');
        await fetch('/api/logout', {
            method: 'POST',
            headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
        });
    } catch (error) {
        console.error('Error al cerrar sesión:', error);
    }
    window.location.href = '/login';
}

function iniciarLogin() {
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');

    if (!loginForm || !loginError) {
        return;
    }

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        loginError.textContent = '';

        const email = document.getElementById('email').value.trim();
        const contrasena = document.getElementById('contrasena').value;

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, contrasena }),
            });

            if (!response.ok) {
                const data = await response.json();
                loginError.textContent = data.detail || 'No se pudo iniciar sesión';
                return;
            }

            const data = await response.json();
            window.location.href = data.redirect_url || '/inicio';
        } catch (error) {
            console.error('Error de login:', error);
            loginError.textContent = 'Error de conexión. Inténtalo de nuevo.';
        }
    });
}

function iniciarRegistro() {
    const form = document.getElementById('registroForm');
    if (!form) {
        return;
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        document.querySelectorAll('.error-message').forEach((el) => {
            el.style.display = 'none';
        });

        const nombre = document.getElementById('nombre').value.trim();
        const apellidos = document.getElementById('apellidos').value.trim();
        const email = document.getElementById('email').value.trim();
        const telefono = document.getElementById('telefono').value.trim();
        const ciudad = document.getElementById('ciudad').value.trim();
        const direccion = document.getElementById('direccion').value.trim();
        const codigo_postal = document.getElementById('codigo_postal').value.trim();
        const contrasena = document.getElementById('contrasena').value;
        const contrasena_confirmacion = document.getElementById('contrasena_confirmacion').value;
        let rol = document.getElementById('rol').value;
        if (rol) {
            rol = rol.toLowerCase();
        }

        let tieneErrores = false;

        if (!nombre) {
            document.getElementById('errorNombre').textContent = 'Requerido';
            document.getElementById('errorNombre').style.display = 'block';
            tieneErrores = true;
        }

        if (!apellidos) {
            document.getElementById('errorApellidos').textContent = 'Requerido';
            document.getElementById('errorApellidos').style.display = 'block';
            tieneErrores = true;
        }

        if (!email) {
            document.getElementById('errorEmail').textContent = 'Requerido';
            document.getElementById('errorEmail').style.display = 'block';
            tieneErrores = true;
        }

        if (!rol) {
            document.getElementById('errorRol').textContent = 'Selecciona un rol';
            document.getElementById('errorRol').style.display = 'block';
            tieneErrores = true;
        }

        if (!contrasena) {
            document.getElementById('errorContrasena').textContent = 'Requerido';
            document.getElementById('errorContrasena').style.display = 'block';
            tieneErrores = true;
        }

        if (contrasena !== contrasena_confirmacion) {
            document.getElementById('errorConfirmacion').textContent = 'No coinciden';
            document.getElementById('errorConfirmacion').style.display = 'block';
            tieneErrores = true;
        }

        if (contrasena && contrasena.length < 8) {
            document.getElementById('errorContrasena').textContent = 'Mínimo 8 caracteres';
            document.getElementById('errorContrasena').style.display = 'block';
            tieneErrores = true;
        }

        for (const [campo, valor] of Object.entries({telefono, direccion, ciudad, codigo_postal})) {
            if (!valor) {
                const error = document.getElementById('error_' + campo);
                error.textContent = 'Requerido'; error.style.display = 'block'; tieneErrores = true;
            }
        }

        if (tieneErrores) {
            return;
        }

        try {
            const response = await fetch('/api/registro', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    nombre,
                    apellidos,
                    email,
                    telefono: telefono || null,
                    rol,
                    ciudad: ciudad || null,
                    direccion: direccion || null,
                    codigo_postal: codigo_postal || null,
                    contrasena,
                }),
            });

            if (response.ok) {
                document.getElementById('successMessage').style.display = 'block';
                form.reset();
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return;
            }

            if (response.status === 422) {
                const data = await response.json();
                const errors = {nombre: 'errorNombre', apellidos: 'errorApellidos', email: 'errorEmail', rol: 'errorRol', contrasena: 'errorContrasena', telefono: 'error_telefono', direccion: 'error_direccion', ciudad: 'error_ciudad', codigo_postal: 'error_codigo_postal'};
                for (const issue of data.detail || []) {
                    const field = issue.loc[issue.loc.length - 1];
                    const element = document.getElementById(errors[field]);
                    if (element) { element.textContent = 'Introduce un valor válido para este campo'; element.style.display = 'block'; }
                }
                return;
            }

            if (response.status === 400) {
                const data = await response.json();
                if (data.detail) {
                    const detail = String(data.detail).toLowerCase();
                    if (detail.includes('email')) {
                        document.getElementById('errorEmail').textContent = 'Email ya registrado';
                        document.getElementById('errorEmail').style.display = 'block';
                    } else if (detail.includes('contraseña')) {
                        document.getElementById('errorContrasena').textContent = data.detail;
                        document.getElementById('errorContrasena').style.display = 'block';
                    } else {
                        alert('Error: ' + (data.detail || 'No se pudo registrar'));
                    }
                } else {
                    alert('Error: No se pudo registrar');
                }
            } else {
                alert('Error al registrar. Intenta nuevamente.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error de conexión. Intenta nuevamente.');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    iniciarLogin();
    iniciarRegistro();
});
