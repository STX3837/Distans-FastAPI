const accountFields = ['nombre', 'apellidos', 'email', 'telefono', 'direccion', 'ciudad', 'codigo_postal'];
async function accountRequest(url, method = 'GET', body) {
    const headers = {'Content-Type': 'application/json'};
    const token = getCookieValue('csrf_token');
    if (token) headers['X-CSRF-Token'] = token;
    const response = await fetch(url, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) {
        const detail = data.detail;
        throw new Error(Array.isArray(detail) ? detail.map(e => e.loc.slice(1).join('.') + ': ' + e.msg).join('; ') : detail || 'No se pudo completar la operación');
    }
    return data;
}
function identityData(form) { return Object.fromEntries(accountFields.map(key => [key, form.elements[key].value.trim() || null])); }
function bindAccountForm(id, messageId, action) {
    const form = document.getElementById(id);
    if (!form) return;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type="submit"]'); const message = document.getElementById(messageId);
        button.disabled = true; message.textContent = '';
        try { await action(form, message); } catch (error) { message.textContent = error.message; } finally { button.disabled = false; }
    });
}
function newPassword(form) {
    const password = form.elements.contrasena_nueva.value;
    if (password !== document.getElementById('confirmacion').value) throw new Error('Las contraseñas no coinciden');
    return password;
}
bindAccountForm('cuentaForm', 'cuentaMensaje', async (form, message) => {
    const user = await accountRequest('/usuarios/me', 'PUT', identityData(form));
    document.getElementById('fechaActualizacion').textContent = user.fecha_actualizacion + ' UTC'; message.textContent = 'Datos guardados';
});
bindAccountForm('passwordForm', 'passwordMensaje', async (form, message) => {
    const data = await accountRequest('/usuarios/me/cambiar-contrasena', 'POST', {contrasena_actual: form.elements.contrasena_actual.value, contrasena_nueva: newPassword(form)});
    form.reset(); message.textContent = data.mensaje; window.location.assign('/login');
});
bindAccountForm('recoveryForm', 'recoveryMensaje', async (form, message) => {
    const data = await accountRequest('/api/recuperar-contrasena', 'POST', {email: form.elements.email.value.trim()}); message.textContent = data.mensaje;
});
const resetToken = window.location.hash.slice(1);
if (document.getElementById('resetForm')) history.replaceState(null, '', window.location.pathname);
bindAccountForm('resetForm', 'recoveryMensaje', async (form, message) => {
    if (!resetToken) throw new Error('Falta el enlace de recuperación. Solicita uno nuevo.');
    const data = await accountRequest('/api/restablecer-contrasena', 'POST', {token: resetToken, contrasena_nueva: newPassword(form)});
    form.reset(); message.textContent = data.mensaje; form.querySelector('[type="submit"]').hidden = true;
});
const adminForm = document.getElementById('adminForm');
if (adminForm) {
    let page = 0; const size = 20; const message = document.getElementById('adminMensaje');
    function clearEditor() {
        adminForm.reset(); document.getElementById('usuario_id').value = ''; document.getElementById('formTitle').textContent = 'Crear usuario';
        document.getElementById('passwordField').hidden = false; adminForm.elements.contrasena.required = true;
    }
    async function loadUsers() {
        const users = await accountRequest('/admin/usuarios/?skip=' + page * size + '&limit=' + size);
        const table = document.getElementById('usuariosTabla'); table.replaceChildren();
        document.getElementById('pagina').textContent = 'Página ' + (page + 1);
        document.getElementById('anterior').disabled = page === 0; document.getElementById('siguiente').disabled = users.length < size;
        for (const user of users) {
            const row = document.createElement('tr');
            for (const value of [user.nombre + ' ' + user.apellidos, user.email, user.rol, user.activo ? 'Activa' : 'Inactiva']) {
                const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
            }
            const actions = document.createElement('td'); const edit = document.createElement('button'); edit.type = 'button'; edit.textContent = 'Editar';
            edit.onclick = () => {
                for (const key of accountFields) adminForm.elements[key].value = user[key] || '';
                adminForm.elements.rol.value = user.rol; document.getElementById('activo').checked = user.activo; document.getElementById('usuario_id').value = user.id;
                document.getElementById('formTitle').textContent = 'Editar usuario'; document.getElementById('passwordField').hidden = true;
                adminForm.elements.contrasena.required = false; adminForm.elements.contrasena.value = ''; adminForm.scrollIntoView({behavior: 'smooth'});
            };
            const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Eliminar';
            remove.onclick = async () => {
                if (!confirm('¿Eliminar la cuenta de ' + user.email + '? Se eliminarán su carrito y sus pedidos asociados.')) return;
                remove.disabled = true;
                try { await accountRequest('/admin/usuarios/' + user.id, 'DELETE'); clearEditor(); await loadUsers(); message.textContent = 'Usuario eliminado'; }
                catch (error) { message.textContent = error.message; remove.disabled = false; }
            };
            actions.append(edit, remove); row.append(actions); table.append(row);
        }
    }
    document.getElementById('cancelar').onclick = clearEditor;
    for (const [id, step] of [['anterior', -1], ['siguiente', 1]]) document.getElementById(id).onclick = async () => {
        page += step; try { await loadUsers(); } catch(error) { page -= step; message.textContent = error.message; }
    };
    bindAccountForm('adminForm', 'adminMensaje', async (form, message) => {
        const id = document.getElementById('usuario_id').value; const body = {...identityData(form), rol: form.elements.rol.value};
        body.activo = document.getElementById('activo').checked;
        if (!id) body.contrasena = form.elements.contrasena.value;
        await accountRequest('/admin/usuarios/' + id, id ? 'PUT' : 'POST', body);
        clearEditor(); await loadUsers(); message.textContent = 'Usuario guardado';
    });
    loadUsers().catch(error => {message.textContent = error.message;});
}
