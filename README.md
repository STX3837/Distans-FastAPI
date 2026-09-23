# Distans

Plataforma web para digitalizar el comercio local y acercar sus productos a clientes de la zona.

Distans es una aplicaciÃ³n desarrollada como Trabajo de Fin de Grado. El proyecto aborda el ciclo completo de un marketplace de proximidad: descubrimiento geogrÃ¡fico de comercios, publicaciÃ³n de catÃ¡logos, compra, seguimiento de pedidos y gestiÃ³n diferenciada para clientes, vendedores y administradores.

## PropÃ³sito del proyecto

Los pequeÃ±os comercios suelen disponer de menos recursos para ofrecer visibilidad y venta digital. Distans propone un punto de encuentro donde cada establecimiento mantiene su propio catÃ¡logo y el usuario puede encontrar productos disponibles cerca de su ubicaciÃ³n.

Los objetivos principales son:

- facilitar la presencia digital de comercios locales;
- permitir la bÃºsqueda de tiendas y productos por proximidad;
- ofrecer un proceso de compra completo y consistente;
- separar con claridad los permisos de compradores, vendedores y administradores;
- proporcionar una aplicaciÃ³n accesible desde ordenador, tableta y mÃ³vil;
- aplicar validaciÃ³n, autenticaciÃ³n y autorizaciÃ³n en el servidor.

## Funcionalidades principales

### Clientes e invitados

- ExploraciÃ³n de productos y tiendas mediante listado o mapa.
- BÃºsqueda por texto, categorÃ­a, precio, modalidad, valoraciÃ³n y radio geogrÃ¡fico.
- Fichas detalladas de tiendas y productos.
- Carrito persistente y compra directa.
- Pago mediante Stripe Checkout o contrarrembolso.
- Historial y seguimiento de pedidos.
- Favoritos, valoraciones y comentarios para compradores registrados.

### Vendedores

- Una tienda por cuenta de vendedor.
- EdiciÃ³n de datos comerciales, localizaciÃ³n y horario.
- Alta, modificaciÃ³n y retirada de productos.
- Control de disponibilidad y stock.
- GestiÃ³n exclusiva de los pedidos correspondientes a su tienda.
- EstadÃ­sticas de visitas y actividad.
- Planes Freemium y Premium.

### AdministraciÃ³n

- GestiÃ³n de usuarios, roles y estado de las cuentas.
- SupervisiÃ³n de tiendas, productos, suscripciones y pedidos.
- ModeraciÃ³n de comentarios.
- Acceso global reservado al rol administrador.

## Arquitectura y tecnologÃ­as

La aplicaciÃ³n sigue una arquitectura web renderizada en servidor con una API HTTP integrada.

```text
Navegador
   |
   | HTTP / sesiones firmadas / CSRF
   v
FastAPI + Jinja2
   |
   | SQLAlchemy / GeoAlchemy2
   v
PostgreSQL + PostGIS

Servicios auxiliares: Stripe Checkout y servidor SMTP
```

| Capa | TecnologÃ­a |
|---|---|
| Backend | Python 3.11, FastAPI y Pydantic 2 |
| Persistencia | SQLAlchemy 2, PostgreSQL 15 y PostGIS |
| Interfaz | Jinja2, HTML, CSS y JavaScript |
| CartografÃ­a | Leaflet y PostGIS |
| Pagos | Stripe Checkout y webhooks |
| Correo de desarrollo | Mailpit |
| Infraestructura | Docker y Docker Compose |
| Calidad | Pytest y SQLite en memoria |

## Puesta en marcha

### Requisitos

- Git.
- Docker Desktop o Docker Engine con Docker Compose.

### InstalaciÃ³n

```bash
git clone https://github.com/STX3837/Distans-FastAPI.git
cd Distans-FastAPI
cp .env.example .env
docker compose up -d --build
```

En PowerShell, utiliza `Copy-Item .env.example .env` en lugar de `cp`.

Antes de levantar un entorno pÃºblico deben sustituirse las credenciales de PostgreSQL y `SESSION_SECRET_KEY` de `.env`. El valor de sesiÃ³n debe ser largo, aleatorio y privado.

Una vez iniciados los contenedores:

