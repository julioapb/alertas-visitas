from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime
import MySQLdb.cursors
from datetime import timedelta

alertas_bp = Blueprint('alertas', __name__, url_prefix='/alertas')

#generar alerta

def generar_alertas():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    # Obtener visitas pendientes
    cur.execute("""
        SELECT id, id_cliente, fecha_visita
        FROM visitas_programadas
        WHERE estado = 'pendiente'
    """)
    visitas = cur.fetchall()

    for visita in visitas:
        id_visita = visita[0]
        id_cliente = visita[1]
        fecha_visita = visita[2]

        fecha_alerta = fecha_visita - timedelta(days=2)

        # Verificar si ya existe alerta (evitar duplicados)
        cur.execute("""
            SELECT id FROM alertas
            WHERE id_visita = %s
        """, (id_visita,))
        existe = cur.fetchone()

        if not existe:
            cur.execute("""
                INSERT INTO alertas (id_cliente, id_visita, tipo, fecha_alerta, atendida)
                VALUES (%s, %s, 'visita', %s, 0)
            """, (
                id_cliente,
                id_visita,
                fecha_alerta
            ))

    mysql.connection.commit()

# Panel de alertas
@alertas_bp.route('/')
def panel_alertas():
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    return redirect(url_for('dashboard'))


