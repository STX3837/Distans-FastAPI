const accountFields = ['nombre', 'apellidos', 'email', 'telefono', 'direccion', 'ciudad', 'codigo_postal'];
async function accountRequest(url, method = 'GET', body) {
    const headers = {'Content-Type': 'application/json'};
    const token = getCookieValue('csrf_token');
    if (token) headers['X-CSRF-Token'] = token;
    const response = await fetch(url, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
    const data = await readApiResponse(response);
    if (!response.ok) {
        throw new Error(apiErrorMessage(data && data.detail));
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
    const editor = document.getElementById('accountEditor');
    let page = 0; let subscriptionEditable = false; const size = 20; const message = document.getElementById('adminMensaje');
    const subscriptionFields = document.getElementById('subscriptionFields');
    const localDate = value => value ? value.slice(0, 16) : '';
    function clearEditor() {
        adminForm.reset(); document.getElementById('usuario_id').value = ''; document.getElementById('formTitle').textContent = 'Crear usuario';
        document.getElementById('passwordField').hidden = false; adminForm.elements.contrasena.required = true;
        subscriptionFields.hidden = true; subscriptionEditable = false;
        document.getElementById('accountEditorMensaje').textContent = '';
    }
    async function loadUsers() {
        const params = new URLSearchParams({skip: page * size, limit: size, q: document.getElementById('busquedaCuentas').value.trim()});
        const role = document.getElementById('filtroRol').value; if (role) params.set('rol', role);
        const users = await accountRequest('/admin/usuarios/?' + params);
        const table = document.getElementById('usuariosTabla'); table.replaceChildren();
        document.getElementById('pagina').textContent = 'Página ' + (page + 1);
        document.getElementById('anterior').disabled = page === 0; document.getElementById('siguiente').disabled = users.length < size;
        for (const user of users) {
            const row = document.createElement('tr');
            for (const value of [user.nombre + ' ' + user.apellidos, user.email, user.rol, user.activo ? 'Activa' : 'Inactiva']) {
                const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
            }
            const actions = document.createElement('td'); const edit = document.createElement('button'); edit.type = 'button';
            edit.textContent = 'Editar';
            edit.onclick = async () => {
                clearEditor();
                for (const key of accountFields) adminForm.elements[key].value = user[key] || '';
                adminForm.elements.rol.value = user.rol; document.getElementById('activo').checked = user.activo; document.getElementById('usuario_id').value = user.id;
                document.getElementById('formTitle').textContent = 'Editar usuario'; document.getElementById('passwordField').hidden = true;
                adminForm.elements.contrasena.required = false; adminForm.elements.contrasena.value = ''; editor.showModal();
                if (user.rol === 'vendedor') {
                    subscriptionFields.hidden = false;
                    document.getElementById('subscriptionStore').textContent = 'Cargando suscripción…';
                    try {
                        const subscription = await accountRequest('/admin/usuarios/' + user.id + '/suscripcion');
                        const store = subscription.tienda;
                        subscriptionEditable = Boolean(store);
                        document.getElementById('subscriptionStore').textContent = store ? 'Tienda: ' + store.nombre + ' · Plan efectivo: ' + store.plan_efectivo : 'Este vendedor todavía no tiene una tienda.';
                        for (const control of subscriptionFields.querySelectorAll('input, select')) control.disabled = !store;
                        if (store) {
                            document.getElementById('subscriptionPlan').value = store.plan;
                            document.getElementById('subscriptionActive').checked = store.suscripcion_activa;
                            document.getElementById('subscriptionGateway').checked = store.pasarela_activa;
                            document.getElementById('subscriptionStart').value = localDate(store.fecha_alta_plan);
                            document.getElementById('subscriptionRenewal').value = localDate(store.fecha_renovacion_plan);
                        }
                    } catch (error) { document.getElementById('subscriptionStore').textContent = error.message; }
                }
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
    document.getElementById('cancelar').onclick = () => editor.close();
    editor.addEventListener('close', clearEditor);
    document.getElementById('crearCuenta').onclick = () => {clearEditor(); editor.showModal();};
    document.getElementById('buscarCuentas').onsubmit = async event => {event.preventDefault(); page = 0; try {await loadUsers();} catch(error) {message.textContent = error.message;}};
    document.getElementById('limpiarCuentas').onclick = async () => {document.getElementById('buscarCuentas').reset(); page = 0; try {await loadUsers();} catch(error) {message.textContent = error.message;}};
    for (const [id, step] of [['anterior', -1], ['siguiente', 1]]) document.getElementById(id).onclick = async () => {
        page += step; try { await loadUsers(); } catch(error) { page -= step; message.textContent = error.message; }
    };
    bindAccountForm('adminForm', 'accountEditorMensaje', async (form) => {
        const id = document.getElementById('usuario_id').value; const body = {...identityData(form), rol: form.elements.rol.value};
        body.activo = document.getElementById('activo').checked;
        if (!id) body.contrasena = form.elements.contrasena.value;
        await accountRequest('/admin/usuarios/' + id, id ? 'PUT' : 'POST', body);
        if (id && body.rol === 'vendedor' && subscriptionEditable) {
            await accountRequest('/admin/usuarios/' + id + '/suscripcion', 'PUT', {
                plan: document.getElementById('subscriptionPlan').value,
                suscripcion_activa: document.getElementById('subscriptionActive').checked,
                pasarela_activa: document.getElementById('subscriptionGateway').checked,
                fecha_alta_plan: document.getElementById('subscriptionStart').value || null,
                fecha_renovacion_plan: document.getElementById('subscriptionRenewal').value || null,
            });
        }
        editor.close();
        try { await loadUsers(); message.textContent = 'Usuario guardado'; }
        catch (error) { message.textContent = 'Usuario guardado. ' + error.message; }
    });
    loadUsers().catch(error => {message.textContent = error.message;});
}
