from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from flask import current_app as app

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']

        cur = app.mysql.connection.cursor()
        cur.execute("SELECT id, usuario, clave FROM usuarios WHERE usuario = %s", (usuario,))
        user = cur.fetchone()

        if user and check_password_hash(user[2], clave):
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))

        flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