- AplicaciÃ³n: <http://localhost:8001>
- DocumentaciÃ³n OpenAPI: <http://localhost:8001/docs>
- DocumentaciÃ³n alternativa: <http://localhost:8001/redoc>
- Bandeja de correo de desarrollo: <http://localhost:8025>

## Entorno de demostraciÃ³n

El proyecto incluye un generador autosuficiente de datos de prueba. Puede ejecutarse inmediatamente despuÃ©s de levantar una base vacÃ­a y no necesita cuentas creadas previamente.

```bash
docker compose exec web python -m scripts.seed_catalogo
```

El comando es aditivo e idempotente: puede ejecutarse varias veces sin eliminar ni duplicar los datos ya creados. En concreto:

- conserva todas las cuentas y todos los datos existentes;
- crea un administrador, un comprador y diez vendedores;
- asigna exactamente una tienda a cada vendedor;
- crea diez comercios geolocalizados en Carmona y Sevilla y treinta productos variados;
- incorpora imÃ¡genes de muestra, ofertas, stock, favoritos, valoraciones y comentarios;
- aÃ±ade un pedido entregado para probar los historiales y paneles;
- crea exclusivamente los elementos de demostraciÃ³n que todavÃ­a falten.

El antiguo argumento `--reset` se conserva temporalmente por compatibilidad, pero ya no elimina informaciÃ³n. El script estÃ¡ destinado a desarrollo y evaluaciÃ³n.

### Credenciales de prueba

Todas las cuentas siguientes utilizan la contraseÃ±a `DistansDemo2026!`:

| Perfil | Correo | Contenido asociado |
|---|---|---|
| Administrador | `demo.admin@distans-demo.com` | Panel global |
| Comprador | `demo.comprador@distans-demo.com` | Favoritos, reseÃ±as y pedido de muestra |
| Vendedor 1 | `demo.vendedor1@distans-demo.com` | Comercio Carmona |
| Vendedor 2 | `demo.vendedor2@distans-demo.com` | ArtesanÃ­a AlcÃ¡zar |
| Vendedor 3 | `demo.vendedor3@distans-demo.com` | Tecno CampiÃ±a |
| Vendedor 4 | `demo.vendedor4@distans-demo.com` | Verde Alcores |
| Vendedor 5 | `demo.vendedor5@distans-demo.com` | LibrerÃ­a Puerta Sevilla |
| Vendedor 6 | `demo.vendedor6@distans-demo.com` | Sabores de Triana (Sevilla) |
| Vendedor 7 | `demo.vendedor7@distans-demo.com` | Bienestar NerviÃ³n (Sevilla) |
| Vendedor 8 | `demo.vendedor8@distans-demo.com` | Flores de la Macarena (Sevilla) |
| Vendedor 9 | `demo.vendedor9@distans-demo.com` | Cultura Alameda (Sevilla) |
| Vendedor 10 | `demo.vendedor10@distans-demo.com` | TecnologÃ­a Sevilla Este (Sevilla) |

La contraseÃ±a puede personalizarse sin editar el cÃ³digo:

```bash
docker compose exec -e DEMO_PASSWORD="OtraClaveDePruebaSegura!" web python -m scripts.seed_catalogo
```

## ConfiguraciÃ³n

Las variables disponibles se documentan en `.env.example`.

| Variable | DescripciÃ³n |
|---|---|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Nombre y credenciales de PostgreSQL |
| `DB_HOST`, `DB_PORT` | DirecciÃ³n del servidor PostgreSQL |
| `SESSION_SECRET_KEY` | Firma criptogrÃ¡fica de las sesiones |
| `ENVIRONMENT` | Entorno `development`, `staging` o `production` |
| `ALLOWED_HOSTS` | Hosts HTTP admitidos, separados por comas |
| `PUBLIC_BASE_URL` | URL utilizada en enlaces y retornos externos |
| `SMTP_*` | ConfiguraciÃ³n para recuperaciÃ³n de contraseÃ±as |
| `STRIPE_SECRET_KEY` | Clave privada de Stripe |
| `STRIPE_WEBHOOK_SECRET` | Secreto de validaciÃ³n de webhooks |
| `CHECKOUT_IVA` | Tipo de IVA aplicado al pedido |
| `CHECKOUT_ENVIO` | Coste fijo de entrega |

