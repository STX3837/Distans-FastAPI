(() => {
    const status = document.getElementById('mapStatus');
    let map;
    function showTab(name) {
        document.querySelectorAll('.market-panel').forEach(panel => {panel.hidden = panel.id !== 'panel-' + name;});
        document.querySelectorAll('[data-tab]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.tab === name)));
        if (name === 'mapa' && map) requestAnimationFrame(() => map.invalidateSize());
    }
    document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
    const defaultTab = document.querySelector('.market-page').dataset.defaultTab;

    if (!window.L) { showTab(defaultTab); status.textContent = 'No se ha podido cargar el mapa. Puedes consultar las tiendas en las tarjetas.'; return; }
    const products = JSON.parse(document.getElementById('mapProducts').textContent);
    map = L.map('productsMap', {scrollWheelZoom: true, zoomControl: false}).setView([40.4168, -3.7038], 6);
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    tiles.on('tileerror', () => {status.textContent = 'No se ha podido cargar el fondo del mapa. Comprueba tu conexión; los marcadores siguen disponibles.';});
    const shops = new Map();
    for (const shop of JSON.parse(document.getElementById('mapStores').textContent)) {
        if (Number.isFinite(shop.latitud) && Number.isFinite(shop.longitud)) shops.set(shop.id, {shop, products: []});
    }
    for (const product of products) {
        const shop = product.tienda;
        if (!Number.isFinite(shop.latitud) || !Number.isFinite(shop.longitud)) continue;
        if (!shops.has(shop.id)) shops.set(shop.id, {shop, products: []});
        shops.get(shop.id).products.push(product);
    }
    const greenIcon = L.divIcon({className: 'green-marker', iconSize: [30, 44], iconAnchor: [15, 44], popupAnchor: [0, -40],
        html: '<svg viewBox="0 0 30 44" xmlns="http://www.w3.org/2000/svg"><path fill="#008b08" d="M15 0C6.7 0 1 6.2 1 14c0 9 14 30 14 30s14-21 14-30C29 6.2 23.3 0 15 0Z"/><circle cx="15" cy="13" r="6" fill="white"/></svg>'});
    const markers = new Map();
    for (const [id, group] of shops) {
        const popup = document.createElement('div'); popup.className = 'shop-popup';
        const heading = document.createElement('h3'); heading.textContent = group.shop.nombre; popup.append(heading);
        const address = document.createElement('p'); address.textContent = group.shop.direccion || group.shop.ubicacion || ''; popup.append(address);
        const list = document.createElement('ul');
        for (const product of group.products) {
            const item = document.createElement('li'); const link = document.createElement('a'); link.href = '/productos/' + product.id;
            link.addEventListener('click', () => showTab('productos'));
            const price = product.precio_oferta !== null ? product.precio_oferta : product.precio;
            link.textContent = product.nombre + ' · ' + new Intl.NumberFormat('es-ES', {style: 'currency', currency: 'EUR'}).format(price);
            item.append(link); list.append(item);
        }
        popup.append(list);
        markers.set(id, L.marker([group.shop.latitud, group.shop.longitud], {title: group.shop.nombre, icon: greenIcon}).addTo(map).bindPopup(popup));
    }
    if (markers.size) {
        map.fitBounds(L.featureGroup([...markers.values()]).getBounds(), {padding: [35, 35], maxZoom: 15});
        status.textContent = markers.size + (markers.size === 1 ? ' tienda en el mapa.' : ' tiendas en el mapa.');
    } else status.textContent = products.length ? 'Estos productos todavía no tienen una tienda ubicada en el mapa.' : 'Los marcadores aparecerán cuando haya resultados con ubicación.';
    document.querySelectorAll('[data-shop-id]').forEach(button => button.addEventListener('click', () => {
        const marker = markers.get(Number(button.dataset.shopId));
        if (!marker) return;
        showTab('mapa');
        document.getElementById('productsMap').scrollIntoView({behavior: 'smooth', block: 'center'});
        map.invalidateSize(); map.setView(marker.getLatLng(), 16, {animate: false}); marker.openPopup();
    }));
    const radiusSelect = document.getElementById('searchRadius');
    let centre = map.getCenter();
    const params = new URLSearchParams(window.location.search);
    if (params.has('latitud') && params.has('longitud')) centre = L.latLng(Number(params.get('latitud')), Number(params.get('longitud')));
    radiusSelect.value = params.get('radio') || '0';
    function submitRadius() {
        const url = new URL(window.location.href);
        url.searchParams.set('latitud', centre.lat);
        url.searchParams.set('longitud', centre.lng);
        url.searchParams.set('radio', radiusSelect.value);
        url.searchParams.set('pagina', '1');
        window.location.assign(url);
    }
    document.querySelector('[data-geo="latitud"]').value = centre.lat;
    document.querySelector('[data-geo="longitud"]').value = centre.lng;
    document.querySelectorAll('[data-geo]').forEach(input => {input.disabled = false;});
    document.querySelector('[data-geo="radio"]').value = radiusSelect.value;
    const centreMarker = L.circleMarker(centre, {radius: 8, color: '#168cff', fillColor: '#168cff', fillOpacity: 1, weight: 0}).addTo(map).bindTooltip('Centro de búsqueda');
    let radiusCircle;
    function filterRadius() {
        const radius = Number(radiusSelect.value);
        if (radiusCircle) map.removeLayer(radiusCircle);
        if (radius) radiusCircle = L.circle(centre, {radius, color: '#168cff', weight: 1, fillOpacity: .04}).addTo(map);
        status.textContent = markers.size + (markers.size === 1 ? ' tienda en el mapa.' : ' tiendas en el mapa.') + (radius ? ' Radio: ' + radius / 1000 + ' km.' : '');
    }
    function selectCentre(point) {
        centre = L.latLng(point); centreMarker.setLatLng(centre);
        map.setView(centre, 14, {animate: false});
        document.getElementById('selectLocation').textContent = 'Cambiar ubicación';
        submitRadius();
    }
    radiusSelect.addEventListener('change', submitRadius);
    const dialog = document.getElementById('locationDialog');
    document.getElementById('selectLocation').addEventListener('click', () => dialog.showModal());
    document.getElementById('closeLocation').addEventListener('click', () => dialog.close());
    document.getElementById('pickOnMap').addEventListener('click', () => {
        dialog.close(); showTab('mapa'); status.textContent = 'Pulsa en el mapa para seleccionar tu ubicación.';
        map.once('click', event => selectCentre(event.latlng));
    });
    document.getElementById('useGeolocation').addEventListener('click', () => {
        const error = document.getElementById('locationError');
        if (!navigator.geolocation) {error.textContent = 'Tu navegador no permite obtener la ubicación.'; return;}
        error.textContent = 'Obteniendo ubicación…';
        navigator.geolocation.getCurrentPosition(position => {
            dialog.close(); error.textContent = ''; showTab('mapa');
            selectCentre([position.coords.latitude, position.coords.longitude]);
        }, () => {error.textContent = 'No se pudo obtener la ubicación. Puedes seleccionarla en el mapa.';}, {timeout: 10000});
    });
    filterRadius();
    showTab(defaultTab);
    window.addEventListener('resize', () => map.invalidateSize());
})();
