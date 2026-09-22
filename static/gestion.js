(() => {
    const status = document.querySelector('[data-management-status]');
    async function mutate(url, method, data) {
        const token = document.cookie.split('; ').find(value => value.startsWith('csrf_token='));
        const response = await fetch(url, {method, headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token ? decodeURIComponent(token.slice(11)) : ''}, ...(data ? {body: JSON.stringify(data)} : {})});
        const result = await response.json();
        if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Revisa los campos y los precios del formulario.');
        return result;
    }
    function fail(error) {if (status) status.textContent = error.message; else alert(error.message);}
    async function imageFor(form) {
        const file = form.querySelector('[data-image-file]').files[0];
        if (!file) return form.elements.imagen.value;
        if (file.size > 5 * 1024 * 1024) throw new Error('La imagen no puede superar 5 MB');
        const body = new FormData(); body.append('archivo', file);
        const token = document.cookie.split('; ').find(value => value.startsWith('csrf_token='));
        const response = await fetch('/api/gestion/imagenes', {method: 'POST', body,
            headers: {'X-CSRF-Token': token ? decodeURIComponent(token.slice(11)) : ''}});
        const result = await response.json();
        if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'No se pudo subir la imagen');
        form.elements.imagen.value = result.imagen;
        form.querySelector('[data-image-file]').value = '';
        return result.imagen;
    }
    document.querySelectorAll('[data-image-file]').forEach(input => {
        const preview = input.form.querySelector('[data-image-preview]');
        let objectUrl;
        function clearPreview() {
            if (objectUrl) URL.revokeObjectURL(objectUrl);
            objectUrl = null; preview.hidden = true; preview.removeAttribute('src');
        }
        input.addEventListener('change', () => {
            clearPreview(); const file = input.files[0];
            if (file) {objectUrl = URL.createObjectURL(file); preview.src = objectUrl; preview.hidden = false;}
        });
        input.form.addEventListener('reset', clearPreview);
    });
    const storeForm = document.getElementById('storeForm');
    if (storeForm) {
        storeForm.addEventListener('submit', async event => {
            event.preventDefault();
            const button = storeForm.querySelector('[type=submit]'); button.disabled = true;
            try {
                const form = new FormData(storeForm), data = Object.fromEntries(form);
                data.imagen = await imageFor(storeForm);
                if (storeForm.elements.suscripcion_activa) {
                    data.suscripcion_activa = storeForm.elements.suscripcion_activa.checked;
                    data.pasarela_activa = storeForm.elements.pasarela_activa.checked;
                    data.fecha_renovacion_plan = data.fecha_renovacion_plan || null;
                }
                data.latitud = Number(data.latitud); data.longitud = Number(data.longitud);
                if (data.vendedor_id) data.vendedor_id = Number(data.vendedor_id);
                const id = storeForm.dataset.storeId;
                const result = await mutate('/api/gestion/tiendas' + (id ? '/' + id : ''), id ? 'PUT' : 'POST', data);
                window.location.assign('/gestion/tiendas/' + result.id);
            } catch (error) {fail(error);} finally {button.disabled = false;}
        });
        if (window.L) {
            const lat = storeForm.elements.latitud, lon = storeForm.elements.longitud;
            const map = L.map('storeLocationMap').setView([37.4712, -5.646], 13);
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
            let marker;
            function refresh() {
                if (lat.value === '' || lon.value === '' || !lat.checkValidity() || !lon.checkValidity()) return;
                const point = [Number(lat.value), Number(lon.value)];
                if (marker) marker.setLatLng(point); else marker = L.marker(point).addTo(map);
                map.setView(point, map.getZoom());
            }
            map.on('click', event => {lat.value = event.latlng.lat.toFixed(6); lon.value = event.latlng.lng.toFixed(6); refresh();});
            lat.addEventListener('change', refresh); lon.addEventListener('change', refresh); refresh();
        }
    }
    const productForm = document.getElementById('productForm');
    if (productForm) {
        const title = document.getElementById('productFormTitle');
        const editor = document.getElementById('productEditor');
        document.getElementById('createProduct').addEventListener('click', () => {
            productForm.reset(); productForm.elements.id.value = ''; title.textContent = 'Crear producto';
            editor.querySelector('[data-product-status]').textContent = ''; editor.showModal();
        });
        document.getElementById('closeProductEditor').addEventListener('click', () => editor.close());
        const editStock = document.getElementById('editStock');
        const saveStocks = document.getElementById('saveStocks');
        const cancelStocks = document.getElementById('cancelStocks');
        const stockInputs = [...document.querySelectorAll('[data-stock-product]')];
        function stockEditing(active) {
            document.querySelectorAll('.stock-edit-controls').forEach(control => {control.hidden = !active;});
            editStock.hidden = active; saveStocks.hidden = !active; cancelStocks.hidden = !active;
            editStock.style.display = active ? 'none' : '';
            saveStocks.style.display = active ? '' : 'none';
            cancelStocks.style.display = active ? '' : 'none';
        }
        stockEditing(false);
        editStock.addEventListener('click', () => {status.textContent = ''; stockEditing(true);});
        cancelStocks.addEventListener('click', () => {
            stockInputs.forEach(input => {input.value = input.defaultValue;});
            status.textContent = ''; stockEditing(false);
        });
        saveStocks.addEventListener('click', async () => {
            if (!stockInputs.every(input => input.reportValidity())) return;
            const productos = stockInputs.filter(input => Number(input.value) !== Number(input.defaultValue))
                .map(input => ({producto_id: Number(input.dataset.stockProduct), stock: Number(input.value)}));
            if (!productos.length) {stockEditing(false); return;}
            saveStocks.disabled = true; cancelStocks.disabled = true;
            stockInputs.forEach(input => {input.disabled = true;});
            try {
                await mutate('/api/gestion/tiendas/' + productForm.dataset.storeId + '/stock', 'PATCH', {productos});
                window.location.reload();
            } catch (error) {fail(error);} finally {
                saveStocks.disabled = false; cancelStocks.disabled = false;
                stockInputs.forEach(input => {input.disabled = false;});
            }
        });
        document.querySelectorAll('[data-edit-product]').forEach(button => button.addEventListener('click', () => {
            const product = JSON.parse(button.dataset.editProduct);
            productForm.reset();
            for (const field of productForm.elements) {
                if (!field.name || !(field.name in product)) continue;
                if (field.type === 'checkbox') field.checked = product[field.name]; else field.value = product[field.name] ?? '';
            }
            title.textContent = 'Editar producto'; editor.querySelector('[data-product-status]').textContent = ''; editor.showModal();
        }));
        document.getElementById('cancelProductEdit').addEventListener('click', () => {productForm.reset(); productForm.elements.id.value = ''; title.textContent = 'Crear producto';});
        productForm.addEventListener('submit', async event => {
            event.preventDefault(); const button = productForm.querySelector('[type=submit]'); button.disabled = true;
            try {
                const data = Object.fromEntries(new FormData(productForm)), id = data.id; delete data.id;
                data.imagen = await imageFor(productForm);
                data.precio = Number(data.precio); data.precio_oferta = data.precio_oferta === '' ? null : Number(data.precio_oferta);
                data.stock = Number(data.stock); data.disponible = productForm.elements.disponible.checked; data.destacado = productForm.elements.destacado.checked;
                await mutate(id ? '/api/gestion/productos/' + id : '/api/gestion/tiendas/' + productForm.dataset.storeId + '/productos', id ? 'PUT' : 'POST', data);
                window.location.reload();
            } catch (error) {editor.querySelector('[data-product-status]').textContent = error.message;} finally {button.disabled = false;}
        });
    }
    document.querySelectorAll('[data-delete-store], [data-delete-product]').forEach(button => button.addEventListener('click', async () => {
        const store = button.dataset.deleteStore;
        if (!confirm(store ? '¿Eliminar esta tienda y todos sus productos?' : '¿Eliminar este producto?')) return;
        button.disabled = true;
        try {await mutate('/api/gestion/' + (store ? 'tiendas/' + store : 'productos/' + button.dataset.deleteProduct), 'DELETE'); if (store) window.location.assign('/mi-tienda'); else window.location.reload();}
        catch (error) {fail(error);} finally {button.disabled = false;}
    }));
})();
