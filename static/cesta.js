(() => {
    function update(cart) {
        document.querySelectorAll('[data-cart-count]').forEach(counter => { counter.textContent = cart.cantidad; });
    }
    window.addEventListener('cart-updated', event => update(event.detail));
    fetch('/api/carrito').then(response => response.ok ? response.json() : null)
        .then(cart => { if (cart) update(cart); }).catch(() => {});
})();
