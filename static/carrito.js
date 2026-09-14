(() => {
    const feedback = document.querySelector('[data-cart-feedback]');
    const buyCart = document.querySelector('[data-buy-cart]');
    if (buyCart) buyCart.addEventListener('click', async () => {
        const cantidades = {};
        for (const input of document.querySelectorAll('[data-cart-quantity]')) {
            if (!input.reportValidity()) return;
            if (Number(input.value) !== Number(input.defaultValue)) {
                feedback.textContent = 'Pulsa «Actualizar» para guardar las cantidades antes de comprar.';
                input.focus();
                return;
            }
            cantidades[input.dataset.cartQuantity] = Number(input.value);
        }
        buyCart.disabled = true;
        try {
            const token = document.cookie.split('; ').find(cookie => cookie.startsWith('csrf_token='));
            const response = await fetch('/api/compra/carrito', {method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token ? decodeURIComponent(token.slice(11)) : ''},
                body: JSON.stringify({cantidades})});
            const data = await response.json();
            if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Revisa las cantidades seleccionadas.');
            window.location.assign(data.url);
        } catch (error) {feedback.textContent = error.message || 'No se pudo iniciar la compra.';}
        finally {buyCart.disabled = false;}
    });
    document.querySelectorAll('[data-add-cart], [data-update-cart], [data-remove-cart]').forEach(button => {
        button.addEventListener('click', async () => {
            const id = button.dataset.addCart || button.dataset.updateCart || button.dataset.removeCart;
            const remove = Boolean(button.dataset.removeCart);
            const input = button.dataset.updateCart
                ? document.querySelector('[data-cart-quantity="' + id + '"]')
                : button.dataset.addCart
                    ? button.closest('.product-card, .product-detail').querySelector('[data-add-quantity]')
                    : null;
            if (input && !input.reportValidity()) return;
            if (button.hasAttribute('data-buy-now')) {
                window.location.assign('/compra/' + id + '?cantidad=' + (input ? input.value : 1));
                return;
            }
            const token = document.cookie.split('; ').find(cookie => cookie.startsWith('csrf_token='));
            button.disabled = true;
            try {
                const response = await fetch('/api/carrito/productos/' + id, {
                    method: remove ? 'DELETE' : button.dataset.updateCart ? 'PUT' : 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token ? decodeURIComponent(token.slice(11)) : ''},
                    ...(remove ? {} : {body: JSON.stringify({cantidad: input ? Number(input.value) : 1})}),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Revisa la cantidad seleccionada.');
                if (!button.dataset.addCart) {window.location.reload(); return;}
                feedback.textContent = 'Producto añadido. Tu carrito contiene ' + data.cantidad + ' unidades.';
            } catch (error) {feedback.textContent = error.message || 'No se pudo actualizar el carrito.';}
            finally {button.disabled = false;}
        });
    });
})();