# Marcar como realizada
@alertas_bp.route('/realizada/<int:id_alerta>', methods=['POST'])
def alerta_realizada(id_alerta):
    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    # 🔹 Obtener valor del checkbox (certificado)
    certificado = request.form.get('certificado')
    certificado_valor = 'si' if certificado == 'si' else 'no'

    cur.execute("""
        SELECT a.id_cliente, a.fecha_alerta, a.tipo, a.id_visita, v.tipo_plaga, v.importe, v.sf
        FROM alertas a
        LEFT JOIN visitas_programadas v ON a.id_visita = v.id
        WHERE a.id = %s
    """, (id_alerta,))
    alerta = cur.fetchone()

    if alerta:
        id_cliente = alerta[0]
        fecha_alerta = alerta[1]
        tipo = alerta[2]
        id_visita = alerta[3]
        tipo_plaga = alerta[4]
        importe = alerta[5]
        sf = alerta[6]

        # 🔹 INSERT CON CERTIFICADO
        cur.execute("""
            INSERT INTO historial_alertas
            (id_cliente, id_visita, tipo, tipo_plaga, importe, sf, fecha_alerta, fecha_atendida, estado, observacion, certificado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_cliente,
            id_visita,
            tipo,
            tipo_plaga,
            importe,
            sf,
            fecha_alerta,
            datetime.now(),
            'realizada',
            None,
            certificado_valor   # 👈 AQUÍ GUARDAS SI / NO
        ))

        if id_visita:
            cur.execute("""
                UPDATE visitas_programadas
                SET estado = 'realizada'
                WHERE id = %s
            """, (id_visita,))

        cur.execute("DELETE FROM alertas WHERE id = %s", (id_alerta,))
        mysql.connection.commit()

        flash("Visita marcada como realizada", "success")
    else:
        flash("No se encontró la alerta", "danger")

    return redirect(url_for('dashboard'))


# Marcar como no realizada
@alertas_bp.route('/no_realizada/<int:id_alerta>', methods=['POST'])
def alerta_no_realizada(id_alerta):
    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT a.id_cliente, a.fecha_alerta, a.tipo, a.id_visita, v.tipo_plaga, v.importe, v.sf
        FROM alertas a
        LEFT JOIN visitas_programadas v ON a.id_visita = v.id
        WHERE a.id = %s
    """, (id_alerta,))
    alerta = cur.fetchone()

    if alerta:
        id_cliente = alerta[0]
        fecha_alerta = alerta[1]
        tipo = alerta[2]
        id_visita = alerta[3]
        tipo_plaga = alerta[4]
        importe = alerta[5]
        sf = alerta[6]

        cur.execute("""
            INSERT INTO historial_alertas
            (id_cliente, id_visita, tipo, tipo_plaga, importe, sf, fecha_alerta, fecha_atendida, estado, observacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_cliente,
            id_visita,
            tipo,
            tipo_plaga,
            importe,
            sf,
            fecha_alerta,
            datetime.now(),
            'no_realizada',
            None
        ))

        if id_visita:
            cur.execute("""
                UPDATE visitas_programadas
                SET estado = 'no_realizada'
                WHERE id = %s
            """, (id_visita,))

        cur.execute("DELETE FROM alertas WHERE id = %s", (id_alerta,))
        mysql.connection.commit()

        flash("Visita marcada como NO realizada", "warning")
    else:
        flash("No se encontró la alerta", "danger")

    return redirect(url_for('dashboard'))

# Historial de alertas
@alertas_bp.route('/historial')
def historial_alertas():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    cliente = request.args.get("cliente", "")
    tipo = request.args.get("tipo", "")
    estado = request.args.get("estado", "")
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")

    query = """
        SELECT 
            h.id,
            c.nombre,
            h.tipo,
            h.tipo_plaga,
            COALESCE(h.importe, v.importe) AS importe,
            COALESCE(h.sf, v.sf) AS sf,
            h.estado,
            h.fecha_alerta,
            h.fecha_atendida
        FROM historial_alertas h
        JOIN clientes c ON h.id_cliente = c.id
        LEFT JOIN visitas_programadas v ON h.id_visita = v.id
        WHERE 1=1
    """
    params = []

    if cliente:
        query += " AND c.nombre LIKE %s"
        params.append(f"%{cliente}%")

    if tipo:
        query += " AND h.tipo = %s"
        params.append(tipo)

    if estado:
        query += " AND h.estado = %s"
        params.append(estado)

    if desde:
        query += " AND h.fecha_alerta >= %s"
        params.append(desde)

    if hasta:
        query += " AND h.fecha_alerta <= %s"
        params.append(hasta)

    query += " ORDER BY h.fecha_atendida DESC"

    cur.execute(query, tuple(params))
    historial = cur.fetchall()

    return render_template("alertas/historial.html", historial=historial)

# Reprogramar visita
@alertas_bp.route('/reprogramar_visita/<int:id_visita>', methods=['POST'])
def reprogramar_visita(id_visita):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    nueva_fecha = request.form.get('nueva_fecha')

    if not nueva_fecha:
        flash("Debes seleccionar una nueva fecha.", "danger")
        cur.close()
        return redirect(request.referrer)

    try:
        nueva_fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d').date()
        hoy = datetime.today().date()

        # Validar que no sea fecha pasada
        if nueva_fecha_dt < hoy:
            flash("No puedes reprogramar una visita a una fecha pasada.", "danger")
            cur.close()
            return redirect(request.referrer)

        # Obtener datos actuales de la visita
        cur.execute("""
            SELECT id, id_cliente, fecha_visita, estado, tipo_plaga, importe, sf
            FROM visitas_programadas
            WHERE id = %s
        """, (id_visita,))
        visita = cur.fetchone()

        if not visita:
            flash("La visita no existe.", "danger")
            cur.close()
            return redirect(request.referrer)

        id_visita = visita[0]
        id_cliente = visita[1]
        fecha_anterior = visita[2]
        estado_actual = visita[3]
        tipo_plaga = visita[4]
        importe = visita[5]
        sf = visita[6]

        # No permitir reprogramar si ya está realizada o no realizada
        if estado_actual in ['realizada', 'no_realizada']:
            flash("No puedes reprogramar una visita ya cerrada.", "warning")
            cur.close()
            return redirect(request.referrer)

        # Nueva fecha de alerta (2 días antes)
        nueva_fecha_alerta = nueva_fecha_dt - timedelta(days=2)

        # 1. Actualizar visita
        cur.execute("""
            UPDATE visitas_programadas
            SET fecha_visita = %s,
                estado = 'pendiente'
            WHERE id = %s
        """, (nueva_fecha, id_visita))

        # 2. Verificar si ya existe alerta
        cur.execute("""
            SELECT id
            FROM alertas
            WHERE id_visita = %s
              AND tipo = 'visita'
        """, (id_visita,))
        alerta_existente = cur.fetchone()

        if alerta_existente:
            # Actualizar alerta existente
            cur.execute("""
                UPDATE alertas
                SET fecha_alerta = %s,
                    atendida = 0
                WHERE id_visita = %s
                  AND tipo = 'visita'
            """, (nueva_fecha_alerta, id_visita))
        else:
            # Crear nueva alerta si no existe
            cur.execute("""
                INSERT INTO alertas (id_cliente, id_visita, tipo, fecha_alerta, atendida)
                VALUES (%s, %s, 'visita', %s, 0)
            """, (
                id_cliente,
                id_visita,
                nueva_fecha_alerta
            ))

        # 3. Guardar historial
        cur.execute("""
            INSERT INTO historial_alertas
            (id_cliente, id_visita, tipo, tipo_plaga, importe, sf, fecha_alerta, fecha_atendida, estado, observacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_cliente,
            id_visita,
            'visita',
            tipo_plaga,
            importe,
            sf,
            nueva_fecha_alerta,
            datetime.now(),
            'reprogramada',
            f'Visita reprogramada de {fecha_anterior} a {nueva_fecha}'
        ))

        mysql.connection.commit()
        flash("Visita reprogramada correctamente.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al reprogramar la visita: {str(e)}", "danger")

    cur.close()
    return redirect(request.referrer)


# Eliminar visita (sin afectar historial)
@alertas_bp.route('/eliminar_visita/<int:id_visita>', methods=['POST'])
def eliminar_visita(id_visita):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    try:
        # 1. Verificar que la visita exista
        cur.execute("""
            SELECT id, id_cliente, fecha_visita
            FROM visitas_programadas
            WHERE id = %s
        """, (id_visita,))
        visita = cur.fetchone()

        if not visita:
            flash("La visita no existe.", "danger")
            cur.close()
            return redirect(request.referrer)

        # 2. Eliminar registros del historial asociados a esta visita
        cur.execute("""
            DELETE FROM historial_alertas
            WHERE id_visita = %s
        """, (id_visita,))

        # 3. Eliminar alerta asociada
        cur.execute("""
            DELETE FROM alertas
            WHERE id_visita = %s
        """, (id_visita,))

        # 4. Eliminar visita programada
        cur.execute("""
            DELETE FROM visitas_programadas
            WHERE id = %s
        """, (id_visita,))

        mysql.connection.commit()
        flash("Visita eliminada correctamente.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al eliminar la visita: {str(e)}", "danger")

    cur.close()
    return redirect(request.referrer)
