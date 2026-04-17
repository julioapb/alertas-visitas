from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import current_app
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import MySQLdb.cursors

clientes_bp = Blueprint('clientes', __name__, template_folder='templates')


# ============================
# LISTAR CLIENTES
# ============================
@clientes_bp.route('/clientes')
def clientes():

    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    nombre = request.args.get("nombre", "")
    nif = request.args.get("nif", "")
    telefono = request.args.get("telefono", "")
    tipo_cliente = request.args.get("tipo_cliente", "")
    ciudad = request.args.get("ciudad", "")
    cp = request.args.get("cp", "")

    query = "SELECT * FROM clientes WHERE 1=1"
    params = []

    if nombre:
        query += " AND nombre LIKE %s"
        params.append(f"%{nombre}%")

    if nif:
        query += " AND nif LIKE %s"
        params.append(f"%{nif}%")

    if telefono:
        query += " AND telefono LIKE %s"
        params.append(f"%{telefono}%")

    if tipo_cliente:
        query += " AND tipo_cliente = %s"
        params.append(tipo_cliente)

    if ciudad:
        query += " AND ciudad LIKE %s"
        params.append(f"%{ciudad}%")

    if cp:
        query += " AND codigo_postal LIKE %s"
        params.append(f"%{cp}%")

    query += " ORDER BY id DESC"

    cur.execute(query, tuple(params))
    data = cur.fetchall()

    return render_template('clientes/clientes.html', clientes=data)


# ============================
# EDITAR CLIENTE
# ============================
@clientes_bp.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):

    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    if request.method == 'POST':

        nombre = request.form['nombre']
        tipo_cliente = request.form['tipo_cliente']
        tipo_actividad = request.form['tipo_actividad']
        nif = request.form['nif']
        direccion = request.form['direccion']
        telefono = request.form['telefono']
        ciudad = request.form['ciudad']
        codigo_postal = request.form['codigo_postal']
        email = request.form['email']
        como_nos_conocio = request.form['como_nos_conocio']
        observaciones = request.form['observaciones']

        cur.execute("""
        UPDATE clientes SET 
        nombre=%s,
        tipo_cliente=%s,
        tipo_actividad=%s,
        nif=%s,
        direccion=%s,
        ciudad=%s,
        codigo_postal=%s,
        email=%s,
        como_nos_conocio=%s,
        observaciones=%s,
        telefono=%s
        WHERE id=%s
        """, (
            nombre,
            tipo_cliente,
            tipo_actividad,
            nif,
            direccion,
            ciudad,
            codigo_postal,
            email,
            como_nos_conocio,
            observaciones,
            telefono,
            id
        ))

        mysql.connection.commit()

        flash("Cliente actualizado correctamente.", "success")

        return redirect(url_for('clientes.ver_cliente', id=id))

    cur.execute("SELECT * FROM clientes WHERE id=%s", (id,))
    cliente = cur.fetchone()

    return render_template("clientes/editar_cliente.html", cliente=cliente)


# ============================
# ELIMINAR CLIENTE
# ============================
@clientes_bp.route('/clientes/eliminar/<int:id>')
def eliminar_cliente(id):

    cur = current_app.mysql.connection.cursor()

    cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
    current_app.mysql.connection.commit()

    flash("Cliente eliminado.", "danger")

    return redirect(url_for('clientes.clientes'))


