document.querySelectorAll('.comment-form').forEach(form => {
    const status = form.querySelector('[data-comment-status]');
    const endpoint = `/api/comentarios/${form.dataset.commentType}/${form.dataset.commentId}`;
    const csrf = () => document.cookie.split('; ').find(part => part.startsWith('csrf_token='))?.split('=')[1] || '';

    async function guardar(method, body) {
        const response = await fetch(endpoint, {
            method,
            headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf()},
            ...(body ? {body: JSON.stringify(body)} : {}),
        });
        const data = await readApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data && data.detail, 'No se pudo guardar el comentario. Inténtalo de nuevo.'));
        window.location.reload();
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type=submit]');
        button.disabled = true;
        status.textContent = 'Guardando...';
        try {
            await guardar('PUT', {texto: form.elements.texto.value});
        } catch (error) {
            status.textContent = error.message;
            button.disabled = false;
        }
    });

    form.querySelector('[data-delete-comment]')?.addEventListener('click', async event => {
        event.currentTarget.disabled = true;
        status.textContent = 'Eliminando...';
        try {
            await guardar('DELETE');
        } catch (error) {
            status.textContent = error.message;
            event.currentTarget.disabled = false;
        }
    });
});

document.querySelectorAll('.admin-comment-form').forEach(form => {
    const endpoint = `/api/admin/comentarios/${form.dataset.commentType}/${form.dataset.commentId}/${form.dataset.commentUserId}`;
    const status = form.querySelector('[data-comment-status]');
    const csrf = () => document.cookie.split('; ').find(part => part.startsWith('csrf_token='))?.split('=')[1] || '';

    async function cambiar(method, body) {
        const response = await fetch(endpoint, {
            method,
            headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf()},
            ...(body ? {body: JSON.stringify(body)} : {}),
        });
        const data = await readApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(data && data.detail, 'No se pudo modificar el comentario. Inténtalo de nuevo.'));
        window.location.reload();
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type=submit]');
        button.disabled = true;
        status.textContent = 'Guardando...';
        try {
            await cambiar('PUT', {texto: form.elements.texto.value});
        } catch (error) {
            status.textContent = error.message;
            button.disabled = false;
        }
    });

    form.querySelector('[data-admin-delete-comment]').addEventListener('click', async event => {
        event.currentTarget.disabled = true;
        status.textContent = 'Borrando...';
        try {
            await cambiar('DELETE');
        } catch (error) {
            status.textContent = error.message;
            event.currentTarget.disabled = false;
        }
    });
});
