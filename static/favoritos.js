(() => {
    const buttons = [...document.querySelectorAll('[data-favorite-type][data-favorite-id]')];
    if (!buttons.length) return;
    const label = button => button.dataset.favoriteType === 'tiendas' ? 'tienda' : 'producto';
    function set(button, saved) {
        button.setAttribute('aria-pressed', String(saved));
        button.textContent = saved ? `♥ Quitar ${label(button)}` : `♡ Guardar ${label(button)}`;
    }
    fetch('/api/favoritos').then(response => response.ok ? response.json() : null).then(data => {
        if (!data) return;
        for (const button of buttons) {
            const items = data[button.dataset.favoriteType] || [];
            set(button, items.some(item => item.id === Number(button.dataset.favoriteId)));
        }
    }).catch(() => {});
    for (const button of buttons) button.addEventListener('click', async () => {
        const saved = button.getAttribute('aria-pressed') === 'true';
        button.disabled = true;
        try {
            const response = await fetch(`/api/favoritos/${button.dataset.favoriteType}/${button.dataset.favoriteId}`, {
                method: saved ? 'DELETE' : 'PUT',
                headers: {'X-CSRF-Token': document.cookie.split('; ').find(part => part.startsWith('csrf_token='))?.split('=')[1] || ''},
            });
            if (!response.ok) throw new Error((await response.json()).detail || 'No se pudo actualizar el favorito');
            document.querySelectorAll(`[data-favorite-type="${button.dataset.favoriteType}"][data-favorite-id="${button.dataset.favoriteId}"]`)
                .forEach(other => set(other, !saved));
            if (location.pathname === '/favoritos' && saved) button.closest('.product-card, .store-card')?.remove();
        } catch (error) {
            alert(error.message);
        } finally {
            button.disabled = false;
        }
    });
})();
