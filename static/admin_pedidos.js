(() => {
    const form = document.getElementById('pedidoForm');
    const dialog = document.getElementById('pedidoEditor');
    const message = document.getElementById('pedidosMensaje');
    const editorMessage = document.getElementById('pedidoEditorMensaje');
    const lines = document.getElementById('pedidoLineas');
    let page = 1;

    function addLine(data) {
        const fragment = document.getElementById('lineaTemplate').content.cloneNode(true);
        const row = fragment.querySelector('.order-line');
        const select = row.querySelector('[data-line-product]');
        const price = row.querySelector('[data-line-price]');
        select.addEventListener('change', () => {price.value = select.selectedOptions[0].dataset.price || '';});
        row.querySelector('[data-remove-line]').addEventListener('click', () => row.remove());
        if (data) {
            select.value = data.producto_id;
            price.value = data.precio_unitario;
            row.querySelector('[data-line-quantity]').value = data.cantidad;
            if (data.cancelado) {
                const badge = document.createElement('span');
                badge.className = 'admin-order-cancelled';
                badge.textContent = 'Cancelado';
                row.append(badge);
            }
        }
        lines.append(fragment);
    }

    function closeEditor() {
        if (dialog.open) dialog.close();
        form.reset();
        form.elements.id.value = '';
        lines.replaceChildren();
        editorMessage.hidden = true;
    }

    function edit(order) {
        closeEditor();
        document.getElementById('pedidoTitulo').textContent = 'Pedido ' + order.codigo_pedido;
        document.getElementById('pedidoFecha').textContent = 'Realizado el ' + new Date(order.fecha + 'Z').toLocaleString('es-ES');
        document.getElementById('pedidoComprador').textContent = order.comprador.nombre || 'Comprador invitado';
        document.getElementById('pedidoEmail').textContent = order.comprador.email || '';
        document.getElementById('pedidoEstado').textContent = order.estado;
        document.getElementById('pedidoTotal').textContent = Number(order.total).toFixed(2) + ' €';
        const refund = document.getElementById('reembolsoAviso');
        refund.hidden = !(order.reembolso_pendiente > 0);
        refund.textContent = refund.hidden ? '' : 'Reembolso pendiente: ' + Number(order.reembolso_pendiente).toFixed(2) + ' €';
        const note = document.getElementById('pedidoSoloLectura');
        note.hidden = order.puede_editar;
        note.textContent = order.puede_editar_datos
            ? 'Puedes editar los datos de contacto, entrega y facturación. Los productos e importes quedan protegidos por el pago o el reparto.'
            : 'Este pedido ya no admite cambios de datos. Puedes consultar todos sus detalles.';
        for (const field of form.elements) {
            if (field.name && field.name in order) field.value = order[field.name] ?? '';
        }
        lines.replaceChildren();
        order.lineas.forEach(addLine);
        for (const control of form.querySelectorAll('input:not([type=hidden]), select, [data-remove-line]')) {
            if (control.name !== 'estado') {
                control.disabled = !(order.puede_editar ||
                    (order.puede_editar_datos && ['nombre_comprador', 'apellidos_comprador', 'email_comprador', 'direccion_envio', 'direccion_facturacion', 'telefono'].includes(control.name)));
            }
        }
        document.getElementById('agregarLinea').hidden = !order.puede_editar;
        document.getElementById('guardarPedido').hidden = !(order.puede_editar || order.puede_editar_datos);
        document.getElementById('marcarEntregadoPedido').hidden = order.estado !== 'enviado';
        form.dataset.fullEdit = order.puede_editar ? 'true' : 'false';
        dialog.showModal();
    }

    async function load() {
        const params = new URLSearchParams({pagina: page, q: document.getElementById('qPedido').value.trim()});
        const state = document.getElementById('estadoFiltro').value;
        if (state) params.set('estado', state);
        const data = await accountRequest('/admin/pedidos/?' + params);
        const table = document.getElementById('pedidosTabla');
        table.replaceChildren();
        document.getElementById('pedidosPagina').textContent = data.total + ' pedidos · Página ' + page;
        document.getElementById('pedidosAnterior').disabled = page <= 1;
        document.getElementById('pedidosSiguiente').disabled = page >= data.paginas;
        if (!data.pedidos.length) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 6;
            cell.textContent = 'No hay pedidos para mostrar.';
            row.append(cell);
            table.append(row);
        }
        for (const order of data.pedidos) {
            const row = document.createElement('tr');
            for (const value of [order.codigo_pedido, order.comprador.email,
                new Date(order.fecha + 'Z').toLocaleDateString('es-ES'), order.estado,
                Number(order.total).toFixed(2) + ' €']) {
                const cell = document.createElement('td');
                cell.textContent = value;
                row.append(cell);
            }
            const actions = document.createElement('td');
            const editButton = document.createElement('button');
            editButton.type = 'button';
            editButton.className = 'add-cart';
            editButton.textContent = 'Ver / editar';
            editButton.onclick = () => edit(order);
            actions.append(editButton);
            if (order.estado === 'enviado') {
                const deliver = document.createElement('button');
                deliver.type = 'button';
                deliver.className = 'add-cart';
                deliver.textContent = 'Marcar entregado';
                deliver.onclick = async () => {
                    deliver.disabled = true;
                    try {
                        await accountRequest('/admin/pedidos/' + order.id + '/entregar', 'POST');
                        await load();
                        message.textContent = 'Pedido entregado';
                    } catch (error) {message.textContent = error.message; deliver.disabled = false;}
                };
                actions.append(deliver);
            }
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'danger-button';
            remove.textContent = 'Eliminar';
            remove.onclick = async () => {
                if (!confirm('¿Eliminar el pedido ' + order.codigo_pedido + ' y sus líneas?')) return;
                remove.disabled = true;
                try {
                    await accountRequest('/admin/pedidos/' + order.id, 'DELETE');
                    closeEditor();
                    await load();
                    message.textContent = 'Pedido eliminado';
                } catch (error) {message.textContent = error.message; remove.disabled = false;}
            };
            actions.append(remove);
            row.append(actions);
            table.append(row);
        }
    }

    document.getElementById('cancelarPedido').onclick = closeEditor;
    document.getElementById('cerrarPedido').onclick = closeEditor;
    document.getElementById('marcarEntregadoPedido').onclick = async () => {
        const button = document.getElementById('marcarEntregadoPedido');
        button.disabled = true;
        editorMessage.hidden = true;
        try {
            await accountRequest('/admin/pedidos/' + form.elements.id.value + '/entregar', 'POST');
            closeEditor();
            await load();
            message.textContent = 'Pedido entregado';
        } catch (error) {editorMessage.textContent = error.message; editorMessage.hidden = false;}
        finally {button.disabled = false;}
    };
    dialog.addEventListener('cancel', event => {event.preventDefault(); closeEditor();});
    dialog.addEventListener('click', event => {if (event.target === dialog) closeEditor();});
    document.getElementById('agregarLinea').onclick = () => addLine();
    document.getElementById('buscarPedidos').onsubmit = async event => {
        event.preventDefault(); page = 1;
        try {await load();} catch (error) {message.textContent = error.message;}
    };
    document.getElementById('limpiarPedidos').onclick = async () => {
        document.getElementById('buscarPedidos').reset(); page = 1;
        try {await load();} catch (error) {message.textContent = error.message;}
    };
    for (const [id, step] of [['pedidosAnterior', -1], ['pedidosSiguiente', 1]]) {
        document.getElementById(id).onclick = async () => {
            page += step;
            try {await load();} catch (error) {page -= step; message.textContent = error.message;}
        };
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = document.getElementById('guardarPedido');
        button.disabled = true;
        editorMessage.hidden = true;
        try {
            const data = Object.fromEntries(new FormData(form));
            const id = data.id;
            delete data.id;
            if (!id) throw new Error('Selecciona un pedido existente para editarlo');
            if (form.dataset.fullEdit === 'true') {
                data.usuario_id = Number(data.usuario_id);
                data.impuesto = Number(data.impuesto);
                data.coste_entrega = Number(data.coste_entrega);
                data.lineas = [...lines.querySelectorAll('.order-line')].map(row => ({
                    producto_id: Number(row.querySelector('[data-line-product]').value),
                    cantidad: Number(row.querySelector('[data-line-quantity]').value),
                    precio_unitario: Number(row.querySelector('[data-line-price]').value),
                }));
                await accountRequest('/admin/pedidos/' + id, 'PUT', data);
            } else {
                await accountRequest('/admin/pedidos/' + id + '/datos', 'PATCH', {
                    nombre_comprador: data.nombre_comprador,
                    apellidos_comprador: data.apellidos_comprador,
                    email_comprador: data.email_comprador,
                    direccion_envio: data.direccion_envio,
                    direccion_facturacion: data.direccion_facturacion,
                    telefono: data.telefono || '',
                });
            }
            closeEditor();
            await load();
            message.textContent = 'Pedido guardado';
        } catch (error) {
            editorMessage.textContent = error.message;
            editorMessage.hidden = false;
        } finally {button.disabled = false;}
    });
    load().catch(error => {message.textContent = error.message;});
})();
