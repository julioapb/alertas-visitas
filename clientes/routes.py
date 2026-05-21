from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask import current_app
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation
import MySQLdb.cursors

clientes_bp = Blueprint('clientes', __name__, template_folder='templates')

TIPOS_ACTIVIDAD = [
    "Comunidades",
    "Naves",
    "Peluqueria/ esteticas",
    "Restaurantes",
    "Tiendas/comercios",
    "Fincas",
    "Administración",
]


# ============================
# LISTAR CLIENTES
# ============================
@clientes_bp.route('/clientes')
def clientes():

    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    per_page = 40
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    nombre = request.args.get("nombre", "")
    nif = request.args.get("nif", "")
    telefono = request.args.get("telefono", "")
    tipo_cliente = request.args.get("tipo_cliente", "")
    tipo_actividad = request.args.get("tipo_actividad", "")
    ciudad = request.args.get("ciudad", "")
    cp = request.args.get("cp", "")

    where = " WHERE 1=1"
    params = []

    if nombre:
        where += " AND nombre LIKE %s"
        params.append(f"%{nombre}%")

    if nif:
        where += " AND nif LIKE %s"
        params.append(f"%{nif}%")

    if telefono:
        where += " AND telefono LIKE %s"
        params.append(f"%{telefono}%")

    if tipo_cliente:
        where += " AND tipo_cliente = %s"
        params.append(tipo_cliente)

    if tipo_actividad:
        where += " AND tipo_actividad = %s"
        params.append(tipo_actividad)

    if ciudad:
        where += " AND ciudad LIKE %s"
        params.append(f"%{ciudad}%")

    if cp:
        where += " AND codigo_postal LIKE %s"
        params.append(f"%{cp}%")

    count_query = "SELECT COUNT(*) FROM clientes" + where
    cur.execute(count_query, tuple(params))
    total_clientes = cur.fetchone()[0]

    total_pages = (total_clientes + per_page - 1) // per_page
    if total_pages and page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page
    query = "SELECT * FROM clientes" + where + " ORDER BY id DESC LIMIT %s OFFSET %s"
    query_params = params + [per_page, offset]

    cur.execute(query, tuple(query_params))
    data = cur.fetchall()

    query_args = request.args.to_dict()
    query_args.pop("page", None)

    return render_template(
        'clientes/clientes.html',
        clientes=data,
        tipos_actividad=TIPOS_ACTIVIDAD,
        page=page,
        per_page=per_page,
        total_clientes=total_clientes,
        total_pages=total_pages,
        query_args=query_args
    )


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

    return render_template(
        "clientes/editar_cliente.html",
        cliente=cliente,
        tipos_actividad=TIPOS_ACTIVIDAD
    )


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
        importe_raw = request.form.get('importe', '').strip().replace(',', '.')
        sf = 1 if request.form.get('sf') == '1' else None

        try:
            importe = Decimal(importe_raw)
            if importe < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash("Introduce un importe valido.", "danger")
            return redirect(url_for('clientes.licencias_cliente', id=id))

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
        SELECT visitas_por_anio,meses_entre_visitas,nombre
        FROM licencias_tipo
        WHERE id=%s
        """, (id_licencia_tipo,))

        tipo = cur.fetchone()

        visitas_por_anio = tipo[0]
        meses_intervalo = tipo[1]
        nombre_tipo = tipo[2]

        fecha_inicio_dt = datetime.strptime(fecha_inicio,"%Y-%m-%d")

        # Crear visitas programadas
        for i in range(visitas_por_anio):

            fecha_visita = fecha_inicio_dt + relativedelta(months=meses_intervalo*i)

            cur.execute("""
                INSERT INTO visitas_programadas
                (id_cliente,fecha_visita,tipo_plaga,estado,importe,sf)
                VALUES (%s,%s,%s,%s,%s,%s)
                """, (
                    id,
                    fecha_visita.strftime("%Y-%m-%d"),
                    tipo_plaga,
                    'pendiente',
                    importe,
                    sf
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

        # alerta renovación (solo si no es Mensual)
        if nombre_tipo != 'Mensual':
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

    # HISTORIAL DE VISITAS
    cur.execute("""
    SELECT
        h.id,
        h.id_visita,
        h.tipo_plaga,
        COALESCE(h.importe, vp.importe) AS importe,
        COALESCE(h.sf, vp.sf) AS sf,
        h.estado,
        h.fecha_alerta,
        h.fecha_atendida
    FROM historial_alertas h
    LEFT JOIN visitas_programadas vp
    ON h.id_visita=vp.id
    WHERE h.id_cliente=%s
      AND h.tipo='visita'
    ORDER BY h.fecha_atendida DESC
    """, (id,))

    historial_visitas = cur.fetchall()

    # TIPOS LICENCIA
    cur.execute("SELECT id,nombre,visitas_por_anio FROM licencias_tipo")
    tipos_licencia = cur.fetchall()

    # 🔥 VISITAS PROGRAMADAS (AQUÍ ESTÁ LO NUEVO)
    cur.execute("""
        SELECT id, fecha_visita, tipo_plaga, estado, importe, sf
        FROM visitas_programadas
        WHERE id_cliente = %s
          AND estado = 'pendiente'
        ORDER BY fecha_visita ASC
    """, (id,))
    visitas_programadas = cur.fetchall()

    fecha_hoy = date.today().strftime("%Y-%m-%d")

    return render_template(
        "clientes/licencias_cliente.html",
        cliente=cliente,
        historial_visitas=historial_visitas,
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

    cur.execute("""
    SELECT
        h.id AS historial_id,
        h.id_visita,
        h.tipo,
        h.tipo_plaga,
        COALESCE(h.importe, vp.importe) AS importe,
        COALESCE(h.sf, vp.sf) AS sf,
        h.estado,
        h.fecha_alerta,
        h.fecha_atendida
    FROM historial_alertas h
    LEFT JOIN visitas_programadas vp
    ON h.id_visita=vp.id
    WHERE h.id_cliente=%s
      AND h.tipo='visita'
    ORDER BY h.fecha_atendida DESC
    """,(id,))

    historial_visitas = cur.fetchall()

    return render_template(
        "clientes/detalle_cliente.html",
        cliente=cliente,
        revisiones=revisiones,
        proxima_revision=proxima_revision,
        historial_visitas=historial_visitas
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

    return render_template(
        "clientes/nuevo_cliente.html",
        tipos_actividad=TIPOS_ACTIVIDAD
    )