# ============================
# LICENCIAS DEL CLIENTE
# ============================
@clientes_bp.route('/clientes/<int:id>/licencias', methods=['GET', 'POST'])
def licencias_cliente(id):

    cur = current_app.mysql.connection.cursor()

    cur.execute("SELECT id,nombre FROM clientes WHERE id=%s", (id,))
    cliente = cur.fetchone()

    if not cliente:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for('clientes.clientes'))

    if request.method == 'POST':

        id_licencia_tipo = request.form['id_licencia_tipo']
        fecha_inicio = request.form['fecha_inicio']
        tipo_plaga = request.form['tipo_plaga']

        # Desactivar licencias anteriores
        cur.execute("""
        UPDATE licencias_cliente
        SET activo=0
        WHERE id_cliente=%s
        """, (id,))

        # Crear licencia
        cur.execute("""
        INSERT INTO licencias_cliente
        (id_cliente,id_licencia_tipo,tipo_plaga,fecha_inicio,fecha_fin,activo)
        VALUES
        (%s,%s,%s,%s,DATE_ADD(%s,INTERVAL 12 MONTH),1)
        """, (
            id,
            id_licencia_tipo,
            tipo_plaga,
            fecha_inicio,
            fecha_inicio
        ))

        current_app.mysql.connection.commit()

        # Obtener configuración licencia
        cur.execute("""
        SELECT visitas_por_anio,meses_entre_visitas
        FROM licencias_tipo
        WHERE id=%s
        """, (id_licencia_tipo,))

        tipo = cur.fetchone()

        visitas_por_anio = tipo[0]
        meses_intervalo = tipo[1]

        fecha_inicio_dt = datetime.strptime(fecha_inicio,"%Y-%m-%d")

        # Crear visitas programadas
        for i in range(visitas_por_anio):

            fecha_visita = fecha_inicio_dt + relativedelta(months=meses_intervalo*i)

            cur.execute("""
                INSERT INTO visitas_programadas
                (id_cliente,fecha_visita,tipo_plaga,estado)
                VALUES (%s,%s,%s,%s)
                """, (
                    id,
                    fecha_visita.strftime("%Y-%m-%d"),
                    tipo_plaga,
                    'pendiente'
                ))

        current_app.mysql.connection.commit()

        # Generar alertas de visita
        cur.execute("""
        SELECT id,fecha_visita
        FROM visitas_programadas
        WHERE id_cliente=%s
        """, (id,))

        visitas = cur.fetchall()

        for v in visitas:

            id_visita = v[0]
            fecha_visita = v[1]

            fecha_alerta = fecha_visita - relativedelta(days=2)

            cur.execute("""
            INSERT INTO alertas
            (id_cliente,tipo,id_visita,descripcion,fecha_alerta)
            VALUES (%s,'visita',%s,%s,%s)
            """, (
                id,
                id_visita,
                f"Visita programada para el {fecha_visita}",
                fecha_alerta
            ))

        # alerta renovación
        cur.execute("""
        SELECT fecha_fin
        FROM licencias_cliente
        WHERE id_cliente=%s AND activo=1
        """, (id,))

        lic = cur.fetchone()

        if lic:

            fecha_fin = lic[0]
            fecha_alerta_renov = fecha_fin - relativedelta(days=30)

            cur.execute("""
            INSERT INTO alertas
            (id_cliente,tipo,descripcion,fecha_alerta)
            VALUES (%s,'renovacion',%s,%s)
            """, (
                id,
                f"La licencia vence el {fecha_fin}. Coordinar renovación.",
                fecha_alerta_renov
            ))

        current_app.mysql.connection.commit()

        return redirect(url_for('clientes.licencias_cliente',id=id))

    # ============================
    # GET
    # ============================

    # LICENCIAS
    cur.execute("""
    SELECT
    lc.id,
    lt.nombre,
    lc.tipo_plaga,
    lc.fecha_inicio,
    lc.fecha_fin,
    lc.activo
    FROM licencias_cliente lc
    JOIN licencias_tipo lt
    ON lc.id_licencia_tipo=lt.id
    WHERE lc.id_cliente=%s
    ORDER BY lc.fecha_inicio DESC
    """, (id,))

    licencias = cur.fetchall()

    # TIPOS LICENCIA
    cur.execute("SELECT id,nombre FROM licencias_tipo")
    tipos_licencia = cur.fetchall()

    # 🔥 VISITAS PROGRAMADAS (AQUÍ ESTÁ LO NUEVO)
    cur.execute("""
        SELECT id, fecha_visita, tipo_plaga, estado
        FROM visitas_programadas
        WHERE id_cliente = %s
        ORDER BY fecha_visita ASC
    """, (id,))
    visitas_programadas = cur.fetchall()

    fecha_hoy = date.today().strftime("%Y-%m-%d")

    return render_template(
        "clientes/licencias_cliente.html",
        cliente=cliente,
        licencias=licencias,
        tipos_licencia=tipos_licencia,
        visitas_programadas=visitas_programadas,  # 👈 IMPORTANTE
        fecha_hoy=fecha_hoy
    )

# ============================
# VER CLIENTE
# ============================
@clientes_bp.route('/cliente/<int:id>')
def ver_cliente(id):

    mysql = current_app.mysql

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM clientes WHERE id=%s",(id,))
    cliente = cur.fetchone()

    cur.execute("""
    SELECT id,tipo_revision,fecha_revision,observaciones,es_garantia,estado
    FROM revisiones
    WHERE id_cliente=%s
    ORDER BY fecha_revision DESC
    """,(id,))

    revisiones = cur.fetchall()

    cur.execute("""
    SELECT id,tipo_revision,fecha_revision
    FROM revisiones
    WHERE id_cliente=%s
    AND fecha_revision>CURDATE()
    ORDER BY fecha_revision ASC
    LIMIT 1
    """,(id,))

    proxima_revision = cur.fetchone()

    return render_template(
        "clientes/detalle_cliente.html",
        cliente=cliente,
        revisiones=revisiones,
        proxima_revision=proxima_revision
    )


# ============================
# NUEVO CLIENTE
# ============================
@clientes_bp.route('/nuevo',methods=['GET','POST'])
def nuevo_cliente():

    mysql = current_app.mysql

    if request.method == 'POST':

        nombre = request.form['nombre']
        tipo_cliente = request.form['tipo_cliente']
        tipo_actividad = request.form['tipo_actividad']
        nif = request.form['nif']
        direccion = request.form['direccion']
        ciudad = request.form['ciudad']
        codigo_postal = request.form['codigo_postal']
        email = request.form['email']
        como_nos_conocio = request.form['como_nos_conocio']
        telefono = request.form['telefono']
        observaciones = request.form.get('observaciones','')
        razon_social = request.form['razon_social']
        poblacion = request.form['poblacion']

        cur = mysql.connection.cursor()

        cur.execute("""
        INSERT INTO clientes
        (nombre,tipo_cliente,tipo_actividad,nif,direccion,ciudad,codigo_postal,email,como_nos_conocio,telefono,observaciones, razon_social, poblacion)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,(
            nombre,
            tipo_cliente,
            tipo_actividad,
            nif,
            direccion,
            ciudad,
            codigo_postal,
            email,
            como_nos_conocio,
            telefono,
            observaciones,
            razon_social,
            poblacion
        ))

        mysql.connection.commit()

        return redirect(url_for('clientes.clientes'))

    return render_template("clientes/nuevo_cliente.html")