from html import escape
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.models import Usuario
from app.schemas import UsuarioCreate
from app.crud import autenticar_usuario, crear_usuario
from app.database import get_db

router = APIRouter(
    tags=["autenticación"],
)


def encabezado_html(ruta_activa: str) -> str:
    return encabezado_html_con_usuario(ruta_activa, None)


def encabezado_html_con_usuario(ruta_activa: str, nombre_usuario: str | None) -> str:
    clase_registro = "topbar-button active" if ruta_activa == "/registro" else "topbar-button"
    clase_login = "topbar-button active" if ruta_activa == "/login" else "topbar-button"
    if nombre_usuario:
        nombre_seguro = escape(nombre_usuario)
        acciones = f"""
            <span class="user-name">{nombre_seguro}</span>
            <button class="topbar-button topbar-logout" type="button" onclick="cerrarSesion()">Cerrar sesión</button>
        """
    else:
        acciones = f"""
            <a class="{clase_registro}" href="/registro">Registrarse</a>
            <a class="{clase_login}" href="/login">Iniciar sesión</a>
            <a class="icon-button" href="/login" aria-label="Usuario">
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 21C20 17.6863 16.4183 15 12 15C7.58172 15 4 17.6863 4 21" stroke="#1E4FA8" stroke-width="1.8" stroke-linecap="round"/>
                    <circle cx="12" cy="8" r="4" stroke="#1E4FA8" stroke-width="1.8"/>
                </svg>
            </a>
            <a class="icon-button" href="/login" aria-label="Carrito">
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2 3H5L7.2 14.2C7.3 14.7 7.7 15 8.2 15H18.6C19.1 15 19.5 14.7 19.6 14.2L21 6H6" stroke="#1E4FA8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="9" cy="20" r="1.4" stroke="#1E4FA8" stroke-width="1.8"/>
                    <circle cx="17" cy="20" r="1.4" stroke="#1E4FA8" stroke-width="1.8"/>
                </svg>
            </a>
        """

    return f"""
    <header class="topbar">
        <a class="brand" href="/registro" aria-label="Distans">
            <div class="brand-mark" aria-hidden="true">
                <svg width="52" height="52" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="8" y="18" width="30" height="30" rx="4" fill="#F3FAFF" stroke="#4AA3DF" stroke-width="2"/>
                    <path d="M12 24H34" stroke="#4AA3DF" stroke-width="2" stroke-linecap="round"/>
                    <path d="M14 30H32" stroke="#4AA3DF" stroke-width="2" stroke-linecap="round"/>
                    <path d="M18 18L18 14C18 11.8 19.8 10 22 10H24C26.2 10 28 11.8 28 14V18" stroke="#4AA3DF" stroke-width="2"/>
                    <circle cx="24" cy="42" r="3" fill="#4AA3DF"/>
                    <path d="M24 52C24 52 33 43.9 33 37.1C33 32.1 29 28 24 28C19 28 15 32.1 15 37.1C15 43.9 24 52 24 52Z" fill="#F3FAFF" stroke="#F0A43A" stroke-width="2"/>
                    <circle cx="24" cy="37" r="2.6" fill="#4AA3DF"/>
                </svg>
            </div>
            <span class="brand-name">DISTANS</span>
        </a>

        <div class="topbar-actions">
            {acciones}
        </div>
    </header>
    """


def estilos_encabezado_html() -> str:
    return """
        .topbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 74px;
            background: #ffffff;
            border-bottom: 1px solid #e8e8e8;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 18px 0 22px;
            z-index: 1000;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #000;
        }

        .brand-mark {
            width: 52px;
            height: 52px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .brand-name {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 40px;
            line-height: 1;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .user-name {
            font-size: 14px;
            font-weight: 700;
            color: #0f2f6b;
            background: #e8f0ff;
            border: 1px solid #bcd0f5;
            border-radius: 999px;
            padding: 8px 12px;
            line-height: 1;
        }

        .topbar-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 36px;
            padding: 0 14px;
            border-radius: 3px;
            background: #4caf50;
            color: #fff;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            border: 1px solid #3d8f42;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
        }

        .topbar-button.active {
            background: #3f9b44;
        }

        .topbar-logout {
            background: #1e4fa8;
            border-color: #173f87;
            color: #fff;
            cursor: pointer;
        }

        .topbar-logout:hover {
            background: #173f87;
        }

        .icon-button {
            width: 40px;
            height: 40px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #1f3e8a;
            text-decoration: none;
        }
    """


