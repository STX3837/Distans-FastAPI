"""Tres escenarios de carga comparables con DISTANS-Django."""

from __future__ import annotations

import os
import random
import re
import uuid
from dataclasses import dataclass
from itertools import count

from locust import HttpUser, LoadTestShape, between, events, task


SCENARIO = os.getenv("LOAD_STAGES", "baseline").lower()
VALID_SCENARIOS = {"baseline", "stress", "write"}
if SCENARIO not in VALID_SCENARIOS:
    raise ValueError(f"LOAD_STAGES debe ser uno de: {', '.join(sorted(VALID_SCENARIOS))}")

PASSWORD = os.getenv("LOAD_PASSWORD", "DemoDistans2026!")
BUYER_EMAIL = os.getenv("LOAD_BUYER_EMAIL", "comprador@demo.example.com")
SELLER_EMAIL = os.getenv("LOAD_SELLER_EMAIL", "libreria@demo.example.com")
MAX_FAILURE_RATIO = float(os.getenv("LOAD_MAX_FAILURE_RATIO", "0.01"))
MAX_P95_MS = int(os.getenv("LOAD_MAX_P95_MS", "1200"))
SMOKE_SECONDS = int(os.getenv("LOAD_SMOKE_SECONDS", "0"))
SMOKE_USERS = int(os.getenv("LOAD_SMOKE_USERS", "2"))

PRODUCT_RE = re.compile(r'href=["\']/productos/(\d+)["\']')
# Solo imita controles que un navegador permitiría pulsar. Las tarjetas mantienen
# ``data-add-cart`` en botones deshabilitados para productos agotados o no disponibles.
CART_PRODUCT_RE = re.compile(
    r'<button(?=[^>]*\bdata-add-cart=["\'](\d+)["\'])(?![^>]*\bdisabled\b)[^>]*>'
)
SELLER_STORE_RE = re.compile(r'href=["\']/gestion/tiendas/(\d+)/productos["\']')
ORDER_RE = re.compile(r'action=["\']/gestion/tiendas/(\d+)/pedidos/(\d+)/estado["\']')
WRITE_USER_SEQUENCE = count()


def _ids(pattern: re.Pattern[str], html: str) -> list[int]:
    return list(dict.fromkeys(int(value) for value in pattern.findall(html)))


