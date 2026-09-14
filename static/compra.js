(() => {
    const form = document.getElementById('checkoutForm');
    const steps = [...form.querySelectorAll('[data-step]')];
    const feedback = document.getElementById('checkoutFeedback');
    const pay = document.getElementById('payButton');
    let current = 0;
    function valid(step) {
        for (const input of steps[step].querySelectorAll('input')) {
            if (!input.checkValidity()) {input.reportValidity(); return false;}
        }
        return true;
    }
    function show(step) {
        current = step;
        steps.forEach((panel, index) => {panel.hidden = index !== step;});
        document.querySelectorAll('.checkout-steps li').forEach((item, index) => {
            if (index === step) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
        });
        steps[step].querySelector('input, button').focus();
        if (step === 2) {
            const review = document.getElementById('buyerReview');
            review.replaceChildren();
            const data = new FormData(form);
            for (const [title, fields] of [['Comprador', ['nombre', 'apellidos', 'email', 'telefono']],
                ['Envío', ['envio_direccion', 'envio_ciudad', 'envio_codigo_postal']],
                ['Facturación', ['facturacion_direccion', 'facturacion_ciudad', 'facturacion_codigo_postal']]]) {
                const heading = document.createElement('h2'); heading.textContent = title;
                const text = document.createElement('p'); text.textContent = fields.map(field => data.get(field)).join(' · ');
                review.append(heading, text);
            }
        }
    }
    form.querySelectorAll('[data-next]').forEach(button => button.addEventListener('click', () => {if (valid(current)) show(current + 1);}));
    form.querySelectorAll('[data-back]').forEach(button => button.addEventListener('click', () => show(current - 1)));
    form.querySelectorAll('[name=metodo]').forEach(input => input.addEventListener('change', () => {
        pay.textContent = input.value === 'inmediato' ? 'Pagar ' + document.getElementById('checkoutTotal').textContent : 'Confirmar pedido a contrarrembolso';
    }));
    // Cada paso se valida por separado para poder enfocar campos ocultos si falta algún dato.
    form.noValidate = true;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (current !== 2) {if (valid(current)) show(current + 1); return;}
        for (let index = 0; index < steps.length; index++) {
            if (![...steps[index].querySelectorAll('input')].every(input => input.checkValidity())) {show(index); valid(index); return;}
        }
        if (pay.disabled) return;
        const fields = new FormData(form);
        const data = {token: form.dataset.token};
        for (const key of ['nombre', 'apellidos', 'email', 'telefono', 'metodo']) data[key] = fields.get(key);
        for (const group of ['envio', 'facturacion']) {
            data[group] = {};
            for (const key of ['direccion', 'ciudad', 'codigo_postal']) data[group][key] = fields.get(group + '_' + key);
        }
        pay.disabled = true;
        feedback.textContent = 'Procesando tu pedido…';
        try {
            const csrf = document.cookie.split('; ').find(cookie => cookie.startsWith('csrf_token='));
            const response = await fetch('/api/compra', {method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf ? decodeURIComponent(csrf.slice(11)) : ''},
                body: JSON.stringify(data)});
            const result = await response.json();
            if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Revisa los datos de contacto y las direcciones.');
            document.querySelector('.checkout-layout').hidden = true;
            document.querySelector('.checkout-steps').hidden = true;
            document.getElementById('purchaseSuccess').hidden = false;
            document.getElementById('successDetails').textContent = 'Código: ' + result.codigo + '. Total: ' + result.total + ' €. ' +
                (result.pago_completado ? 'Pago simulado completado.' : 'Pago pendiente al recibir el pedido.');
        } catch (error) {feedback.textContent = error.message || 'No se pudo confirmar. Puedes volver a intentarlo.';}
        finally {pay.disabled = false;}
    });
})();