class LoginRequest(BaseModel):
    email: EmailStr
    contrasena: str


@router.get("/", response_class=HTMLResponse)
def pagina_inicio():
    """
    Redirección a la página de registro al acceder a la raíz.
    """
    return ("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Distans</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

""" + estilos_encabezado_html() + """

        body {{
            font-family: 'Arial', sans-serif;
            background: #f0f0f0;
            min-height: 100vh;
            padding-top: 74px;
            display: flex;
            align-items: flex-start;
            justify-content: center;
        }}

        .hero {{
            margin-top: 40px;
            background: #b3ff99;
            border-radius: 15px;
            padding: 32px 36px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 520px;
            width: calc(100% - 32px);
        }}

        .hero h1 {{
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 34px;
            color: #000;
            margin-bottom: 10px;
        }}

        .hero p {{
            color: #222;
            margin-bottom: 18px;
        }}

        .hero a {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 40px;
            padding: 0 16px;
            border-radius: 3px;
            background: #4caf50;
            border: 1px solid #3d8f42;
            color: #fff;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
""" + encabezado_html("/registro") + """
    <main class="hero">
        <h1>Bienvenido a Distans</h1>
        <p>Te estamos redirigiendo al registro.</p>
        <a href="/registro">Ir al registro ahora</a>
    </main>
    <script>
        setTimeout(() => {{
            window.location.href = '/registro';
        }}, 1200);
    </script>
</body>
</html>
    """).replace("{{", "{").replace("}}", "}")


@router.get("/registro", response_class=HTMLResponse)
def pagina_registro():
    """
    Sirve la página HTML de registro.
    """
    return ("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crear una cuenta - Distans</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
""" + estilos_encabezado_html() + """

        body {
            font-family: 'Arial', sans-serif;
            background: #f0f0f0;
            min-height: 100vh;
            padding-top: 74px;
        }
        
        .container {
            background: #b3ff99;
            border-radius: 15px;
            width: 100%;
            max-width: 450px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin: 24px auto 40px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 35px;
        }
        
        .header h1 {
            color: #000;
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 3px;
        }
        
        .form-group {
            margin-bottom: 18px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .form-row .form-group {
            margin-bottom: 0;
        }
        
        label {
            display: block;
            margin-bottom: 6px;
            color: #000;
            font-weight: 500;
            font-size: 13px;
        }
        
        input, select {
            width: 100%;
            padding: 10px 12px;
            border: none;
            border-radius: 5px;
            font-size: 13px;
            background: #ffffff;
            transition: box-shadow 0.3s;
            font-family: Arial, sans-serif;
        }
        
        input:focus, select:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
        }
        
        .button {
            width: 100%;
            padding: 12px;
            background: #b3ff99;
            color: #000;
            border: 2px solid #000;
            border-radius: 5px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 15px;
        }
        
        .button:hover {
            background: #9aff7f;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .error-message {
            color: #d32f2f;
            font-size: 11px;
            margin-top: 4px;
            display: none;
        }
        
        .success-message {
            background: #81c784;
            color: #fff;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
            font-size: 14px;
            text-align: center;
        }
    </style>
</head>
<body>
""" + encabezado_html("/registro") + """

    <div class="container">
        <div class="header">
            <h1>Crear una cuenta</h1>
        </div>
        
        <div class="success-message" id="successMessage">
            ✓ Cuenta creada exitosamente
        </div>
        
        <form id="registroForm">
            <div class="form-row">
                <div class="form-group">
                    <label for="email">Correo electrónico</label>
                    <input type="email" id="email" name="email" required>
                    <div class="error-message" id="errorEmail"></div>
                </div>
                <div class="form-group">
                    <label for="telefono">Teléfono</label>
                    <input type="tel" id="telefono" name="telefono">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="nombre">Nombre</label>
                    <input type="text" id="nombre" name="nombre" required>
                    <div class="error-message" id="errorNombre"></div>
                </div>
                <div class="form-group">
                    <label for="apellidos">Apellidos</label>
                    <input type="text" id="apellidos" name="apellidos" required>
                    <div class="error-message" id="errorApellidos"></div>
                </div>
            </div>
            
            <div class="form-group">
                <label for="direccion">Dirección</label>
                <input type="text" id="direccion" name="direccion">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="ciudad">Ciudad</label>
                    <input type="text" id="ciudad" name="ciudad">
                </div>
                <div class="form-group">
                    <label for="codigo_postal">Código Postal</label>
                    <input type="text" id="codigo_postal" name="codigo_postal">
                </div>
            </div>
            
            <div class="form-group">
                <label for="rol">Rol</label>
                <select id="rol" name="rol" required>
                    <option value="">Selecciona un rol</option>
                    <option value="comprador">Comprador</option>
                    <option value="vendedor">Vendedor</option>
                </select>
                <div class="error-message" id="errorRol"></div>
            </div>
            
            <div class="form-group">
                <label for="contrasena">Contraseña</label>
                <input type="password" id="contrasena" name="contrasena" required>
                <div class="error-message" id="errorContrasena"></div>
            </div>
            
            <div class="form-group">
                <label for="contrasena_confirmacion">Confirmar contraseña</label>
                <input type="password" id="contrasena_confirmacion" name="contrasena_confirmacion" required>
                <div class="error-message" id="errorConfirmacion"></div>
            </div>
            
            <button type="submit" class="button">Crear cuenta</button>
        </form>
    </div>
    
    <script>
        const form = document.getElementById('registroForm');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
            
            const nombre = document.getElementById('nombre').value.trim();
            const apellidos = document.getElementById('apellidos').value.trim();
            const email = document.getElementById('email').value.trim();
            const telefono = document.getElementById('telefono').value.trim();
            let rol = document.getElementById('rol').value;
            if (rol) rol = rol.toLowerCase();
            const ciudad = document.getElementById('ciudad').value.trim();
            const direccion = document.getElementById('direccion').value.trim();
            const codigo_postal = document.getElementById('codigo_postal').value.trim();
            const contrasena = document.getElementById('contrasena').value;
            const contrasena_confirmacion = document.getElementById('contrasena_confirmacion').value;
            
            let tieneErrores = false;
            
            if (!nombre) {
                document.getElementById('errorNombre').textContent = 'Requerido';
                document.getElementById('errorNombre').style.display = 'block';
                tieneErrores = true;
            }
            
            if (!apellidos) {
                document.getElementById('errorApellidos').textContent = 'Requerido';
                document.getElementById('errorApellidos').style.display = 'block';
                tieneErrores = true;
            }
            
            if (!email) {
                document.getElementById('errorEmail').textContent = 'Requerido';
                document.getElementById('errorEmail').style.display = 'block';
                tieneErrores = true;
            }
            
            if (!rol) {
                document.getElementById('errorRol').textContent = 'Selecciona un rol';
                document.getElementById('errorRol').style.display = 'block';
                tieneErrores = true;
            }
            
            if (!contrasena) {
                document.getElementById('errorContrasena').textContent = 'Requerido';
                document.getElementById('errorContrasena').style.display = 'block';
                tieneErrores = true;
            }
            
            if (contrasena !== contrasena_confirmacion) {
                document.getElementById('errorConfirmacion').textContent = 'No coinciden';
                document.getElementById('errorConfirmacion').style.display = 'block';
                tieneErrores = true;
            }
            
            if (contrasena && contrasena.length < 6) {
                document.getElementById('errorContrasena').textContent = 'Mínimo 6 caracteres';
                document.getElementById('errorContrasena').style.display = 'block';
                tieneErrores = true;
            }
            
            if (tieneErrores) return;
            
            try {
                const response = await fetch('/api/registro', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        nombre,
                        apellidos,
                        email,
                        telefono: telefono || null,
                        rol,
                        ciudad: ciudad || null,
                        direccion: direccion || null,
                        codigo_postal: codigo_postal || null,
                        contrasena
                    })
                });
                
                if (response.ok) {
                    document.getElementById('successMessage').style.display = 'block';
                    form.reset();
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else if (response.status === 400) {
                    const data = await response.json();
                    if (data.detail) {
                        const detail = String(data.detail).toLowerCase();
                        if (detail.includes('email')) {
                            document.getElementById('errorEmail').textContent = 'Email ya registrado';
                            document.getElementById('errorEmail').style.display = 'block';
                        } else if (detail.includes('contraseña')) {
                            document.getElementById('errorContrasena').textContent = data.detail;
                            document.getElementById('errorContrasena').style.display = 'block';
                        } else {
                            alert('Error: ' + (data.detail || 'No se pudo registrar'));
                        }
                    } else {
                        alert('Error: No se pudo registrar');
                    }
                } else {
                    alert('Error al registrar. Intenta nuevamente.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error de conexión. Intenta nuevamente.');
            }
        });
    </script>
</body>
</html>
    """).replace("{{", "{").replace("}}", "}")


@router.post("/api/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    usuario_data: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint de API para registrar un nuevo usuario.
    """
    
    # Verificar que el email no exista
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Asegurar que el rol es del tipo Enum
    if isinstance(usuario_data.rol, str):
        from app.schemas import RolUsuario as RolUsuarioSchema
        try:
            usuario_data.rol = RolUsuarioSchema(usuario_data.rol)
        except Exception:
            raise HTTPException(status_code=400, detail="Rol no válido")

    try:
        nuevo_usuario = crear_usuario(db, usuario_data)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )
    
    return {
        "id": nuevo_usuario.id,
        "nombre": nuevo_usuario.nombre,
        "apellidos": nuevo_usuario.apellidos,
        "email": nuevo_usuario.email,
        "rol": nuevo_usuario.rol.value,
        "mensaje": "Usuario registrado exitosamente"
    }


@router.post("/api/login", status_code=status.HTTP_200_OK)
def iniciar_sesion(datos: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Verifica credenciales y devuelve los datos básicos del usuario.
    """
    usuario = autenticar_usuario(db, datos.email, datos.contrasena)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está inactiva"
        )

    request.session["usuario"] = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "apellidos": usuario.apellidos,
        "email": usuario.email,
    }

    return {
        "mensaje": "Inicio de sesión correcto",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellidos": usuario.apellidos,
            "email": usuario.email,
        }
    }


