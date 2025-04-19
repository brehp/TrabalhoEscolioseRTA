from flask import Flask, render_template, request, redirect, url_for
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import threading
from datetime import datetime
import base64

app = Flask(__name__)

DATABASE_URL = "postgresql://pacientes_web_user:uKk2h90mdG3FVesUsIBf2AuZqCbmfwnZ@dpg-cvu4v9h5pdvs73e4qec0-a.oregon-postgres.render.com/pacientes_web"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_imagens_paciente(paciente_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT imagem, data FROM imagens WHERE paciente_id = %s ORDER BY data DESC", (paciente_id,))
    rows = cur.fetchall()
    imagens = []

    for row in rows:
        if row['imagem']:
            imagem_base64 = base64.b64encode(row['imagem']).decode('utf-8')
            imagens.append({
                'imagem_base64': imagem_base64,
                'data': row['data']
            })

    conn.close()
    return imagens

@app.route("/dashboard/<int:paciente_id>")
def dashboard(paciente_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nome FROM pacientes WHERE id = %s", (paciente_id,))
    result = c.fetchone()
    nome = result['nome'] if result else "Paciente"
    conn.close()

    imagens = get_imagens_paciente(paciente_id)
    ultima_imagem = imagens[0]['imagem_base64'] if imagens else None

    return render_template("dashboard.html", nome=nome, imagens=imagens, ultima_imagem=ultima_imagem, paciente_id=paciente_id)

@app.route("/desenhar/<int:paciente_id>")
def desenhar_mao(paciente_id):
    import desenhar_mao
    desenhar_mao.run(paciente_id)
    return redirect(url_for('dashboard', paciente_id=paciente_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/paciente')
def entrar_com_cpf():
    cpf = request.args.get('cpf')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM pacientes WHERE cpf = %s", (cpf,))
    result = c.fetchone()
    conn.close()

    if result:
        paciente_id = result['id']
        return redirect(url_for('dashboard', paciente_id=paciente_id))
    else:
        return "Paciente não encontrado. Verifique o CPF ou cadastre-se.", 404

@app.route('/cadastro', methods=['POST'])
def cadastro():
    nome = request.form['nome']
    data_nascimento = request.form['data_nascimento']
    cpf = request.form['cpf']

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO pacientes (nome, data_nascimento, cpf) VALUES (%s, %s, %s)",
              (nome, data_nascimento, cpf))
    conn.commit()
    c.execute("SELECT LASTVAL()")
    paciente_id = c.fetchone()['lastval']
    conn.close()

    return redirect(url_for('dashboard', paciente_id=paciente_id))

@app.route('/upload/<int:paciente_id>', methods=['POST'])
def upload(paciente_id):
    image = request.files['imagem']
    if image:
        image_bytes = image.read()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO imagens (paciente_id, imagem, data) VALUES (%s, %s, %s)",
                  (paciente_id, psycopg2.Binary(image_bytes), time.strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()

    return redirect(url_for('dashboard', paciente_id=paciente_id))

@app.route('/desenhar_mao/<int:paciente_id>')
def desenhar_mao_threaded(paciente_id):
    def executar_desenho():
        os.system(f"python desenhar_mao.py {paciente_id}")
    threading.Thread(target=executar_desenho).start()
    return render_template('aguarde.html', paciente_id=paciente_id)

if __name__ == '__main__':
    app.run(debug=True)
