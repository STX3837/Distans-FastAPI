
# Distans-FastAPI ⚡🌍


Este es un proyecto base para la creación de APIs de alto rendimiento utilizando FastAPI, SQLAlchemy (con GeoAlchemy2) y PostgreSQL + PostGIS, completamente dockerizado para un entorno de desarrollo aislado.

## Índice
- [Requisitos Previos](#requisitos-previos)
- [Instalación y Despliegue Local](#instalación-y-despliegue-local)
- [Configuración](#configuración)
- [Acceso a la API](#acceso-a-la-api)
- [Comandos Útiles](#comandos-útiles)
- [Recarga automática (Hot Reload)](#recarga-automática-hot-reload)

## 📋 Requisitos Previos
Para poder ejecutar este proyecto en tu máquina local, necesitas tener instalado:

- Git
- Docker (y Docker Compose, incluido en Docker Desktop)

## 🚀 Instalación y Despliegue Local
Sigue estos pasos para levantar el entorno de desarrollo desde cero.

### 1. Clonar el repositorio
Abre tu terminal y ejecuta:

```bash
git clone https://github.com/STX3837/Distans-FastAPI.git
cd Distans-FastAPI
```

También puedes clonar usando el enlace: https://github.com/STX3837/Distans-FastAPI.git

### 2. Configurar las variables de entorno
Por seguridad, las credenciales de la base de datos no se suben al repositorio. Debes crear un archivo llamado `.env` en la raíz del proyecto (al mismo nivel que `docker-compose.yml`) con el siguiente contenido:

```env
DB_NAME=mi_base_datos
DB_USER=mi_usuario
DB_PASSWORD=una_contraseña_segura
SESSION_SECRET_KEY=una_clave_aleatoria_larga_y_privada
```

### 3. Construir y levantar los contenedores
Con Docker ejecutándose en tu máquina, construye y levanta los servicios en segundo plano:

```bash
docker-compose up -d --build
```

> Nota: La primera vez que ejecutes este comando, Docker descargará imágenes y instalará dependencias; puede tardar varios minutos.

## 💻 Acceso a la API
Una vez que los contenedores estén corriendo, accede a través de tu navegador:

- **Pantalla de acceso:** [http://localhost:8001/](http://localhost:8001/)
- **Página de inicio con productos:** [http://localhost:8001/inicio](http://localhost:8001/inicio)
- **Registro:** [http://localhost:8001/registro](http://localhost:8001/registro)
- **Inicio de sesión:** [http://localhost:8001/login](http://localhost:8001/login)
- **Mi cuenta:** [http://localhost:8001/usuarios/cuenta](http://localhost:8001/usuarios/cuenta) (requiere iniciar sesión)
- **Administración:** [http://localhost:8001/admin/usuarios/panel](http://localhost:8001/admin/usuarios/panel) (requiere una cuenta administradora)
- **Recuperar contraseña:** [http://localhost:8001/recuperar-contrasena](http://localhost:8001/recuperar-contrasena)
- Documentación Interactiva (Swagger UI): http://localhost:8001/docs
- Documentación Alternativa (ReDoc): http://localhost:8001/redoc

(Nota: la API está expuesta en el puerto `8001` en este README para evitar conflictos con otros servicios web que puedan estar corriendo en el puerto `8000`. Asegúrate de que el mapeo en `docker-compose.yml` coincida con el puerto que uses.)

## 🛠️ Comandos Útiles de Docker y FastAPI
Aquí tienes una lista de comandos de referencia rápida para gestionar tu entorno desde la terminal:

Ver los logs (registros) de la API en tiempo real:

```bash
docker-compose logs -f web
```

Detener los contenedores:

```bash
docker-compose down
```

Reiniciar la API (si instalas una nueva dependencia):

```bash
docker-compose restart web
```

Acceder a la base de datos PostGIS desde la terminal:

```bash
docker-compose exec db psql -U mi_usuario -d mi_base_datos
```

## 🔄 Recarga automática (Hot Reload)
El servicio web está configurado con la recarga activa. Esto significa que si haces un cambio en el archivo `main.py` (o cualquier otro archivo Python de tu proyecto), el servidor se reiniciará automáticamente dentro del contenedor en fracciones de segundo. ¡No necesitas reiniciar Docker para ver tus cambios!

---
Reiniciar la API (si instalas una nueva dependencia):

```bash
docker-compose restart web
```
Acceder a la base de datos PostGIS desde la terminal:

```bash
docker-compose exec db psql -U mi_usuario -d mi_base_datos
```
🔄 Sobre la recarga automática (Hot Reload)
El servicio web está configurado con la recarga activa. Esto significa que si haces un cambio en el archivo main.py (o cualquier otro archivo Python de tu proyecto), el servidor se reiniciará automáticamente dentro del contenedor en fracciones de segundo. ¡No necesitas reiniciar Docker para ver tus cambios!


## Cuenta, administración y recuperación de contraseña

- `/usuarios/cuenta`: consulta y edición de datos, incluido email, y cambio de contraseña.
- `/admin/usuarios/panel`: listado paginado, creación, edición y eliminación. Requiere un administrador existente; el registro público solo admite comprador o vendedor.
- `/recuperar-contrasena`: envío de un enlace por correo. `/restablecer-contrasena`: formulario para establecer la nueva contraseña.

Configura `SESSION_SECRET_KEY`, `PUBLIC_BASE_URL` y las variables `SMTP_*` de `.env.example` en `.env`. Docker Compose carga este archivo. En producción usa `ENVIRONMENT=production`, una URL pública HTTPS y SMTP con STARTTLS. No guardes credenciales reales en el repositorio. Para pruebas locales puede utilizarse un servidor SMTP de desarrollo, con `SMTP_STARTTLS=false` y su puerto correspondiente. Si el envío falla, se registra un error sin exponer el correo o el token y se permite reintentar.

Las contraseñas nuevas admiten entre 8 y 128 caracteres y se almacenan con PBKDF2-SHA256, salt aleatoria y 600000 iteraciones. Las contraseñas existentes siguen verificándose. El cambio o restablecimiento invalida las sesiones anteriores. Las operaciones de edición autenticadas requieren `X-CSRF-Token` con el valor de la cookie `csrf_token`.

Los enlaces caducan en 30 minutos, son de un solo uso y quedan invalidados si cambia el email o la contraseña. La respuesta de recuperación no revela si existe la cuenta; las solicitudes a la misma cuenta tienen un intervalo de un minuto. La tabla nueva `restablecimientos_contrasena` se crea al arrancar mediante el mecanismo existente `create_all`, sin alterar los datos de usuarios existentes.

La eliminación de usuarios conserva las cascadas existentes para carrito y pedidos. Si el usuario tiene tiendas, devuelve un error 409: deben reasignarse o eliminarse antes. El panel solicita confirmación antes de eliminar la cuenta.

Pruebas: instala `pip install -r requirements-dev.txt` y ejecuta `python -m pytest -q`. Las pruebas de API usan SQLite en memoria y sustituyen el envío SMTP; no envían correos reales ni usan la base de producción.

Criterios: [almacenamiento de contraseñas de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) y [recuperación de contraseña de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

