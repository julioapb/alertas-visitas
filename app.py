from flask import Flask
from flask_mysqldb import MySQL
from auth.routes import auth_bp
from clientes.routes import clientes_bp
from alertas.routes import alertas_bp, generar_alertas
from flask import render_template, session, redirect, url_for, request
from datetime import date, datetime
from revisiones.routes import revisiones_bp

app = Flask(__name__)
app.config.from_object('config')

mysql = MySQL(app)
app.mysql = mysql

TIPOS_ACTIVIDAD = [
    "Comunidades",
    "Naves",
    "Peluqueria/ esteticas",
    "Restaurantes",
    "Tiendas/comercios",
    "Fincas",
    "Administración",
]


@app.template_filter('fecha_es')
def fecha_es(value):
    if not value:
        return ''

    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y %H:%M')

    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')

    if isinstance(value, str):
        for formato in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                fecha = datetime.strptime(value, formato)
                return fecha.strftime('%d/%m/%Y %H:%M' if ' ' in value else '%d/%m/%Y')
            except ValueError:
                pass

    return value

# Registrar los Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(alertas_bp)
app.register_blueprint(revisiones_bp)


@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    generar_alertas()

    cur = mysql.connection.cursor()

    # =========================
    # FILTROS
    # =========================
    cliente = request.args.get('cliente', '')
    tipo_actividad = request.args.get('tipo_actividad', '')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')

    # =========================
    # ALERTAS DE VISITAS
    # =========================
    query_visitas = """
        SELECT a.id, c.nombre, v.fecha_visita, a.fecha_alerta, v.id, v.tipo_plaga
        FROM alertas a
        JOIN clientes c ON a.id_cliente = c.id
        JOIN visitas_programadas v ON a.id_visita = v.id
        WHERE a.tipo = 'visita'
          AND a.atendida = 0
          AND a.fecha_alerta <= CURDATE()
    """
    params_visitas = []

    if cliente:
        query_visitas += " AND c.nombre LIKE %s"
        params_visitas.append(f"%{cliente}%")

    if tipo_actividad:
        query_visitas += " AND c.tipo_actividad = %s"
        params_visitas.append(tipo_actividad)

    if desde:
        query_visitas += " AND a.fecha_alerta >= %s"
        params_visitas.append(desde)

    if hasta:
        query_visitas += " AND a.fecha_alerta <= %s"
        params_visitas.append(hasta)

    query_visitas += " ORDER BY a.fecha_alerta ASC"

    cur.execute(query_visitas, tuple(params_visitas))
    alertas_visitas = cur.fetchall()

    # =========================
    # ALERTAS DE RENOVACIÓN
    # =========================
    query_renov = """
        SELECT a.id, c.nombre, lc.fecha_fin, a.fecha_alerta
        FROM alertas a
        JOIN clientes c ON a.id_cliente = c.id
        JOIN licencias_cliente lc ON lc.id_cliente = c.id AND lc.activo = 1
        WHERE a.tipo = 'renovacion'
          AND a.atendida = 0
          AND a.fecha_alerta <= CURDATE()
    """
    params_renov = []

    if cliente:
        query_renov += " AND c.nombre LIKE %s"
        params_renov.append(f"%{cliente}%")

    if tipo_actividad:
        query_renov += " AND c.tipo_actividad = %s"
        params_renov.append(tipo_actividad)

    if desde:
        query_renov += " AND a.fecha_alerta >= %s"
        params_renov.append(desde)

    if hasta:
        query_renov += " AND a.fecha_alerta <= %s"
        params_renov.append(hasta)

    query_renov += " ORDER BY a.fecha_alerta ASC"

    cur.execute(query_renov, tuple(params_renov))
    alertas_renov = cur.fetchall()

    return render_template(
        'dashboard.html',
        alertas_visitas=alertas_visitas,
        alertas_renov=alertas_renov,
        tipos_actividad=TIPOS_ACTIVIDAD
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