@router.post("/api/logout", status_code=status.HTTP_200_OK)
def cerrar_sesion(request: Request):
    """
    Cierra la sesión del usuario actual.
    """
    request.session.clear()
    return {"mensaje": "Sesión cerrada"}


@router.get("/login", response_class=HTMLResponse)
def pagina_login(request: Request):
    """
    Página de login.
    """
    if request.session.get("usuario"):
        return RedirectResponse(url="/bienvenida", status_code=status.HTTP_303_SEE_OTHER)

    return ("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Iniciar sesión - Distans</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

""" + estilos_encabezado_html() + """

        body {{
            font-family: 'Arial', sans-serif;
            background: #f0f0f0;
            min-height: 100vh;
            padding-top: 74px;
        }}

        .login-wrap {{
            min-height: calc(100vh - 74px);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}

        .login-card {{
            width: 100%;
            max-width: 420px;
            background: #b3ff99;
            border-radius: 15px;
            padding: 38px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}

        .login-card h1 {{
            text-align: center;
            color: #000;
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 32px;
            margin-bottom: 28px;
        }}

        .field {{
            margin-bottom: 18px;
        }}

        label {{
            display: block;
            margin-bottom: 6px;
            color: #000;
            font-weight: 500;
            font-size: 13px;
        }}

        input {{
            width: 100%;
            padding: 10px 12px;
            border: none;
            border-radius: 5px;
            font-size: 13px;
            background: #ffffff;
            font-family: Arial, sans-serif;
        }}

        .button {{
            width: 100%;
            padding: 12px;
            background: #4caf50;
            color: #fff;
            border: 1px solid #3d8f42;
            border-radius: 5px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 8px;
        }}

        .note {{
            margin-top: 16px;
            text-align: center;
            color: #222;
            font-size: 14px;
        }}

        .note a {{
            color: #000;
            font-weight: 700;
            text-decoration: none;
        }}

        .error-message {{
            margin-top: 14px;
            color: #b00020;
            font-size: 14px;
            text-align: center;
            min-height: 18px;
        }}
    </style>
</head>
<body>
""" + encabezado_html("/login") + """
    <main class="login-wrap">
        <section class="login-card">
            <h1>Iniciar sesión</h1>
            <form id="loginForm">
                <div class="field">
                    <label for="email">Correo electrónico</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="field">
                    <label for="contrasena">Contraseña</label>
                    <input type="password" id="contrasena" name="contrasena" required>
                </div>
                <button type="submit" class="button">Entrar</button>
            </form>
            <p class="error-message" id="loginError"></p>
            <p class="note">¿No tienes cuenta? <a href="/registro">Regístrate</a></p>
        </section>
    </main>
    <script>
        const loginForm = document.getElementById('loginForm');
        const loginError = document.getElementById('loginError');

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            loginError.textContent = '';

            const email = document.getElementById('email').value.trim();
            const contrasena = document.getElementById('contrasena').value;

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email, contrasena }),
                });

                if (!response.ok) {
                    const data = await response.json();
                    loginError.textContent = data.detail || 'No se pudo iniciar sesión';
                    return;
                }

                await response.json();
                window.location.href = '/bienvenida';
            } catch (error) {
                console.error('Error de login:', error);
                loginError.textContent = 'Error de conexión. Inténtalo de nuevo.';
            }
        });
    </script>