class DistansUser(HttpUser):
    abstract = True
    wait_time = between(1, 3)

    def csrf_headers(self) -> dict[str, str]:
        return {"X-CSRF-Token": self.client.cookies.get("csrf_token", "")}

    def login(self, email: str) -> None:
        self.client.get("/login", name="GET /login")
        with self.client.post(
            "/api/login",
            json={"email": email, "contrasena": PASSWORD},
            name="POST /api/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"no se pudo iniciar sesión como {email}")

    def discover_catalog(self) -> None:
        with self.client.get("/inicio", params={"tab": "productos"},
                             name="GET /inicio [catálogo]", catch_response=True) as response:
            self.product_ids = _ids(PRODUCT_RE, response.text) if response.status_code == 200 else []
            self.cart_product_ids = _ids(CART_PRODUCT_RE, response.text) if response.status_code == 200 else []
            if not self.product_ids:
                response.failure("el catálogo no contiene productos; ejecuta scripts.seed_catalogo")


class BrowseUser(DistansUser):
    abstract = SCENARIO == "write"
    weight = 7

    def on_start(self):
        self.product_ids, self.cart_product_ids = [], []
        access = self.client.get("/", name="GET / [acceso invitado]")
        self.client.post("/invitado", data={"csrf_token": self.client.cookies.get("csrf_token", "")},
                         headers={"Referer": f"{self.host}/"}, name="POST /invitado",
                         allow_redirects=True)
        self.discover_catalog()

    @task(8)
    def catalog(self):
        self.client.get("/inicio", params={"tab": "productos"}, name="GET /inicio [catálogo]")

    @task(4)
    def filtered_catalog(self):
        params = random.choice([
            {"tab": "productos", "categoria": "Cultura y ocio"},
            {"tab": "productos", "categoria": "Tecnología y electrónica", "precio_max": "60"},
            {"tab": "productos", "precio_min": "5", "precio_max": "35", "valoracion_min": "0"},
        ])
        self.client.get("/inicio", params=params, name="GET /inicio [filtros]")

    @task(4)
    def product_detail(self):
        if self.product_ids:
            self.client.get(f"/productos/{random.choice(self.product_ids)}", name="GET /productos/:id")

    @task(2)
    def stores(self):
        self.client.get("/inicio", params={"tab": "tiendas"}, name="GET /inicio [tiendas]")

    @task(2)
    def map(self):
        self.client.get("/inicio", params={"tab": "mapa"}, name="GET /inicio [mapa]")

    @task(1)
    def cart_flow(self):
        if not self.cart_product_ids:
            return
        product_id = random.choice(self.cart_product_ids)
        # Fijar la cantidad evita que una sesión acumule unidades durante toda la
        # prueba y termine provocando un 409 legítimo al superar el stock.
        with self.client.put(
            f"/api/carrito/productos/{product_id}", json={"cantidad": 1},
            headers=self.csrf_headers(), name="PUT /api/carrito/productos/:id",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                try:
                    detail = response.json().get("detail", response.text[:200])
                except ValueError:
                    detail = response.text[:200]
                response.failure(f"carrito rechazado ({response.status_code}): {detail}")
        self.client.get("/carrito", name="GET /carrito")


class BuyerUser(DistansUser):
    abstract = SCENARIO == "write"
    weight = 2

    def on_start(self):
        self.product_ids, self.cart_product_ids = [], []
        self.login(BUYER_EMAIL)
        self.discover_catalog()

    @task(4)
    def favorites(self):
        self.client.get("/favoritos", name="GET /favoritos")

    @task(4)
    def order_history(self):
        self.client.get("/pedidos/historial", name="GET /pedidos/historial")

    @task(2)
    def account(self):
        self.client.get("/usuarios/cuenta", name="GET /usuarios/cuenta")

    @task(3)
    def catalog(self):
        self.client.get("/inicio", params={"tab": "productos"}, name="GET /inicio [catálogo]")


class SellerUser(DistansUser):
    abstract = SCENARIO == "write"
    weight = 1

    def on_start(self):
        self.login(SELLER_EMAIL)
        page = self.client.get("/mi-tienda", name="GET /mi-tienda [preparación]")
        match = SELLER_STORE_RE.search(page.text)
        self.store_id = int(match.group(1)) if match else None

    @task(5)
    def dashboard(self):
        self.client.get("/mi-tienda", name="GET /mi-tienda")

    @task(4)
    def orders(self):
        if self.store_id:
            self.client.get(f"/gestion/tiendas/{self.store_id}/pedidos", name="GET /gestion/tiendas/:id/pedidos")

    @task(1)
    def filtered_orders(self):
        if self.store_id:
            self.client.get(f"/gestion/tiendas/{self.store_id}/pedidos", params={"q": "PED-DEMO"},
                            name="GET /gestion/tiendas/:id/pedidos [filtro]")


class WriteUser(DistansUser):
    """Un producto temporal por usuario y transiciones sobre pedidos aislados."""

    abstract = SCENARIO != "write"
    wait_time = between(2, 4)

    def on_start(self):
        self.product_id = None
        self.order_id = None
        self.order_state_index = 0
        self.marker = f"LOADTEST-{uuid.uuid4().hex[:12]}"
        self.login(SELLER_EMAIL)
        dashboard = self.client.get("/mi-tienda", name="GET /mi-tienda [preparación write]")
        match = SELLER_STORE_RE.search(dashboard.text)
        if not match:
            return
        self.store_id = int(match.group(1))
        self._create_product()
        orders = self.client.get(f"/gestion/tiendas/{self.store_id}/pedidos", params={"q": "LOAD-WRITE"},
                                 name="GET pedidos [preparación write]")
        candidates = list(dict.fromkeys(ORDER_RE.findall(orders.text)))
        if candidates:
            _, order_id = candidates[next(WRITE_USER_SEQUENCE) % len(candidates)]
            self.order_id = int(order_id)

    def product_data(self) -> dict:
        return {
            "nombre": self.marker,
            "descripcion": "Producto temporal de la prueba de carga.",
            "precio": random.choice([18.9, 19.9, 20.9]),
            "precio_oferta": None,
            "marca": "LOADTEST",
            "categoria": "Tecnología y electrónica",
            "imagen": "",
            "disponible": True,
            "destacado": False,
            "stock": 10,
        }

    def _create_product(self):
        with self.client.post(
            f"/api/gestion/tiendas/{self.store_id}/productos", json=self.product_data(),
            headers=self.csrf_headers(), name="POST crear producto", catch_response=True,
        ) as response:
            if response.status_code == 201:
                self.product_id = response.json().get("id")
            if not self.product_id:
                response.failure(f"no se pudo crear el producto temporal: {response.status_code} {response.text[:200]}")

    @task(5)
    def edit_product(self):
        if not self.product_id:
            return
        data = self.product_data()
        data["descripcion"] = "Producto temporal editado por la prueba de carga."
        with self.client.put(
            f"/api/gestion/productos/{self.product_id}", json=data, headers=self.csrf_headers(),
            name="PUT editar producto", catch_response=True,
        ) as response:
            if response.status_code != 200 or response.json().get("nombre") != self.marker:
                response.failure("la edición del producto no se guardó")

    @task(1)
    def advance_order(self):
        if not self.order_id or self.order_state_index >= 2:
            return
        state = ("listo para recoger", "recogido")[self.order_state_index]
        with self.client.post(
            f"/gestion/tiendas/{self.store_id}/pedidos/{self.order_id}/estado",
            data={"estado": state, "csrf_token": self.client.cookies.get("csrf_token", "")},
            headers={"Referer": f"{self.host}/gestion/tiendas/{self.store_id}/pedidos"},
            name="POST editar estado pedido", catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"el pedido devolvió {response.status_code}")
            else:
                self.order_state_index += 1

    def on_stop(self):
        if not self.product_id:
            return
        with self.client.delete(
            f"/api/gestion/productos/{self.product_id}", headers=self.csrf_headers(),
            name="DELETE limpiar producto temporal", catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure("no se pudo limpiar el producto temporal")


@dataclass(frozen=True)
class Stage:
    duration: int
    users: int
    spawn_rate: float


PRESETS = {
    "baseline": [Stage(60, 10, 2), Stage(180, 25, 3), Stage(240, 10, 5)],
    "stress": [Stage(60, 25, 5), Stage(180, 75, 10), Stage(300, 150, 15), Stage(360, 25, 25)],
    "write": [Stage(30, 2, 1), Stage(120, 5, 1), Stage(180, 2, 2)],
}


class StagedLoadShape(LoadTestShape):
    stages = [Stage(SMOKE_SECONDS, SMOKE_USERS, SMOKE_USERS)] if SMOKE_SECONDS > 0 else PRESETS[SCENARIO]

    def tick(self):
        elapsed = self.get_run_time()
        for stage in self.stages:
            if elapsed < stage.duration:
                return stage.users, stage.spawn_rate
        return None


@events.quitting.add_listener
def enforce_quality_gates(environment, **_kwargs):
    stats = environment.stats.total
    violations = []
    if stats.num_requests == 0:
        violations.append("no se registraron peticiones")
    if stats.fail_ratio > MAX_FAILURE_RATIO:
        violations.append(f"errores {stats.fail_ratio:.2%} > {MAX_FAILURE_RATIO:.2%}")
    p95 = stats.get_response_time_percentile(0.95) or 0
    if p95 > MAX_P95_MS:
        violations.append(f"p95 {p95:.0f} ms > {MAX_P95_MS} ms")
    if violations:
        environment.process_exit_code = 1
        print("LOAD TEST FAILED: " + "; ".join(violations))
