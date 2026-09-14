(() => {
    const form = document.getElementById('pedidoForm'), message = document.getElementById('pedidosMensaje');
    const lines = document.getElementById('pedidoLineas');
    let page = 1;
    function addLine(data) {
        const fragment = document.getElementById('lineaTemplate').content.cloneNode(true), row = fragment.querySelector('.order-line');
        const select = row.querySelector('[data-line-product]'), price = row.querySelector('[data-line-price]');
        select.addEventListener('change', () => {price.value = select.selectedOptions[0].dataset.price || '';});
        row.querySelector('[data-remove-line]').addEventListener('click', () => row.remove());
        if (data) {select.value = data.producto_id; price.value = data.precio_unitario; row.querySelector('[data-line-quantity]').value = data.cantidad;}
        lines.append(fragment);
    }
    function reset() {form.reset(); form.elements.id.value = ''; lines.replaceChildren(); document.getElementById('pedidoEditor').hidden = true;}
    function edit(order) {
        document.getElementById('pedidoEditor').hidden = false;
        for (const field of form.elements) if (field.name && field.name in order) field.value = order[field.name] ?? '';
        lines.replaceChildren(); order.lineas.forEach(addLine); document.getElementById('pedidoTitulo').textContent = 'Editar pedido'; form.scrollIntoView({behavior: 'smooth'});
    }
    async function load() {
        const params = new URLSearchParams({pagina: page, q: document.getElementById('qPedido').value.trim()});
        const state = document.getElementById('estadoFiltro').value; if (state) params.set('estado', state);
        const data = await accountRequest('/admin/pedidos/?' + params), table = document.getElementById('pedidosTabla'); table.replaceChildren();
        document.getElementById('pedidosPagina').textContent = data.total + ' pedidos · Página ' + page;
        document.getElementById('pedidosAnterior').disabled = page <= 1; document.getElementById('pedidosSiguiente').disabled = page >= data.paginas;
        if (!data.pedidos.length) {const row = document.createElement('tr'), cell = document.createElement('td'); cell.colSpan = 6; cell.textContent = 'No hay pedidos para mostrar.'; row.append(cell); table.append(row);}
        for (const order of data.pedidos) {
            const row = document.createElement('tr');
            for (const value of [order.codigo_pedido, order.comprador.email, new Date(order.fecha + 'Z').toLocaleDateString('es-ES'), order.estado, order.total.toFixed(2) + ' €']) {const cell = document.createElement('td'); cell.textContent = value; row.append(cell);}
            const actions = document.createElement('td'), editButton = document.createElement('button'), remove = document.createElement('button');
            editButton.type = 'button'; editButton.className = 'add-cart'; editButton.textContent = 'Ver / editar'; editButton.onclick = () => edit(order);
            remove.type = 'button'; remove.className = 'danger-button'; remove.textContent = 'Eliminar';
            remove.onclick = async () => {if (!confirm('¿Eliminar el pedido ' + order.codigo_pedido + ' y sus líneas?')) return; remove.disabled = true; try {await accountRequest('/admin/pedidos/' + order.id, 'DELETE'); reset(); await load(); message.textContent = 'Pedido eliminado';} catch(error) {message.textContent = error.message; remove.disabled = false;}};
            actions.append(editButton, remove); row.append(actions); table.append(row);
        }
    }
    document.getElementById('cancelarPedido').onclick = reset;
    document.getElementById('agregarLinea').onclick = () => addLine();
    document.getElementById('buscarPedidos').onsubmit = async event => {event.preventDefault(); page = 1; try {await load();} catch(error) {message.textContent = error.message;}};
    document.getElementById('limpiarPedidos').onclick = async () => {document.getElementById('buscarPedidos').reset(); page = 1; try {await load();} catch(error) {message.textContent = error.message;}};
    for (const [id, step] of [['pedidosAnterior', -1], ['pedidosSiguiente', 1]]) document.getElementById(id).onclick = async () => {page += step; try {await load();} catch(error) {page -= step; message.textContent = error.message;}};
    form.addEventListener('submit', async event => {
        event.preventDefault(); const button = form.querySelector('[type=submit]'); button.disabled = true;
        try {
            const data = Object.fromEntries(new FormData(form)), id = data.id; delete data.id;
            if (!id) throw new Error('Selecciona un pedido existente para editarlo');
            data.usuario_id = Number(data.usuario_id); data.impuesto = Number(data.impuesto); data.coste_entrega = Number(data.coste_entrega);
            data.lineas = [...lines.querySelectorAll('.order-line')].map(row => ({producto_id: Number(row.querySelector('[data-line-product]').value), cantidad: Number(row.querySelector('[data-line-quantity]').value), precio_unitario: Number(row.querySelector('[data-line-price]').value)}));
            await accountRequest('/admin/pedidos/' + id, 'PUT', data); reset(); await load(); message.textContent = 'Pedido guardado';
        } catch(error) {message.textContent = error.message;} finally {button.disabled = false;}
    });
    reset(); load().catch(error => {message.textContent = error.message;});
})();
