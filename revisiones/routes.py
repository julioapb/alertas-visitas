from flask import Blueprint, render_template, request, redirect, url_for, current_app

revisiones_bp = Blueprint('revisiones', __name__, url_prefix='/revisiones')


@revisiones_bp.route('/nueva/<int:id_cliente>', methods=['GET', 'POST'])
def nueva_revision(id_cliente):
    mysql = current_app.mysql

    if request.method == 'POST':
        tipo = request.form['tipo_revision']
        fecha = request.form['fecha_revision']
        obs = request.form.get('observaciones', '')
        garantia = 1 if 'es_garantia' in request.form else 0

        cur = mysql.connection.cursor()

        # 1️⃣ Guardar la revisión actual
        cur.execute("""
            INSERT INTO revisiones (id_cliente, tipo_revision, fecha_revision, observaciones, es_garantia)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_cliente, tipo, fecha, obs, garantia))

        # 2️⃣ Calcular próxima revisión automática
        from datetime import datetime, timedelta

        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        proxima_fecha = None

        # Frecuencias según el tipo
        if tipo in ["DDD", "Polillas"]:
            proxima_fecha = fecha_dt + timedelta(days=180)  # 6 meses
        elif tipo in ["Cucarachas", "Mosquitos", "Mosquitos de la humedad"]:
            proxima_fecha = fecha_dt + timedelta(days=90)   # 3 meses
        elif tipo == "Roedores":
            proxima_fecha = fecha_dt + timedelta(days=60)   # 2 meses
        else:
            proxima_fecha = None  # revisiones sin recurrencia

        # 3️⃣ Crear alerta automática si hay próxima revisión — sin duplicar
        if proxima_fecha:
            fecha_alerta = proxima_fecha.strftime("%Y-%m-%d")

            # Verificar si ya existe una alerta para esa fecha
            cur.execute("""
                SELECT id FROM alertas
                WHERE id_cliente = %s
                AND tipo = 'visita'
                AND fecha_alerta = %s
            """, (id_cliente, fecha_alerta))
            existe = cur.fetchone()

            # Si NO existe, la creamos
            if not existe:
                cur.execute("""
                    INSERT INTO alertas (id_cliente, tipo, fecha_alerta, atendida)
                    VALUES (%s, 'visita', %s, 0)
                """, (id_cliente, fecha_alerta))

        mysql.connection.commit()

        return redirect(url_for('clientes.ver_cliente', id=id_cliente))

    # GET → Mostrar formulario
    return render_template('revisiones/nueva.html', id_cliente=id_cliente)