Para producciÃ³n deben configurarse HTTPS, `ENVIRONMENT=production`, hosts explÃ­citos, secretos externos al repositorio, SMTP con STARTTLS y credenciales Stripe del entorno correspondiente.

## Modelo de permisos

La interfaz oculta las acciones no disponibles, pero la protecciÃ³n efectiva se aplica siempre en el servidor.

| Recurso | Comprador | Vendedor | Administrador |
|---|---:|---:|---:|
| CatÃ¡logo pÃºblico | Lectura | Limitado a su contexto | Lectura global |
| Perfil propio | SÃ­ | SÃ­ | SÃ­ |
| Carrito y pedidos propios | SÃ­ | No | SupervisiÃ³n global |
| Tienda y productos | No | Solo los propios | Todas las tiendas |
| Subpedidos | No | Solo los de su tienda | Todos |
| Usuarios y suscripciones | No | No | SÃ­ |

## Seguridad

El proyecto incorpora:

- contraseÃ±as derivadas mediante PBKDF2-SHA256 con sal aleatoria;
- sesiones firmadas, cookies `SameSite=Lax` y cookies `Secure` fuera de desarrollo;
- invalidaciÃ³n de sesiones tras cambiar o restablecer la contraseÃ±a;
- protecciÃ³n CSRF de doble envÃ­o en operaciones autenticadas;
- comprobaciones de rol y propiedad en cada recurso privado;
- validaciÃ³n Pydantic de tipos, longitudes, rangos y enumeraciones;
- control transaccional de stock y recÃ¡lculo de importes en el servidor;
- verificaciÃ³n de firma y lÃ­mite de 5 MB para imÃ¡genes;
- validaciÃ³n de `Host`, CSP, HSTS en producciÃ³n y protecciÃ³n contra framing y MIME sniffing;
- verificaciÃ³n criptogrÃ¡fica de webhooks de Stripe.

Estas medidas reducen la superficie de ataque, pero no sustituyen una auditorÃ­a profesional. Un despliegue real debe aÃ±adir monitorizaciÃ³n, copias de seguridad, actualizaciÃ³n periÃ³dica de dependencias, limitaciÃ³n de intentos en el proxy y revisiÃ³n externa.

## Pruebas

La suite automatizada cubre autenticaciÃ³n, perfiles, autorizaciÃ³n por roles, catÃ¡logo, filtros, carrito, compra, pagos, favoritos, valoraciones, comentarios, administraciÃ³n y estados de pedidos.

```bash
docker compose exec -e PYTHONPATH=/app web python -m pytest -q
```

## Estructura del repositorio

```text
app/
  routers/            endpoints y vistas por dominio
  models.py           entidades y relaciones SQLAlchemy
  schemas.py          contratos y validaciÃ³n Pydantic
  security.py         contraseÃ±as y utilidades de seguridad
  migrations.py       actualizaciones incrementales del esquema
scripts/
  seed_catalogo.py    entorno reproducible de demostraciÃ³n
templates/            vistas Jinja2
static/               estilos, JavaScript, recursos y Leaflet
tests/                pruebas automatizadas
migrations/           documentaciÃ³n y SQL histÃ³rico
main.py               configuraciÃ³n principal de FastAPI
docker-compose.yml    servicios de aplicaciÃ³n, base de datos y correo
```

## Operaciones habituales

```bash
# Consultar los registros
docker compose logs -f web

# Detener los servicios conservando la base de datos
docker compose down

# Detener los servicios y eliminar tambiÃ©n el volumen de datos
docker compose down -v
```

PostgreSQL utiliza el volumen `fastapi_postgres_data`. La opciÃ³n `down -v` lo elimina de forma irreversible.

## Estado y alcance acadÃ©mico

Distans implementa un producto funcional completo para su evaluaciÃ³n como TFG. El entorno incluido estÃ¡ orientado a desarrollo y demostraciÃ³n. Para convertirlo en un servicio comercial serÃ­a recomendable incorporar migraciones versionadas con Alembic, observabilidad centralizada, almacenamiento externo de imÃ¡genes, copias automatizadas, despliegue continuo y una auditorÃ­a de seguridad independiente.

