(() => {
    let attempts = 0;
    async function check() {
        if (++attempts > 24) return;
        try {
            const response = await fetch('/api/pago/estado', {cache: 'no-store'});
            if (response.status === 401 || response.status === 403 || response.status === 404) return;
            if (response.ok) {
                const status = await response.json();
                if (status.completado || status.caducado) {window.location.reload(); return;}
            }
        } catch (_) {}
        window.setTimeout(check, 5000);
    }
    window.setTimeout(check, 3000);
})();