</body>
</html>
    """).replace("{{", "{").replace("}}", "}")


@router.get("/bienvenida", response_class=HTMLResponse)
def pagina_bienvenida(request: Request):
    """
    Página mostrada después de un login correcto.
    """
    usuario = request.session.get("usuario")
    if not usuario:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    nombre = usuario.get("nombre", "Usuario")

    return ("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bienvenida - Distans</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

""" + estilos_encabezado_html() + """

        body {{
            font-family: 'Arial', sans-serif;
            background: #f0f0f0;
            min-height: 100vh;
            padding-top: 74px;
        }}

        .welcome-wrap {{
            min-height: calc(100vh - 74px);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}

        .welcome-card {{
            width: 100%;
            max-width: 540px;
            background: #b3ff99;
            border-radius: 15px;
            padding: 44px 32px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}

        .welcome-card h1 {{
            color: #000;
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 48px;
            line-height: 1.1;
        }}
    </style>
</head>
<body>
""" + encabezado_html_con_usuario("/bienvenida", nombre) + """
    <main class="welcome-wrap">
        <section class="welcome-card">
            <h1>¡Bienvenido!</h1>
        </section>
    </main>
    <script>
        async function cerrarSesion() {{
            try {{
                await fetch('/api/logout', {{ method: 'POST' }});
            }} catch (error) {{
                console.error('Error al cerrar sesión:', error);
            }}
            window.location.href = '/login';
        }}
    </script>
</body>
</html>
    """).replace("{{", "{").replace("}}", "}")
