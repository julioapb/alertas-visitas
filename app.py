from flask import Flask
from flask_mysqldb import MySQL
from auth.routes import auth_bp
from clientes.routes import clientes_bp
from alertas.routes import alertas_bp
from flask import render_template, session, redirect, url_for, request
from datetime import date
from revisiones.routes import revisiones_bp

app = Flask(__name__)
app.config.from_object('config')

mysql = MySQL(app)
app.mysql = mysql

# Registrar los Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(alertas_bp)
app.register_blueprint(revisiones_bp)


@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()

    # =========================
    # FILTROS
    # =========================
    cliente = request.args.get('cliente', '')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')

    # =========================
    # ALERTAS DE VISITAS
    # =========================
    query_visitas = """
        SELECT a.id, c.nombre, v.fecha_visita, a.fecha_alerta, v.id
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
        alertas_renov=alertas_renov
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)