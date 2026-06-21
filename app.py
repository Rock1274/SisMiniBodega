from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, jsonify, make_response
import psycopg2
import base64
from functools import wraps
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import secrets
from flask_cors import CORS
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

    
load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_1234'

# Configuración para desarrollo - deshabilitar cache
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

CORS(app)  # Permite todas las solicitudes; ajusta para producción

# Configuración para subida de archivos
UPLOAD_FOLDER = os.path.join('static', 'Paquetes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegurar que el directorio existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def archivo_permitido(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_filename(name):
    import re
    # Replace invalid characters with _
    invalid_chars = r'[<>:"|?*\x00-\x1f]'
    name = re.sub(invalid_chars, '_', name)
    # Also replace / and \ with _
    name = name.replace('/', '_').replace('\\', '_')
    return name

def limpiar_imagenes_huerfanas():
    """Elimina imágenes huérfanas que no corresponden a ningún producto activo"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT descripcion FROM Paquete')
        descripciones_activas = {row[0] for row in cursor.fetchall()}
        conn.close()

        archivos_esperados = {sanitize_filename(desc) + '.png' for desc in descripciones_activas}
        archivos_en_carpeta = set(os.listdir(app.config['UPLOAD_FOLDER']))

        for archivo in archivos_en_carpeta:
            if archivo.endswith('.png') and archivo != 'PorDefecto.webp' and archivo not in archivos_esperados:
                ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], archivo)
                try:
                    os.remove(ruta_archivo)
                    print(f"Imagen huérfana eliminada: {archivo}")
                except OSError as e:
                    print(f"Error al eliminar {archivo}: {e}")
    except Exception as e:
        print(f"Error en limpieza de imágenes huérfanas: {e}")

# Agregar filtro Jinja para sanitizar nombres de archivo
app.jinja_env.filters['sanitize'] = sanitize_filename

def is_ajax_request():
    """Detecta si la petición es AJAX desde nuestro sistema de navegación"""
    return request.headers.get('X-Custom-Ajax-Navigation') == 'true'

def render_template_ajax(template, **kwargs):
    if request.headers.get('X-Custom-Ajax-Navigation') == 'true':
        # Devolver JSON con content y modals para AJAX
        rendered = render_template(template, **kwargs)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = rendered
        modals = soup.find(attrs={'data-modals': True})

        response_data = {
            'content': content,
            'modals': modals.prettify() if modals else ''
        }
        # Incluir kwargs adicionales en la respuesta JSON
        response_data.update(kwargs)
        response = jsonify(response_data)
        # Agregar headers estrictos para evitar cache en respuestas AJAX
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Accel-Expires'] = '0'
        response.headers['Surrogate-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    response = make_response(render_template(template, **kwargs))
    # Agregar headers para evitar cache en respuestas HTML también
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Expires'] = '0'
    response.headers['Surrogate-Control'] = 'no-store'
    return response

def get_db_connection():
    try:
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            conn = psycopg2.connect(
                host=os.environ.get("DB_HOST"),
                database=os.environ.get("DB_NAME"),
                user=os.environ.get("DB_USER"), 
                password=os.environ.get("DB_PASSWORD"),
                port=os.environ.get("DB_PORT")
            )

        print("Conexión a PostgreSQL en Supabase exitosa.")
        return conn

    except Exception as e:
        print(f"Error de conexión: {e}")
        raise

def verificar_sesion_recordada():
    """Verifica si hay una cookie de sesión recordada y restaura la sesión"""
    if 'usuario' not in session:
        # Verificar cookie de sesión recordada
        cookie_usuario = request.cookies.get('recuerdame_usuario')
        cookie_tipo = request.cookies.get('recuerdame_tipo')
        cookie_user_id = request.cookies.get('recuerdame_user_id')

        if cookie_usuario and cookie_tipo and cookie_user_id:
            # Verificar que el usuario aún existe en la base de datos
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id_usuario, nusuario, tipo FROM Usuario WHERE nusuario = %s', (cookie_usuario,))
                user_verificado = cursor.fetchone()
                conn.close()

                if user_verificado:
                    # CORRECCIÓN: Usar los valores correctos de la BD en lugar de las cookies
                    session['usuario'] = user_verificado[1]  # NUsuario de BD
                    session['tipo'] = user_verificado[2]     # Tipo de BD
                    session['user_id'] = user_verificado[0]  # Id_Usuario de BD
                    print(f"Sesion restaurada automaticamente para usuario: {user_verificado[1]}")
                else:
                    # Usuario no válido, eliminar cookies
                    print("⚠️ Cookies inválidas detectadas, eliminando...")
                    # Las cookies se eliminarán automáticamente al expirar
            except Exception as e:
                print(f"Error al verificar usuario en cookies: {e}")

@app.before_request
def before_request():
    """Se ejecuta antes de cada petición para verificar sesión recordada"""
    # Solo verificar en rutas que no sean login, logout o archivos estáticos
    if request.endpoint and not request.endpoint.startswith(('login', 'logout', 'static')):
        verificar_sesion_recordada()

def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar sesión recordada antes de requerir login
        verificar_sesion_recordada()

        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def calcular_edad(fecha_nacimiento): 
    if not fecha_nacimiento:
        return ''
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = fecha_nacimiento.split(' ')[0]  # Por si viene con hora
        fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%Y-%m-%d')
    hoy = datetime.today()
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return edad

def manejar_imagen_producto(descripcion, imagen=None):
    """
    Maneja la imagen de un producto. Si se proporciona una imagen, la guarda.
    Si no hay imagen y no existe una para el producto, copia la imagen por defecto.
    """
    nombre_archivo = f"{sanitize_filename(descripcion)}.png"
    ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    
    if imagen and imagen.filename != '':
        # Validar formato de archivo
        if not archivo_permitido(imagen.filename):
            raise ValueError('Formato de imagen no permitido. Usa: .png, .jpg, .jpeg, .gif o .webp')

        # Guardar la imagen subida
        try:
            imagen.save(ruta_imagen)
        except Exception as e:
            raise ValueError(f'Error al guardar la imagen: {str(e)}')
    else:
        # Si no hay imagen subida y no existe una para el producto, copiar por defecto
        if not os.path.exists(ruta_imagen):
            ruta_por_defecto = os.path.join(app.config['UPLOAD_FOLDER'], 'PorDefecto.webp')
            if os.path.exists(ruta_por_defecto):
                import shutil
                shutil.copy2(ruta_por_defecto, ruta_imagen)
    
    return nombre_archivo

def validar_email(email):
    """Valida el formato de un email usando regex"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def enviar_email_gmail(destinatario, codigo):
    """Envía un email con el código de verificación usando Gmail"""
    remitente = 'soportedebodega.cocacola@gmail.com'  # Email de soporte
    password = 'haan gkbx pchr zlvs'  # Reemplazar con el App Password de soportedebodega.cocacola@gmail.com

    if remitente == 'tu_email@gmail.com':
        print("Error: Configura las credenciales de Gmail en la función enviar_email_gmail")
        return False

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = 'Código de Verificación para Recuperar Contraseña'

    cuerpo = f'''
    Hola,

    Has solicitado recuperar tu contraseña en el sistema de MiniBodega CocaCola.

    Tu código de verificación es: {codigo}

    Este código expira en 10 minutos. Si no solicitaste este cambio, ignora este email.

    Saludos,
    Equipo de Soporte CocaCola
    soporte.cocacola@gmail.com
    '''
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        text = msg.as_string()
        server.sendmail(remitente, destinatario, text)
        server.quit()
        print(f"Email enviado a {destinatario}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Error de autenticación: {e}. Verifica el email y App Password.")
        return False
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return False

#Login con funcionalidad de "Recuérdame"
# ====================================
# Esta función maneja el login y la creación de cookies persistentes
# cuando el usuario marca el checkbox "recuérdame".
#
# Funcionamiento:
# 1. Si el usuario marca "recuérdame", se crean cookies que duran 30 días
# 2. Las cookies contienen: usuario, tipo y user_id
# 3. Antes de cada petición, se verifica si hay cookies válidas
# 4. Si hay cookies válidas, se restaura la sesión automáticamente
# 5. Al hacer logout, se eliminan las cookies
#
# Seguridad:
# - Las cookies tienen httponly=True para prevenir acceso desde JavaScript
# - Se verifica que el usuario aún existe en la BD antes de restaurar sesión
# - Las cookies expiran automáticamente después de 30 días
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Verificar si ya hay una sesión recordada
    verificar_sesion_recordada()

    # Si ya hay sesión activa, redirigir al index
    if 'usuario' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nusuario = request.form['nusuario']
        contrasena = request.form['contrasena']
        recuerdame = request.form.get('recuerdame')  # Checkbox "recuérdame"
        contrasena_codificada = base64.b64encode(contrasena.encode('utf-16le')).decode()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Usuario WHERE nusuario = %s AND contraseña = %s', (nusuario, contrasena_codificada))
        print(f"Usuario: {nusuario}, Contraseña: {contrasena_codificada}")
        user = cursor.fetchone()
        conn.close()

        if user:
            # Crear sesión normal - CORREGIDOS LOS ÍNDICES SEGÚN ESTRUCTURA DE TABLA
            session['usuario'] = user[2]  # NUsuario (índice 2)
            session['tipo'] = user[5]     # Tipo (índice 5)
            session['user_id'] = user[0]  # Id_Usuario (índice 0)

            # Si se marcó "recuérdame", crear cookies persistentes
            if recuerdame:
                # Crear respuesta con cookies
                resp = make_response(redirect(url_for('index')))

                # Cookies que duran 30 días
                expires = datetime.now() + timedelta(days=30)

                # CORREGIDOS LOS ÍNDICES PARA LAS COOKIES
                resp.set_cookie('recuerdame_usuario', user[2], expires=expires, httponly=True, secure=False)  # NUsuario
                resp.set_cookie('recuerdame_tipo', user[5], expires=expires, httponly=True, secure=False)    # Tipo
                resp.set_cookie('recuerdame_user_id', str(user[0]), expires=expires, httponly=True, secure=False)  # Id_Usuario

                print(f"Cookies de 'recordame' creadas para usuario: {user[2]}")
                return resp
            else:
                # Sin cookies, solo sesión normal
                return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')
    return render_template('Login/login.html')

@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        email = request.form['email'].strip()
        flash(f'Email ingresado: {email}', 'info')
        if not validar_email(email):
            flash('Formato de email inválido.', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM Usuario WHERE email = %s', (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            flash('Email no registrado.', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        # Generar código de 6 dígitos
        codigo = ''.join(secrets.choice('0123456789') for _ in range(6))
        expiry = datetime.now() + timedelta(minutes=10)
        """ flash(f'Debug: Código generado: {codigo}', 'info') """

        # Guardar en BD (asumiendo tabla ResetTokens)
        try:
            cursor.execute('INSERT INTO ResetTokens (email, token, expiry) VALUES (%s, %s, %s )', (email, codigo, expiry))
            conn.commit()
        except Exception as e:
            conn.close()
            flash(f'Error al guardar en BD: {str(e)}', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        # Enviar email
        if enviar_email_gmail(email, codigo):
            session['reset_email'] = email

            cursor.execute('SELECT nombrecompleto FROM Usuario WHERE email = %s', (email,))
            usuario = cursor.fetchone()
            usuario_nombre = usuario[0] if usuario else 'Usuario'
            conn.close()
            flash(f'Código de verificación enviado a tu email, {usuario_nombre}', 'success')
            return redirect(url_for('verificar_codigo'))
        else:
            conn.close()
            flash('Error al enviar el email. Verifica credenciales de Gmail.', 'danger')

    return render_template('Login/recuperar_contrasena.html')

@app.route('/verificar_codigo', methods=['GET', 'POST'])
def verificar_codigo():
    if request.method == 'POST':
        codigo = request.form['codigo'].strip()
        email = session.get('reset_email')
        if not email:
            flash('Sesión expirada. Intenta de nuevo.', 'danger')
            return redirect(url_for('recuperar_contrasena'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT token, expiry FROM ResetTokens WHERE email = %s ORDER BY expiry DESC', (email,))
        token_data = cursor.fetchone()
        conn.close()

        if not token_data or token_data[0] != codigo or datetime.now() > token_data[1]:
            flash('Código inválido o expirado.', 'danger')
            return redirect(url_for('verificar_codigo'))

        session['reset_verified'] = True
        flash('Código verificado. Ingresa tu nueva contraseña.', 'success')
        return redirect(url_for('reset_contrasena'))

    # Para GET, verificar si hay email en sesión
    if not session.get('reset_email'):
        flash('Sesión expirada. Intenta de nuevo.', 'danger')
        return redirect(url_for('recuperar_contrasena'))

    return render_template('Login/verificar_codigo.html')

@app.route('/reset_contrasena', methods=['GET', 'POST'])
def reset_contrasena():
    if not session.get('reset_verified'):
        flash('Sesión expirada. Intenta de nuevo.', 'danger')
        return redirect(url_for('recuperar_contrasena'))

    if request.method == 'POST':
        nueva_contrasena = request.form['nueva_contrasena']
        confirmar_contrasena = request.form['confirmar_contrasena']

        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('reset_contrasena'))

        email = session.get('reset_email')
        contrasena_codificada = base64.b64encode(nueva_contrasena.encode('utf-16le')).decode()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Usuario SET contraseña = %s WHERE email = %s', (contrasena_codificada, email))
        conn.commit()
        conn.close()

        # Limpiar sesión
        session.pop('reset_email', None)
        session.pop('reset_verified', None)

        flash('Contraseña actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('Login/reset_contrasena.html')

# Ruta: Logout
@app.route('/logout')
def logout():
    session.clear()

    # Crear respuesta que elimina las cookies de "recuérdame"
    resp = make_response(redirect(url_for('login')))

    # Eliminar cookies configurándolas con fecha de expiración pasada
    resp.set_cookie('recuerdame_usuario', '', expires=0)
    resp.set_cookie('recuerdame_tipo', '', expires=0)
    resp.set_cookie('recuerdame_user_id', '', expires=0)

    print("Sesion cerrada y cookies de 'recordame' eliminadas")
    return resp
# Ruta: Página principal con bienvenida
@app.route('/')
@login_requerido
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. STOCK BAJO (Corregido a minúsculas limpias)
    cursor.execute('''
        SELECT descripcion, inventario
        FROM paquete
        WHERE inventario < 30 
        ORDER BY inventario ASC
    ''')
    alertas_stock = cursor.fetchall()

    # 2. TOTAL PRODUCTOS (Corregido a minúsculas limpias)
    cursor.execute("SELECT COUNT(*) FROM paquete")
    total_productos = cursor.fetchone()[0]

    # 3. VENTAS HOY (Corregido a minúsculas limpias)
    cursor.execute('''
        SELECT COALESCE(SUM(totalventa), 0)
        FROM venta
        WHERE fecha::date = CURRENT_DATE    
    ''')
    ventas_hoy = cursor.fetchone()[0]

    # 4. TOTAL COMPRAS
    cursor.execute("SELECT COUNT(*) FROM compras")
    total_compras = cursor.fetchone()[0]

    # 5. VENTAS POR DÍA (Corregido a minúsculas limpias)
    cursor.execute('''
        SELECT fecha::date as f, SUM(totalventa) as t
        FROM venta
        GROUP BY fecha::date
        ORDER BY f DESC
        LIMIT 7
    ''')
    ventas_chart = cursor.fetchall()

    labels = [str(v[0]) for v in ventas_chart][::-1]
    datos = [float(v[1]) for v in ventas_chart][::-1]

    # 6. ÚLTIMA COMPRA (Corregido a minúsculas limpias)
    cursor.execute("""
        SELECT c.id_compra, c.fechadecompra, p.nombreproveedor
        FROM compras c
        LEFT JOIN proveedor p ON c.id_proveedor = p.id_proveedor
        ORDER BY c.id_compra DESC
        LIMIT 1
    """)

    ultima = cursor.fetchone()
    ultima_compra = None

    if ultima:
        id_compra = ultima[0]
        fecha = ultima[1]
        proveedor = ultima[2] if ultima[2] else "Sin proveedor"
    
        cursor.execute("SELECT * FROM obtenertotalfactura(%s)", (id_compra,))
        resultado = cursor.fetchone()
    
        total = float(resultado[1]) if resultado and resultado[1] else 0.0
    
        ultima_compra = {
            "fecha": fecha,
            "proveedor": proveedor,
            "total": total
        }

    # 7. EMPLEADOS (Corregido a minúsculas limpias)
    cursor.execute("""
        SELECT pnombre || ' ' || COALESCE(snombre,'') || ' ' || papellido || ' ' || COALESCE(sapellido,'') AS nombrecompleto
        FROM empleado
        LIMIT 5
    """)
    empleados = cursor.fetchall()

    conn.close()

    if is_ajax_request():
        rendered = render_template(
            'bienvenida.html',
            alertas_stock=alertas_stock,
            total_productos=total_productos,
            ventas_hoy=ventas_hoy,
            total_compras=total_compras,
            labels=labels,
            datos=datos,
            ultima_compra=ultima_compra,
            empleados=empleados
        )

        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else ''
        })

    return render_template(
        'bienvenida.html',
        alertas_stock=alertas_stock,
        total_productos=total_productos,
        ventas_hoy=ventas_hoy,
        total_compras=total_compras,
        labels=labels,
        datos=datos,
        ultima_compra=ultima_compra,
        empleados=empleados
    )

# Paquetes
@app.route('/paquetes', methods=['GET', 'POST'])
@login_requerido
def ver_paquetes():
    busqueda = request.args.get('busqueda', '').strip()
    filtro = request.args.get('Filtros', 'Nombre')  # 'Nombre' por defecto
    page = request.args.get('page', 1, type=int)
    limit = 12
    offset = (page - 1) * limit
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener total de paquetes para paginación
    if busqueda:
        if filtro == 'Nombre':
            cursor.execute('SELECT COUNT(*) FROM Paquete WHERE descripcion LIKE %s', (f'%{busqueda}%',))
        elif filtro == 'Inventario':
            try:
                if busqueda.startswith('='):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE inventario = %s', (valor,))
                elif busqueda.startswith('>'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE inventario > %s', (valor,))
                elif busqueda.startswith('<'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE inventario < %s', (valor,))
                elif '-' in busqueda:
                    min_val, max_val = map(int, busqueda.split('-'))
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE inventario BETWEEN %s AND %s', (min_val, max_val))
                else:
                    valor = float(busqueda)
                    cursor.execute('SELECT COUNT(*) FROM Paquete WHERE inventario BETWEEN %s AND (%s + 5)', (valor, valor))
            except ValueError:
                total = 0
                paquetes = []
        elif filtro == 'TipoPaquete':
            cursor.execute('SELECT COUNT(*) FROM Paquete WHERE tipopaquete LIKE %s', (f'%{busqueda}%',))
        else:
            cursor.execute('SELECT COUNT(*) FROM Paquete')
    else:
        cursor.execute('SELECT COUNT(*) FROM Paquete')

    total_result = cursor.fetchone()
    total = total_result[0] if total_result else 0
    total_pages = (total + limit - 1) // limit

    # Buscar paquetes con paginación
    if busqueda:
        if filtro == 'Nombre':
            cursor.execute('''
                SELECT *
                FROM Paquete
                WHERE descripcion LIKE %s
                ORDER BY id_paquete DESC
                LIMIT %s OFFSET %s
            ''', (f'%{busqueda}%', limit, offset))
        elif filtro == 'Inventario':
            try:
                if busqueda.startswith('='):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT * FROM Paquete WHERE inventario = %s ORDER BY id_paquete DESC LIMIT %s OFFSET %s', (valor, limit, offset))
                elif busqueda.startswith('>'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT * FROM Paquete WHERE inventario > %s ORDER BY id_paquete DESC LIMIT %s OFFSET %s', (valor, limit, offset))
                elif busqueda.startswith('<'):
                    valor = float(busqueda[1:])
                    cursor.execute('SELECT * FROM Paquete WHERE inventario < %s ORDER BY id_paquete DESC LIMIT %s OFFSET %s', (valor, limit, offset))
                elif '-' in busqueda:
                    min_val, max_val = map(int, busqueda.split('-'))
                    cursor.execute('SELECT * FROM Paquete WHERE inventario BETWEEN %s AND %s ORDER BY id_paquete DESC LIMIT %s OFFSET %s', (min_val, max_val, limit, offset))
                else:
                    valor = float(busqueda)
                    cursor.execute('SELECT * FROM Paquete WHERE inventario BETWEEN %s AND (%s + 5) ORDER BY id_paquete DESC LIMIT %s OFFSET %s', (valor, valor, limit, offset))
            except ValueError:
                paquetes = []
        elif filtro == 'TipoPaquete':
            cursor.execute('''
                SELECT *
                FROM Paquete
                WHERE tipopaquete LIKE %s
                ORDER BY id_paquete DESC
                LIMIT %s OFFSET %s
            ''', (f'%{busqueda}%', limit, offset))
        else:
            cursor.execute('''
                SELECT *
                FROM Paquete
                ORDER BY id_paquete DESC
                LIMIT %s OFFSET %s
            ''', (limit, offset))
    else:
        cursor.execute('''
            SELECT *
            FROM Paquete
            ORDER BY id_paquete DESC
            LIMIT %s OFFSET %s
        ''', (limit, offset))

    paquetes = cursor.fetchall()
    print("PRIMER PAQUETE:")
    print(paquetes[0])
    print(type(paquetes[0]))

    # Crear paquete (si POST)
    if request.method == 'POST':
        descripcion = request.form['Descripcion']
        tipo = int(request.form['TipoPaquete'])
        inventario = 0
        unidadessobrantes = int(request.form['UnidadesSobrantes']) if request.form['UnidadesSobrantes'] else 0
        paquetescompletos = int(request.form['PaquetesCompletos']) if request.form['PaquetesCompletos'] else 0
        precio_venta = request.form['PrecioVenta_Paq']
        precio_compra = request.form['PrecioCompra_Paq']

        # Validar que las unidades sobrantes no excedan el tipo de paquete
        if unidadessobrantes > tipo:
            flash(f'❌ Las unidades sobrantes ({unidadessobrantes}) no pueden ser mayores que el tipo de paquete ({tipo})', 'danger')
            return redirect(url_for('ver_paquetes'))

        # Manejo de imagen
        imagen = request.files.get('imagen')
        try:
            nombre_archivo = manejar_imagen_producto(descripcion, imagen)
        except ValueError as e:
            flash(f'❌ {str(e)}', 'danger')
            return redirect(url_for('ver_paquetes'))

        # Inserción en la BD (NO incluye imagen, como pediste)
        cursor.execute('''
            INSERT INTO Paquete (descripcion, tipopaquete, inventario, unidadessobrantes, paquetescompletos, precioventa_paq, preciocompra_paq)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (descripcion, tipo, inventario, unidadessobrantes, paquetescompletos, precio_venta, precio_compra))

        conn.commit()
        conn.close()

        # Limpiar imágenes huérfanas después de crear el producto
        limpiar_imagenes_huerfanas()
        return redirect(url_for('ver_paquetes'))

    archivos_disponibles = set(os.listdir(app.config['UPLOAD_FOLDER']))
    conn.close()

    # Timestamp para evitar cache de imágenes
    timestamp = int(time.time())

    if is_ajax_request():
        rendered = render_template(
            'Productos/paquetes.html',
            paquetes=paquetes,
            busqueda=busqueda,
            lookup_files=archivos_disponibles,
            filtro=filtro,
            timestamp=timestamp,
            page=page,
            total_pages=total_pages
        )
        soup = BeautifulSoup(rendered, 'html.parser')
        content = rendered
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content,
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template(
            'Productos/paquetes.html',
            paquetes=paquetes,
            busqueda=busqueda,
            lookup_files=archivos_disponibles,
            filtro=filtro,
            timestamp=timestamp,
            page=page,
            total_pages=total_pages
        )

#Edicion de paquetes
@app.route('/editar_paquete/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_paquete(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        descripcion = request.form['Descripcion']
        tipo = int(request.form['TipoPaquete'])
        inventario = 0
        unidadessobrantes = int(request.form['UnidadesSobrantes']) if request.form['UnidadesSobrantes'] else 0
        paquetescompletos = int(request.form['PaquetesCompletos']) if request.form['PaquetesCompletos'] else 0
        precio_venta = request.form['PrecioVenta_Paq']
        precio_compra = request.form['PrecioCompra_Paq']
        imagen = request.files.get('imagen')

        if unidadessobrantes > tipo:
            flash(f'❌ Las unidades sobrantes ({unidadessobrantes}) no pueden ser mayores que el tipo de paquete ({tipo})', 'danger')

            # 🚀 Si es AJAX, devolvemos JSON (NO redirect)
            if request.headers.get('X-Custom-Ajax-Navigation') == 'true':
                return jsonify({"redirect": url_for('editar_paquete', id=id)})

            return redirect(url_for('editar_paquete', id=id))

        # Obtener descripción anterior para comparar
        cursor.execute('SELECT descripcion FROM Paquete WHERE id_paquete = %s', (id,))
        paquete_anterior = cursor.fetchone()
        descripcion_anterior = paquete_anterior[0] if paquete_anterior else None

        # Eliminar la imagen anterior si hay nueva imagen
        if imagen and imagen.filename != '':
            if descripcion_anterior:
                ruta_anterior = os.path.join(app.config['UPLOAD_FOLDER'], f"{sanitize_filename(descripcion_anterior)}.png")
                if os.path.exists(ruta_anterior):
                    try:
                        os.remove(ruta_anterior)
                    except Exception as e:
                        print(f"Error al eliminar imagen anterior: {e}")

        # Manejar renombrado de imagen si la descripción cambió
        if descripcion_anterior and descripcion_anterior != descripcion:
            nombre_archivo_anterior = f"{sanitize_filename(descripcion_anterior)}.png"
            ruta_anterior = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo_anterior)

            nombre_archivo_nuevo = f"{sanitize_filename(descripcion)}.png"
            ruta_nueva = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo_nuevo)

            # Si no hay nueva imagen, renombrar la existente
            if not (imagen and imagen.filename != ''):
                if os.path.exists(ruta_anterior) and not os.path.exists(ruta_nueva):
                    os.rename(ruta_anterior, ruta_nueva)

        try:
            nombre_archivo = manejar_imagen_producto(descripcion, imagen)
        except ValueError as e:
            flash(f'❌ {str(e)}', 'danger')

            if request.headers.get('X-Custom-Ajax-Navigation') == 'true':
                return jsonify({"redirect": url_for('editar_paquete', id=id)})

            return redirect(url_for('editar_paquete', id=id))

        cursor.execute('''
            UPDATE Paquete
            SET descripcion = %s, tipopaquete = %s, inventario = %s, unidadessobrantes = %s, paquetescompletos = %s, precioventa_paq = %s, preciocompra_paq = %s
            WHERE id_paquete = %s
        ''', (descripcion, tipo, inventario, unidadessobrantes, paquetescompletos, precio_venta, precio_compra, id))

        conn.commit()
        conn.close()

        # Limpiar imágenes huérfanas después de editar el producto
        limpiar_imagenes_huerfanas()

        # 🚀 Si es AJAX, regresamos JSON limpio → JS hace navigateTo()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"redirect": url_for('ver_paquetes')})

        return redirect(url_for('ver_paquetes'))


    # Obtener paquetes para el combo
    cursor.execute('SELECT * FROM Paquete WHERE id_paquete = %s', (id,))
    paquete = cursor.fetchone() 

    # Obtener lista de archivos disponibles
    archivos_disponibles = set(os.listdir(app.config['UPLOAD_FOLDER']))

    conn.close()

    # Timestamp para evitar cache de imágenes
    timestamp = int(time.time())

    if is_ajax_request():
        rendered = render_template('Productos/editar_paquetes.html', paquete=paquete, archivos_disponibles=archivos_disponibles, timestamp=timestamp)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template('Productos/editar_paquetes.html', paquete=paquete, archivos_disponibles=archivos_disponibles, timestamp=timestamp)



#Detalle Venta
@app.route('/detalles_ventas', methods=['GET', 'POST'])
@login_requerido
def ver_detalles_ventas():
    producto = request.args.get('producto', '').strip()
    id_venta = request.args.get('id_venta', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    error = None

    # Buscar detalles de ventas (por nombre de paquete si hay búsqueda)
    if producto:
        cursor.execute('''
            SELECT 
                dv.id_detalleventa,
                dv.id_venta,
                p.descripcion AS descripcionpaquete,
                dv.cantidadpaquetes,
                dv.cantidadunidades,
                dv.cantidadvendidatotal,
                dv.preciounitario,
                dv.subtotal
            FROM DetalleVenta dv
            JOIN Paquete p ON dv.id_paquete = p.id_paquete
            WHERE p.descripcion LIKE %s
            ORDER BY dv.id_venta ASC
        ''', (f'%{producto}%',))
    elif id_venta:
        cursor.execute('''
            SELECT 
                dv.id_detalleventa,
                dv.id_venta,
                p.descripcion AS descripcionpaquete,
                dv.cantidadpaquetes,
                dv.cantidadunidades,
                dv.cantidadvendidatotal,
                dv.preciounitario,
                dv.subtotal
            FROM DetalleVenta dv
            JOIN Paquete p ON dv.id_paquete = p.id_paquete
            WHERE dv.id_venta LIKE %s
            ORDER BY dv.id_venta ASC
        ''', (f'%{id_venta}%',))
    else:
        cursor.execute('''
            SELECT 
                dv.id_detalleventa,
                dv.id_venta,
                p.descripcion AS descripcionpaquete,
                dv.cantidadpaquetes,
                dv.cantidadunidades,
                dv.cantidadvendidatotal,
                dv.preciounitario,
                dv.subtotal
            FROM DetalleVenta dv
            JOIN Paquete p ON dv.id_paquete = p.id_paquete
            ORDER BY dv.id_venta ASC
        ''')
    detalles_ventas = cursor.fetchall()


    # Agregar Detalle Venta
    if request.method == 'POST':
        is_htmx = request.headers.get('HX-Request')
        print(f"HTMX Request: {is_htmx}")
        try:
            id_venta = int(request.form['dv_id_venta'])
            id_paquete = int(request.form['dv_paquete_id'])
            paquetes_finales = int(request.form['dv_paquetes_finales'])
            unidades_finales = int(request.form['dv_unidades_finales'])

            # Verificar que la venta existe
            cursor.execute('SELECT id_venta FROM Venta WHERE id_venta = %s', (id_venta,))
            venta = cursor.fetchone()
            if not venta:
                raise ValueError('Venta no encontrada')

            # Obtener inventario actual del paquete
            cursor.execute('SELECT inventario, tipopaquete, precioventa_paq, descripcion FROM Paquete WHERE id_paquete = %s', (id_paquete,))
            paquete = cursor.fetchone()
            if not paquete:
                raise ValueError('Paquete no encontrado')
            inventario_actual = paquete[0]
            tipo_paquete = paquete[1]
            precio_paquete = paquete[2]
            descripcion_paquete = paquete[3]


            cursor.execute('''
                INSERT INTO DetalleVenta (id_paquete, cantidadpaquetes, cantidadunidades, id_venta)
                VALUES (%s, %s, %s, %s)
            ''', (id_paquete, paquetes_finales, unidades_finales, id_venta))

            conn.commit()

            cursor.execute(
                '''
                SELECT
                    cantidadvendidatotal,
                    preciounitario,
                    subtotal,
                    cantidadpaquetes,
                    cantidadunidades,
                    id_detalleventa
                FROM DetalleVenta
                ORDER BY id_detalleventa DESC
                LIMIT 1;
            '''
            )
            detalle_insertado = cursor.fetchone()

            cantidad_vendida_total = detalle_insertado[0]
            precio_unitario = detalle_insertado[1]
            subtotal = detalle_insertado[2]
            cantidad_paquetes = detalle_insertado[3]
            cantidad_unidades = detalle_insertado[4]
            id = detalle_insertado[5]


            # Recargar toda la tabla con los datos actualizados de la BD
            if is_htmx:
                # Obtener todos los detalles de ventas actualizados
                cursor.execute('''
                    SELECT
                        dv.id_detalleventa,
                        dv.id_venta,
                        p.descripcion AS descripcionpaquete,
                        dv.cantidadpaquetes,
                        dv.cantidadunidades,
                        dv.cantidadvendidatotal,
                        dv.preciounitario,
                        dv.subtotal
                    FROM DetalleVenta dv
                    JOIN Paquete p ON dv.id_paquete = p.id_paquete
                    ORDER BY dv.id_venta ASC
                ''')
                detalles_actualizados = cursor.fetchall()

                # Generar HTML completo del tbody
                tbody_html = ''
                for detalle in detalles_actualizados:
                    tbody_html += f'''
                    <tr>
                        <td class="text-center">{detalle[1]}</td>
                        <td>{detalle[2]}</td>
                        <td class="text-center">{detalle[3]}</td>
                        <td class="text-center">{detalle[4]}</td>
                        <td class="text-center">{detalle[5]:.2f}</td>
                        <td class="text-end">C${detalle[6]:.2f}</td>
                        <td class="text-end">C${detalle[7]:.2f}</td>
                        <td class="text-center">
                            <a href="/editar_detalle_venta/{detalle[0]}" class="btn btn-sm btn-warning">Editar</a>
                        </td>
                    </tr>
                    '''
                return tbody_html
            else:
                flash('Detalle de venta registrado correctamente.', 'success')
                conn.close()
                return redirect(url_for('ver_detalles_ventas'))

        except ValueError as e:
            error = str(e)
            if is_htmx:
                return f'<div class="alert alert-danger">{error}</div>'
        except psycopg2.Error as e:
            error = f'Error de base de datos: {str(e)}'
            if is_htmx:
                return f'<div class="alert alert-danger">{error}</div>'


    # Cargar combos: Paquetes y ventas
    cursor.execute('SELECT id_paquete, descripcion, paquetescompletos, unidadessobrantes, inventario, tipopaquete FROM Paquete')
    paquetes = cursor.fetchall()

    cursor.execute('SELECT MAX(id_venta) FROM Venta')
    max_id_venta_result = cursor.fetchone()
    max_id_venta = max_id_venta_result[0] if max_id_venta_result and max_id_venta_result[0] is not None else 1

    cursor.execute('SELECT id_venta, fecha, totalventa FROM Venta ORDER BY fecha ASC')
    ventas = cursor.fetchall()

    tiene_detalles = len(detalles_ventas) > 0
    conn.close()

    if is_ajax_request():
        rendered = render_template(
            'Ventas/detalles_ventas.html',
            detalles_ventas=detalles_ventas,
            producto=producto,
            id_venta=id_venta,
            paquetes=paquetes,
            ventas=ventas,
            max_id_venta=max_id_venta,
            error=error,
            tiene_detalles=tiene_detalles
        )
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else ''
        })
    else:
        return render_template(
            'Ventas/detalles_ventas.html',
            detalles_ventas=detalles_ventas,
            producto=producto,
            id_venta=id_venta,
            paquetes=paquetes,
            ventas=ventas,
            max_id_venta=max_id_venta,
            error=error,
            tiene_detalles=tiene_detalles
        )



@app.route('/crear_venta', methods=['POST'])
@login_requerido
def crear_venta():
    is_htmx = request.headers.get('HX-Request')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('INSERT INTO Venta DEFAULT VALUES RETURNING id_venta, fecha, totalventa;')
        venta = cursor.fetchone()
        nueva_venta_id = int(venta[0]) if venta and venta[0] is not None else 1

        conn.commit()

        if is_htmx:
            # Devolver HTML de la nueva fila para la tabla en ver_ventas.html
            fecha = venta[1].strftime('%Y-%m-%d') if venta[1] else 'N/A'
            total_venta = f"C${venta[2]:.2f}" if venta[2] else 'C$0.00'
            nueva_fila_html = f'''
            <tr class="text-center">
                <td>{venta[0]}</td>
                <td>{fecha}</td>
                <td>{total_venta}</td>
            </tr>
            '''
            return nueva_fila_html
        else:
            flash(f'Venta creada exitosamente. ID: {nueva_venta_id}', 'success')
            return redirect(url_for('ver_detalles_ventas'))

    except Exception as e:
        conn.rollback()
        if is_htmx:
            return f'<div class="alert alert-danger">Error al crear la venta: {str(e)}</div>'
        else:
            flash(f'Ocurrió un error al crear la venta: {str(e)}', 'danger')
            return redirect(url_for('ver_detalles_ventas'))

    finally:
        cursor.close()
        conn.close()



@app.route('/editar_detalle_venta/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_detalle_venta(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT
                    dv.id_detalleventa,
                    dv.id_paquete,
                    dv.id_venta,
                    p.tipopaquete AS tipopaquete,
                    p.paquetescompletos AS paquetescompletos,
                    p.unidadessobrantes AS unidadessobrantes,
                    p.inventario AS inventario,
                    p.descripcion AS descripcion,
                    dv.cantidadpaquetes,
                    dv.cantidadunidades
                    FROM DetalleVenta dv
                    inner join Paquete p on dv.id_paquete = p.id_paquete
                    WHERE id_detalleventa = %s''', (id,))
    detalle = cursor.fetchone()

    # Convertir detalle a dict para serialización JSON
    if detalle:
        detalle = dict(zip([col[0] for col in cursor.description], detalle))

    # Obtener paquetes para el combo
    cursor.execute('SELECT id_paquete, descripcion, paquetescompletos, unidadessobrantes, inventario FROM Paquete')
    paquetes = cursor.fetchall()

    # Convertir paquetes a lista de dicts para serialización JSON
    paquetes = [dict(zip([col[0] for col in cursor.description], row)) for row in paquetes]

    cursor.execute('SELECT MAX(id_venta) FROM Venta')
    max_id_venta_result = cursor.fetchone()
    max_id_venta = max_id_venta_result[0] if max_id_venta_result and max_id_venta_result[0] is not None else 1


    if not detalle:
        cursor.close()
        conn.close()
        flash('Detalle de venta no encontrado.', 'danger')
        return redirect(url_for('ver_detalles_ventas'))

    if request.method == 'POST':
        try:
            id_venta = int(request.form['id_venta'])
            id_paquete = int(request.form['paquete_id'])
            cantidad_paquetes = int(request.form['cantidad_paquetes'])
            cantidad_unidades = int(request.form['cantidad_unidades'])

            # Verificar que la venta existe
            cursor.execute('SELECT id_venta FROM Venta WHERE id_venta = %s', (id_venta,))
            venta = cursor.fetchone()
            if not venta:
                raise ValueError('Venta no encontrada')

            # Si quieres actualizar precio unitario y subtotal, también agregar aquí y en el form

            # Actualizamos solo los campos que sí están en DetalleVenta
            cursor.execute('''
                UPDATE DetalleVenta
                SET id_venta = %s, id_paquete = %s, cantidadpaquetes = %s, cantidadunidades = %s
                WHERE id_detalleventa = %s
            ''', (id_venta, id_paquete, cantidad_paquetes, cantidad_unidades, id))

            conn.commit()
            flash('Detalle de venta actualizado correctamente.', 'success')
            return redirect(url_for('ver_detalles_ventas'))

        except Exception as e:
            flash(f'Error al actualizar el detalle: {str(e)}', 'danger')


    cursor.close()
    conn.close()

    return render_template_ajax(
        'Ventas/editar_detalle_venta.html',
        detalle=detalle,
        paquetes=paquetes,
        max_id_venta=max_id_venta)

""" @app.route('/eliminar_detalle_venta/<int:id>', methods=['POST'])
@login_requerido
def eliminar_detalle_venta(id):
    print(id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM DetallesDeVentas WHERE Id_DetallesDeVentas = %s', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_detalles_ventas'))

 """

#Compras
@app.route("/compras")
@login_requerido
def ver_compras():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Traer compras con proveedor y fecha
    cursor.execute("""
        SELECT C.Id_Compra, C.FechaDeCompra, P.NombreProveedor
        FROM Compras C
        LEFT JOIN Proveedor P ON C.Id_Proveedor = P.Id_Proveedor
        ORDER BY C.Id_Compra DESC
    """)
    compras = cursor.fetchall()

    lista_compras = []
    for compra in compras:
        id_compra = compra[0]
        fecha = compra[1]
        proveedor = compra[2] if compra[2] else "Sin proveedor"

        # Ejecutar el procedimiento almacenado para calcular el total
        cursor.execute("SELECT * FROM obtenertotalfactura(%s)", (id_compra,))
        resultado = cursor.fetchone()

        if resultado and resultado[1] is not None:
            total = float(resultado[1])  # Convertir Decimal a float
        else:
            total = 0.0

        lista_compras.append((id_compra, fecha, proveedor, total))

    cursor.close()
    conn.close()

    return render_template_ajax("Compras/compras.html", compras=lista_compras)


# -----------------------
# 2. Mostrar formulario de nueva compra
# -----------------------
@app.route('/crear_compra', methods=['GET'])
@login_requerido
def crear_compra():
    return render_template('Compras/crear_compra.html')


# -----------------------
# 2.1 Confirmar y crear compra en BD
# -----------------------
@app.route('/crear_compra/confirmar', methods=['POST'])
@login_requerido
def confirmar_crear_compra():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Compras (Id_Proveedor) VALUES (1) RETURNING Id_Compra")
    nueva_compra_id = cursor.fetchone()[0]
    conn.commit()

    cursor.close()
    conn.close()

    flash('Compra iniciada, agregue productos al carrito')
    return redirect(url_for('carrito', id_compra=nueva_compra_id))

# -----------------------
# 3. Ver carrito / agregar productos
# -----------------------
@app.route('/carrito/<int:id_compra>', methods=['GET'])
@login_requerido
def carrito(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la compra
    cursor.execute("SELECT Id_Compra, FechaDeCompra, Id_Proveedor FROM Compras WHERE Id_Compra = %s", (id_compra,))
    compra = cursor.fetchone()
    if not compra:
        flash('Compra no encontrada')
        cursor.close()
        conn.close()
        return redirect(url_for('ver_compras'))

    # Buscar productos
    buscar = request.args.get('buscar', '').strip()
    if buscar:
        cursor.execute("""
            SELECT Id_Paquete, Descripcion, PrecioCompra_Paq
            FROM Paquete WHERE Descripcion LIKE %s
        """, (f"%{buscar}%",))
    else:
        cursor.execute("""
            SELECT Id_Paquete, Descripcion, PrecioCompra_Paq
            FROM Paquete
        """)
    paquetes = cursor.fetchall()

    # Obtener detalles del carrito
    cursor.execute('''
        SELECT
            dc.id_detalledecompra AS "Id_DetalleDeCompra",
            p.descripcion AS "Producto",
            dc.cantidad AS "Cantidad",
            dc.cantidad * p.preciocompra_paq AS "TotalConIVA"
        FROM DetallesDeCompras dc
        JOIN Paquete p ON dc.id_paquete = p.id_paquete
        WHERE dc.id_compra = %s
    ''', (id_compra,))
    columnas_carrito = [col[0] for col in cursor.description]
    carrito = [dict(zip(columnas_carrito, fila)) for fila in cursor.fetchall()]

    cursor.close()
    conn.close()

    if request.args.get('partial') == '1':
        carrito_html = render_template_string('''
<table class="table table-bordered" id="carrito_tabla">
    <thead class="table-dark">
        <tr>
            <th>Producto</th>
            <th>Cantidad</th>
            <th>Total c/ IVA</th>
            <th>Acción</th>
        </tr>
    </thead>
    <tbody>
        {% for d in carrito %}
        <tr>
            <td>{{ d.Producto }}</td>
            <td>{{ d.Cantidad }}</td>
            <td>{{ "%.2f"|format(d.TotalConIVA) }}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="eliminarProducto('{{ d.Id_DetalleDeCompra }}')">Eliminar</button>
            </td>
        </tr>
        {% else %}
        <tr>
            <td colspan="4" class="text-center">No hay productos en el carrito</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
        ''', carrito=carrito)
        return carrito_html
    else:
        return render_template('Compras/carrito.html', compra=compra, paquetes=paquetes, carrito=carrito, buscar=buscar)

# -----------------------
# 4. Agregar producto al carrito
# -----------------------
@app.route('/carrito/<int:id_compra>/agregar', methods=['POST'])
@login_requerido
def agregar_al_carrito(id_compra):
    id_paquete = request.form.get('id_paquete')
    cantidad = int(request.form.get('cantidad', 1))

    if cantidad < 1:
        flash('La cantidad debe ser al menos 1')
        return redirect(url_for('carrito', id_compra=id_compra))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar que existe
    cursor.execute("SELECT PrecioCompra_Paq FROM Paquete WHERE Id_Paquete = %s", (id_paquete,))
    paquete = cursor.fetchone()
    if not paquete:
        flash('Producto no encontrado')
        cursor.close()
        conn.close()
        return redirect(url_for('carrito', id_compra=id_compra))

    # Revisar si ya existe en carrito
    cursor.execute("""
        SELECT Id_DetalleDeCompra, Cantidad 
        FROM DetallesDeCompras 
        WHERE Id_Compra = %s AND Id_Paquete = %s
    """, (id_compra, id_paquete))
    detalle = cursor.fetchone()
    if detalle:
        nueva_cantidad = detalle[1] + cantidad
        cursor.execute("UPDATE DetallesDeCompras SET Cantidad = %s WHERE Id_DetalleDeCompra = %s", (nueva_cantidad, detalle[0]))
    else:
        cursor.execute("""
            INSERT INTO DetallesDeCompras (Id_Compra, Id_Paquete, Cantidad)
            VALUES (%s, %s, %s)
        """, (id_compra, id_paquete, cantidad))

    conn.commit()
    cursor.close()
    conn.close()

    if is_ajax_request():
        return jsonify({'success': True})
    else:
        flash('Producto agregado al carrito')
        return redirect(url_for('carrito', id_compra=id_compra))

# -----------------------
# 5. Eliminar producto del carrito
# -----------------------
@app.route('/carrito/<int:id_compra>/eliminar/<int:id_detalle>', methods=['DELETE'])
@login_requerido
def eliminar_detalle(id_compra, id_detalle):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DetallesDeCompras WHERE Id_DetalleDeCompra = %s", (id_detalle,))
    conn.commit()
    cursor.close()
    conn.close()

    if is_ajax_request():
        return jsonify({'success': True})
    else:
        flash('Producto eliminado del carrito')
        return redirect(url_for('carrito', id_compra=id_compra))
# -----------------------
# 6. Finalizar compra (MODIFICADA: SP actualiza PaquetesCompletos, trigger recalcula Inventario)
# -----------------------
@app.route('/carrito/<int:id_compra>/finalizar', methods=['GET'])
@login_requerido
def finalizar_compra(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Ejecutar el procedimiento para obtener el total
        cursor.execute("SELECT * FROM obtenertotalfactura(%s)", (id_compra,))
        resultado = cursor.fetchone()

        if resultado is None or resultado[1] is None:
            flash('No se puede finalizar una compra sin productos')
            return redirect(url_for('carrito', id_compra=id_compra))

        total = float(resultado[1])  # resultado[1] es el total

        # Verificar que hay productos
        cursor.execute("SELECT COUNT(*) FROM DetallesDeCompras WHERE Id_Compra = %s", (id_compra,))
        count_detalles = cursor.fetchone()[0]
        if count_detalles == 0:
            flash('No hay productos en el carrito')
            return redirect(url_for('carrito', id_compra=id_compra))

        # Depuración: Ver PaquetesCompletos e Inventario antes
        cursor.execute("SELECT p.Id_Paquete, p.Descripcion, p.PaquetesCompletos, p.Inventario FROM Paquete p INNER JOIN DetallesDeCompras dc ON p.Id_Paquete = dc.Id_Paquete WHERE dc.Id_Compra = %s", (id_compra,))
        estado_antes = cursor.fetchall()
        print(f"Estado ANTES de finalizar compra {id_compra}: {estado_antes}")

        # Llamar al SP para actualizar PaquetesCompletos (trigger recalculará Inventario)
        cursor.execute("SELECT finalizarcomprasumarinventario(%s)", (id_compra,))
        print(f"SP ejecutado para compra {id_compra} (actualizó PaquetesCompletos)")

        # Depuración: Ver PaquetesCompletos e Inventario después
        cursor.execute("SELECT p.Id_Paquete, p.Descripcion, p.PaquetesCompletos, p.Inventario FROM Paquete p INNER JOIN DetallesDeCompras dc ON p.Id_Paquete = dc.Id_Paquete WHERE dc.Id_Compra = %s", (id_compra,))
        estado_despues = cursor.fetchall()
        print(f"Estado DESPUÉS de finalizar compra {id_compra}: {estado_despues}")

        # Comparar para confirmar cambios
        cambios = []
        for antes, despues in zip(estado_antes, estado_despues):
            if antes[2] != despues[2] or antes[3] != despues[3]:  # PaquetesCompletos o Inventario cambió
                cambios.append(f"Paquete {despues[0]} ({despues[1]}): PaquetesCompletos {antes[2]} -> {despues[2]}, Inventario {antes[3]} -> {despues[3]}")
        if cambios:
            print(f"Cambios detectados: {cambios}")
        else:
            print("No se detectaron cambios")

        conn.commit()  # Confirmar cambios

        flash(f'Compra finalizada correctamente. Total: C${total:.2f}')
        return redirect(url_for('ver_compras'))

    except Exception as e:
        print(f"Error en finalizar_compra: {e}")
        conn.rollback()
        flash('Error al finalizar la compra')
        return redirect(url_for('carrito', id_compra=id_compra))
    finally:
        cursor.close()
        conn.close()
        
# -----------------------
# 7. Cancelar compra
# -----------------------
@app.route('/carrito/<int:id_compra>/cancelar', methods=['GET'])
@login_requerido
def cancelar_compra(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si tiene detalles
    cursor.execute("SELECT COUNT(*) FROM DetallesDeCompras WHERE Id_Compra = %s", (id_compra,))
    tiene_detalles = cursor.fetchone()[0]

    if tiene_detalles > 0:
        flash('No se puede cancelar, la compra ya tiene productos')
    else:
        cursor.execute("DELETE FROM Compras WHERE Id_Compra = %s", (id_compra,))
        conn.commit()
        flash('Compra cancelada correctamente')

    cursor.close()
    conn.close()
    return redirect(url_for('ver_compras'))

# -----------------------
# 7.1 Cancelar compra automáticamente si el usuario se va sin finalizar
# -----------------------
@app.route('/carrito/<int:id_compra>/cancelar_exit', methods=['POST'])
def cancelar_compra_exit(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si la compra tiene productos
    cursor.execute("SELECT COUNT(*) FROM DetallesDeCompras WHERE Id_Compra = %s", (id_compra,))
    tiene_detalles = cursor.fetchone()[0]

    # Solo borrar si está vacía
    if tiene_detalles == 0:
        cursor.execute("DELETE FROM Compras WHERE Id_Compra = %s", (id_compra,))
        conn.commit()

    cursor.close()
    conn.close()
    return ('', 204)  # Sin contenido (no rompe la navegación)


# -----------------------
    # 8. Ver detalles de una compra
# -----------------------
@app.route('/detalles_compras/<int:id_compra>', methods=['GET'])
@login_requerido
def detalles_compras(id_compra):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Traer la compra
    cursor.execute("""
        SELECT Id_Compra, FechaDeCompra, Id_Proveedor
        FROM Compras 
        WHERE Id_Compra = %s
    """, (id_compra,))
    compra = cursor.fetchone()

    if not compra:
        flash('Compra no encontrada', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('ver_compras'))

    # Traer detalles de la compra
    cursor.execute('''
        SELECT 
            p.descripcion AS producto, 
            round(dc.cantidad,0) AS cantidad, 
            round(dc.precioantdes,2) AS precioantdes, 
            round(dc.totalantdes,2) AS totalantdes, 
            round(dc.descuentototal,2) AS descuentototal, 
            round(dc.totalcondes,2) AS totalcondes, 
            round(dc.totalconiva,2) AS totalconiva
        FROM DetallesDeCompras dc
        JOIN Paquete p ON dc.id_paquete = p.id_paquete
        WHERE dc.id_compra = %s
    ''', (id_compra,))
    detalles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('Compras/detalles_compra.html', compra=compra, detalles=detalles)


# Nomina
@app.route('/ver_nomina', methods=['GET', 'POST'])
@login_requerido
def ver_nomina():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todos los empleados activos para el select
    cursor.execute('''
        SELECT 
            id_empleado,
            pnombre, snombre, papellido, sapellido,
            estado
        FROM Empleado WHERE estado = 'Activo'
        ORDER BY pnombre, papellido
    ''')
    
    columnas = [col[0] for col in cursor.description]
    empleados_raw = cursor.fetchall()
    empleados = []
    
    for emp_raw in empleados_raw:
        emp = dict(zip(columnas, emp_raw))
        # Combinar nombres y apellidos
        nombres = f"{emp.get('PNombre', '')} {emp.get('SNombre', '')}".strip()
        apellidos = f"{emp.get('PApellido', '')} {emp.get('SApellido', '')}".strip()
        emp['Nombres'] = nombres
        emp['Apellidos'] = apellidos
        empleados.append(emp)

    conn.close()
    return render_template_ajax('Empleados/ver_nomina.html', empleados=empleados)





@app.route('/crear_nota/<int:id>', methods=['GET', 'POST'])
@login_requerido
def crear_nota(id):
    if request.method == 'POST':
        asunto = request.form['asunto'].strip()
        fecha = request.form['fecha']
        
        if not asunto:
            flash('El asunto es obligatorio.', 'danger')
            return redirect(url_for('crear_nota'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO Notas (asunto, fechadelasunto, id_empleado)
                VALUES (%s, %s, %s)
            ''', (asunto, fecha, id))
            
            conn.commit()
            conn.close()
            flash('Nota creada exitosamente.', 'success')
            return redirect(url_for('crear_nota', id=id))
            
        except Exception as e:
            conn.close()
            flash('Error al crear la nota.', 'danger')
            return redirect(url_for('crear_nota', id=id))
    
    # GET - Mostrar página con notas existentes
    conn = get_db_connection()
    cursor = conn.cursor()
    

    
    # Obtener todas las notas del empleado actual
    cursor.execute('''
        SELECT n.id_nota, n.asunto, n.fechadelasunto, n.id_empleado,
               e.pnombre, e.snombre, e.papellido, e.sapellido, n.estado
        FROM Notas n
        LEFT JOIN Empleado e ON n.id_empleado = e.id_empleado
        WHERE n.id_empleado = %s
        ORDER BY n.fechadelasunto DESC, n.id_nota DESC
    ''', (id,))
    
    columnas = [col[0] for col in cursor.description]
    notas_raw = cursor.fetchall()
    notas = []
    
    for nota_raw in notas_raw:
        nota = dict(zip(columnas, nota_raw))
        # Combinar nombre del empleado
        nombres = f"{nota.get('PNombre', '')} {nota.get('SNombre', '')}".strip()
        apellidos = f"{nota.get('PApellido', '')} {nota.get('SApellido', '')}".strip()
        nota['nombre_empleado'] = f"{nombres} {apellidos}".strip()
        notas.append(nota)
    
    conn.close()
    
    # Fecha actual para el formulario
    from datetime import date
    fecha_actual = date.today().strftime('%Y-%m-%d')
    
    return render_template_ajax('Empleados/crear_nota.html', notas=notas, fecha_actual=fecha_actual, empleado_id=id)

@app.route('/marcar_nota', methods=['POST'])
@login_requerido
def marcar_nota():
    data = request.get_json()
    nota_id = data.get('nota_id')
    completada = data.get('completada', False)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que la nota existe
        cursor.execute('SELECT id_empleado FROM Notas WHERE id_nota = %s', (nota_id,))
        nota = cursor.fetchone()
        
        if not nota:
            conn.close()
            return jsonify({'success': False, 'message': 'Nota no encontrada'})
        
        # Actualizar el estado en la columna Estado
        nuevo_estado = 'Completada' if completada else 'Pendiente'
        cursor.execute('UPDATE Notas SET estado = %s WHERE id_nota = %s', (nuevo_estado, nota_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/eliminar_nota', methods=['POST'])
@login_requerido
def eliminar_nota():
    data = request.get_json()
    nota_id = data.get('nota_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que la nota existe
        cursor.execute('SELECT id_empleado FROM Notas WHERE id_nota = %s', (nota_id,))
        nota = cursor.fetchone()
        
        if not nota:
            conn.close()
            return jsonify({'success': False, 'message': 'Nota no encontrada'})
        
        # Eliminar la nota
        cursor.execute('DELETE FROM Notas WHERE id_nota = %s', (nota_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/crear_empleado', methods=['GET', 'POST'])
@login_requerido
def crear_empleado():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        primer_nombre = request.form['primer_nombre']
        segundo_nombre = request.form.get('segundo_nombre', '')
        primer_apellido = request.form['primer_apellido']
        segundo_apellido = request.form.get('segundo_apellido', '')
        
        # Combinar nombres y apellidos
        nombres = f"{primer_nombre} {segundo_nombre}".strip()
        apellidos = f"{primer_apellido} {segundo_apellido}".strip()
        
        cedula = request.form['cedula']
        estado = request.form['estado']
        estado_civil = request.form['estado_civil']
        sexo = request.form['sexo']
        fecha_nacimiento = request.form['fecha_nacimiento']
        fecha_inicontrato = request.form['fecha_Inicontrato']
        fecha_fincontrato = request.form['fecha_Fincontrato']
        direccion = request.form['direccion']
        num_inss = request.form['num']
        num_ruc = request.form['num2']
        salarioBase = request.form['salarioBase'] or 0
        supervisor = request.form['supervisor'] or None

        cursor.execute('''
            INSERT INTO Empleado (pnombre, snombre, papellido, sapellido, numcedula, estadocivil, sexo, 
                                 fechadenacimiento, fechadeiniciocontrato, fechadefincontrato, direccion, 
                                 numinss, ruc, salariobase, supervisor, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, cedula, estado_civil, sexo,
              fecha_nacimiento, fecha_inicontrato, fecha_fincontrato, direccion, num_inss, num_ruc, salarioBase, supervisor, estado))
        conn.commit()
        conn.close()
        
        flash('Empleado creado exitosamente.', 'success')
        return redirect(url_for('ver_empleados'))

    # Obtener supervisores para el combo
    cursor.execute('SELECT id_empleado, pnombre, snombre, papellido, sapellido FROM Empleado')
    supervisores_raw = cursor.fetchall()
    
    # Procesar supervisores
    supervisores = []
    for sup in supervisores_raw:
        supervisor_dict = {
            'Id_Empleado': sup[0],
            'PNombre': sup[1],
            'SNombre': sup[2],
            'PApellido': sup[3],
            'SApellido': sup[4],
            'Nombres': f"{sup[1]} {sup[2]}".strip(),
            'Apellidos': f"{sup[3]} {sup[4]}".strip()
        }
        supervisores.append(supervisor_dict)

    conn.close()
    return render_template_ajax('Empleados/crear_empleado.html', supervisores=supervisores)


@app.route('/empleados', methods=['GET'])
@login_requerido
def ver_empleados():
    busqueda = request.args.get('busqueda', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar empleados
    if busqueda:
        cursor.execute('''
            SELECT 
                e.id_empleado,
                e.pnombre,
                e.snombre,
                e.papellido,
                e.sapellido,
                e.fechadenacimiento,
                e.fechadeiniciocontrato,
                e.fechadefincontrato AS fechadefincontrato,
                e.direccion,
                e.estado,
                s.pnombre AS supervisorpnombre,
                s.snombre AS supervisorsnombre,
                s.papellido AS supervisorpapellido,
                s.sapellido AS supervisorsapellido,
                e.numcedula,
                e.estadocivil,
                e.sexo,
                e.numinss,
                e.ruc,
                e.salariobase
            FROM Empleado e
            LEFT JOIN Empleado s ON e.supervisor = s.id_empleado
            WHERE (e.pnombre LIKE %s OR e.snombre LIKE %s OR e.papellido LIKE %s OR e.sapellido LIKE %s OR e.direccion LIKE %s)
            ORDER BY e.id_empleado ASC
        ''', (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
    else:
        cursor.execute('''
            SELECT 
                e.id_empleado,
                e.pnombre,
                e.snombre,
                e.papellido,
                e.sapellido,
                e.fechadenacimiento,
                e.fechadeiniciocontrato,
                e.fechadefincontrato AS fechadefincontrato,
                e.direccion,
                e.estado,
                s.pnombre AS supervisorpnombre,
                s.snombre AS supervisorsnombre,
                s.papellido AS supervisorpapellido,
                s.sapellido AS supervisorsapellido,
                e.numcedula,
                e.estadocivil,
                e.sexo,
                e.numinss,
                e.ruc,
                e.salariobase
            FROM Empleado e
            LEFT JOIN Empleado s ON e.supervisor = s.id_empleado
            ORDER BY e.id_empleado ASC
        ''')

    columnas_raw = [col[0] for col in cursor.description]
    empleados_raw = [dict(zip(columnas_raw, fila)) for fila in cursor.fetchall()]
    empleados = []
    for emp_raw in empleados_raw:
        emp = {
            'Id_Empleado': emp_raw.get('id_empleado'),
            'PNombre': emp_raw.get('pnombre'),
            'SNombre': emp_raw.get('snombre'),
            'PApellido': emp_raw.get('papellido'),
            'SApellido': emp_raw.get('sapellido'),
            'FechaDeNacimiento': emp_raw.get('fechadenacimiento'),
            'FechaDeInicioContrato': emp_raw.get('fechadeiniciocontrato'),
            'FechaDeFinContrato': emp_raw.get('fechadefincontrato'),
            'Direccion': emp_raw.get('direccion'),
            'Estado': emp_raw.get('estado'),
            'NumCedula': emp_raw.get('numcedula'),
            'EstadoCivil': emp_raw.get('estadocivil'),
            'Sexo': emp_raw.get('sexo'),
            'NumInss': emp_raw.get('numinss'),
            'RUC': emp_raw.get('ruc'),
            'SalarioBase': emp_raw.get('salariobase'),
        }

        emp['Nombres'] = f"{emp['PNombre'] or ''} {emp['SNombre'] or ''}".strip()
        emp['Apellidos'] = f"{emp['PApellido'] or ''} {emp['SApellido'] or ''}".strip()

        if emp_raw.get('supervisorpnombre'):
            emp['NombreSupervisor'] = f"{emp_raw.get('supervisorpnombre') or ''} {emp_raw.get('supervisorsnombre') or ''}".strip()
            emp['ApellidoSupervisor'] = f"{emp_raw.get('supervisorpapellido') or ''} {emp_raw.get('supervisorsapellido') or ''}".strip()

        emp['Edad'] = calcular_edad(emp['FechaDeNacimiento'])
        emp['FechaDeContrato'] = emp['FechaDeInicioContrato']

        empleados.append(emp)

    conn.close()
    return render_template_ajax(
        'Empleados/empleados.html',
        empleados=empleados,
        busqueda=busqueda
    )


@app.route('/editar_empleado/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_empleado(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener el empleado usando consulta explícita para asegurar todas las columnas
    cursor.execute('''
        SELECT id_empleado, pnombre, snombre, papellido, sapellido, estadocivil, sexo, 
               fechadenacimiento, fechadeiniciocontrato, fechadefincontrato, ruc, salariobase,
               numcedula, numinss, estado, direccion, supervisor, papelera
        FROM Empleado 
        WHERE id_empleado = %s
    ''', (id,))
    empleado_raw = cursor.fetchone()

    # Obtener supervisores para el combo (excluyendo el mismo empleado)
    cursor.execute('SELECT id_empleado, pnombre, snombre, papellido, sapellido FROM Empleado WHERE id_empleado != %s', (id,))
    supervisores_raw = cursor.fetchall()

    if not empleado_raw:
        conn.close()
        flash('Empleado no encontrado.', 'danger')
        return redirect(url_for('ver_empleados'))

    # Convertir empleado a diccionario usando nombres de columna explícitos
    columnas = ['id_empleado', 'pnombre', 'snombre', 'papellido', 'sapellido', 'estadocivil', 'sexo', 
                'fechadenacimiento', 'fechadeiniciocontrato', 'fechadefincontrato', 'ruc', 'salariobase',
                'numcedula', 'numinss', 'estado', 'direccion', 'supervisor', 'papelera']
    empleado = dict(zip(columnas, empleado_raw))
    
    # Combinar nombres y apellidos para el empleado
    empleado['Nombres'] = f"{empleado.get('pnombre', '')} {empleado.get('snombre', '')}".strip()
    empleado['Apellidos'] = f"{empleado.get('papellido', '')} {empleado.get('sapellido', '')}".strip()

    # Procesar supervisores
    supervisores = []
    for sup in supervisores_raw:
        supervisor_dict = {
            'id_empleado': sup[0],
            'pnombre': sup[1],
            'snombre': sup[2],
            'papellido': sup[3],
            'sapellido': sup[4],
            'nombres': f"{sup[1]} {sup[2]}".strip(),
            'spellidos': f"{sup[3]} {sup[4]}".strip()
        }
        supervisores.append(supervisor_dict)

    if request.method == 'POST':
        primer_nombre = request.form['primer_nombre']
        segundo_nombre = request.form.get('segundo_nombre', '')
        primer_apellido = request.form['primer_apellido']
        segundo_apellido = request.form.get('segundo_apellido', '')
        cedula = request.form['cedula']
        estado = request.form['estado']
        estado_civil = request.form['estado_civil']
        sexo = request.form['sexo']
        fecha_nacimiento = request.form['fecha_nacimiento']
        fecha_inicontrato = request.form['fecha_Inicontrato']
        fecha_fincontrato = request.form['fecha_Fincontrato']
        direccion = request.form['direccion']
        num_inss = request.form['num']
        num_ruc = request.form['num2']
        salarioBase = request.form['salarioBase'] or 0
        supervisor = request.form['supervisor'] or None
        cursor.execute('''
            UPDATE Empleado
            SET pnombre=%s, snombre=%s, papellido=%s, sapellido=%s, numcedula=%s, estadocivil=%s, sexo=%s, 
                fechadenacimiento=%s, fechadeiniciocontrato=%s, fechadefincontrato=%s, direccion=%s, 
                numinss=%s, ruc=%s, salariobase=%s, supervisor=%s, estado=%s
            WHERE id_empleado=%s
        ''', (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, cedula, estado_civil, sexo,
              fecha_nacimiento, fecha_inicontrato, fecha_fincontrato, direccion, num_inss, num_ruc, salarioBase, supervisor, estado, id))
        conn.commit()
        conn.close()
        flash('Empleado actualizado exitosamente.', 'success')
        return redirect(url_for('ver_empleados'))

    conn.close()
    return render_template_ajax('Empleados/editar_empleado.html', empleado=empleado, supervisores=supervisores)


#Ganancia Diaria
@app.route('/ganancia_diaria')
@login_requerido
def ganancia_diaria():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Traer todas las ganancias
    cursor.execute('''
        SELECT gd.id_venta, gd.fecha, gd.totalventa, gd.gananciacalculada
        FROM GananciaDiaria gd
        ORDER BY gd.id_venta ASC
    ''')
    ganancias = cursor.fetchall()

    # Obtener ventas disponibles para mostrar o calcular
    cursor.execute('SELECT id_venta FROM Venta ORDER BY id_venta ASC')
    ventas = cursor.fetchall()

    fechas = [row[1].strftime('%Y-%m-%d') for row in ganancias if row[3] is not None]
    valores = [float(row[3]) for row in ganancias if row[3] is not None]

    conn.close()

    if is_ajax_request():
        rendered = render_template('Ventas/ganancia_diaria.html', ganancias=ganancias, ventas=ventas, fechas=fechas, valores=valores)
        soup = BeautifulSoup(rendered, 'html.parser')
        content = soup.find('div', class_='content')
        modals = soup.find(attrs={'data-modals': True})

        return jsonify({
            'content': content.prettify() if content else '',
            'modals': modals.prettify() if modals else '',
            'fechas': fechas,
            'valores': valores
        })
    else:
        return render_template('Ventas/ganancia_diaria.html', ganancias=ganancias, ventas=ventas, fechas=fechas, valores=valores)


@app.route('/calcular_ganancia/<int:id_venta>', methods=['POST'])
@login_requerido
def calcular_ganancia(id_venta):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM calculargananciadiaria(%s)', (id_venta,))
        conn.commit()
        flash(f'Ganancia calculada para venta #{id_venta}', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al calcular ganancia: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('ganancia_diaria'))


# Función de debug detallada para verificar funcionalidad de "recuérdame"
@app.route('/debug_recuerdame')
def debug_recuerdame():
    """Página de debug detallada para verificar el funcionamiento de 'recuérdame'"""

    # Obtener todas las cookies
    all_cookies = {}
    for cookie_name in request.cookies:
        all_cookies[cookie_name] = request.cookies[cookie_name]

    # Información específica de cookies de recuerdame
    cookies_info = {
        'recuerdame_usuario': request.cookies.get('recuerdame_usuario', 'NO EXISTE'),
        'recuerdame_tipo': request.cookies.get('recuerdame_tipo', 'NO EXISTE'),
        'recuerdame_user_id': request.cookies.get('recuerdame_user_id', 'NO EXISTE'),
    }

    # Información de sesión
    session_info = {
        'usuario': session.get('usuario', 'NO EXISTE'),
        'tipo': session.get('tipo', 'NO EXISTE'),
        'user_id': session.get('user_id', 'NO EXISTE'),
        'session_keys': list(session.keys()),
    }

    # Verificar usuario en BD si hay cookies
    db_status = "No hay cookies para verificar"
    if cookies_info['recuerdame_usuario'] != 'NO EXISTE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id_usuario, nusuario, tipo FROM Usuario WHERE nusuario = %s',
                         (cookies_info['recuerdame_usuario'],))
            user_from_db = cursor.fetchone()
            conn.close()

            if user_from_db:
                db_status = f"✅ Usuario encontrado en BD: ID={user_from_db[0]}, Usuario={user_from_db[1]}, Tipo={user_from_db[2]}"
            else:
                db_status = "❌ Usuario NO encontrado en base de datos"
        except Exception as e:
            db_status = f"❌ Error al consultar BD: {e}"

    # Estado general
    has_valid_cookies = all(cookie != 'NO EXISTE' for cookie in cookies_info.values())
    has_session = session_info['usuario'] != 'NO EXISTE'

    status_message = ""
    if has_session:
        status_message = "✅ Sesión activa - Usuario logueado"
    elif has_valid_cookies:
        status_message = "🔄 Cookies válidas encontradas - Debería restaurar sesión automáticamente"
    else:
        status_message = "❌ No hay sesión ni cookies válidas"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔍 Debug - Recuérdame</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .success {{ background: #d4edda; border-color: #c3e6cb; }}
            .warning {{ background: #fff3cd; border-color: #ffeaa7; }}
            .error {{ background: #f8d7da; border-color: #f5c6cb; }}
            .info {{ background: #d1ecf1; border-color: #bee5eb; }}
            pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
            .status {{ font-size: 18px; font-weight: bold; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Debug - Funcionalidad "Recuérdame"</h1>

            <div class="status {'success' if has_session else 'warning' if has_valid_cookies else 'error'}">
                {status_message}
            </div>

            <div class="section info">
                <h2>🍪 Cookies de "Recuérdame"</h2>
                <pre>{cookies_info}</pre>
                <p><strong>Estado:</strong> {'✅ Cookies completas' if has_valid_cookies else '❌ Cookies incompletas'}</p>
            </div>

            <div class="section info">
                <h2>📋 Sesión Actual</h2>
                <pre>{session_info}</pre>
                <p><strong>Estado:</strong> {'✅ Sesión activa' if has_session else '❌ Sin sesión'}</p>
            </div>

            <div class="section info">
                <h2>🗄️ Verificación en Base de Datos</h2>
                <p>{db_status}</p>
            </div>

            <div class="section info">
                <h2>🍪 Todas las Cookies del Navegador</h2>
                <pre>{all_cookies}</pre>
            </div>

            <div class="section">
                <h2>🧪 Acciones de Prueba</h2>
                <p>
                    <a href="{url_for('login')}" style="color: #007bff; text-decoration: none;">🔐 Ir a Login</a> |
                    <a href="{url_for('index')}" style="color: #28a745; text-decoration: none;">🏠 Ir al Inicio</a> |
                    <a href="{url_for('logout')}" style="color: #dc3545; text-decoration: none;">🚪 Hacer Logout</a>
                </p>
            </div>

            <div class="section">
                <h2>📝 Instrucciones para Probar</h2>
                <ol>
                    <li>Ve a <a href="{url_for('login')}">/login</a></li>
                    <li>Marca el checkbox "Recuérdame"</li>
                    <li>Inicia sesión</li>
                    <li>Cierra COMPLETAMENTE el navegador</li>
                    <li>Vuelve a abrir y ve directamente a <a href="{url_for('login')}">/login</a></li>
                    <li>Si funciona, deberías ser redirigido automáticamente</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """

#Ejecucion

if __name__ == '__main__':
    print("Iniciando servidor con funcionalidad de 'Recordame'")
    print("Instrucciones:")
    print("   1. Ve a /login")
    print("   2. Marca el checkbox 'Recordame'")
    print("   3. Inicia sesion")
    print("   4. Cierra el navegador")
    print("   5. Vuelve a abrir y ve directamente a cualquier pagina")
    print("   6. Deberias estar logueado automaticamente")
    print("   7. Ve a /debug_recuerdame para verificar el estado detallado")
    app.run(host='0.0.0.0', debug=True)