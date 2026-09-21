document.querySelectorAll('.rating-form').forEach(form => {
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('button[type=submit]');
        const status = form.querySelector('[data-rating-status]');
        button.disabled = true;
        status.textContent = 'Guardando...';
        try {
            const token = document.cookie.split('; ').find(part => part.startsWith('csrf_token='))?.split('=')[1] || '';
            const response = await fetch(`/api/valoraciones/${form.dataset.ratingType}/${form.dataset.ratingId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token},
                body: JSON.stringify({puntuacion: Number(form.elements.puntuacion.value)}),
            });
            if (!response.ok) throw new Error('No se pudo guardar la valoración. Inténtalo de nuevo.');
            window.location.reload();
        } catch (error) {
            status.textContent = error.message;
            button.disabled = false;
        }
    });
});
