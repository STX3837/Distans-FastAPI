Distans-FastAPI ⚡🌍
Este es un proyecto base para la creación de APIs de alto rendimiento utilizando FastAPI, SQLAlchemy (con GeoAlchemy2) y PostgreSQL + PostGIS, completamente dockerizado para un entorno de desarrollo aislado.
<!-- Badges -->
# Distans-FastAPI ⚡🌍

![Python](https://img.shields.io/badge/python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-%2300BCD4.svg?style=flat&logo=fastapi) ![Docker](https://img.shields.io/badge/docker-%23007ACC.svg?style=flat&logo=docker) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

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
```

### 3. Construir y levantar los contenedores
Con Docker ejecutándose en tu máquina, construye y levanta los servicios en segundo plano:

```bash
docker-compose up -d --build
```

> Nota: La primera vez que ejecutes este comando, Docker descargará imágenes y instalará dependencias; puede tardar varios minutos.

## 💻 Acceso a la API
Una vez que los contenedores estén corriendo, accede a través de tu navegador:

- Respuesta JSON de prueba: http://localhost:8001
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
