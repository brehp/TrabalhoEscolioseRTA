from flask import Flask, render_template, request, redirect, url_for
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import threading
from datetime import datetime
import base64

#Cria o site no flask
app = Flask(__name__)

DATABASE_URL = "postgresql://pacientes_web_user:uKk2h90mdG3FVesUsIBf2AuZqCbmfwnZ@dpg-cvu4v9h5pdvs73e4qec0-a.oregon-postgres.render.com/pacientes_web"

# Retorna uma conexão com o banco de dados usando dicionário como retorno
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Busca as imagens desse paciente, transforma em base64 para exibir no site
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

# Busca o nome do paciente e todas as imagens no banco.
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
    # Importa um script chamado desenhar_mao.py.
    import desenhar_mao
    # Chama a função run(paciente_id) desse script para iniciar a interface de desenho.
    desenhar_mao(paciente_id)
    # Após terminar, redireciona para o dashboard.
    return redirect(url_for('dashboard', paciente_id=paciente_id))

# Pagina inicial
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/paciente')
def entrar_com_cpf():
    # Pega o CPF digitado.
    cpf = request.args.get('cpf')
    senha = request.args.get('senha')

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM pacientes WHERE cpf = %s AND senha = %s", (cpf, senha,))
    result = c.fetchone()
    conn.close()

    if result:
        paciente_id = result['id']
        return redirect(url_for('dashboard', paciente_id=paciente_id))
    else:
        return "Paciente não encontrado. Verifique o CPF ou cadastre-se."

#Insere o cadastro do paciente
@app.route('/cadastro', methods=['POST'])
def cadastro():
    nome = request.form['nome']
    data_nascimento = request.form['data_nascimento']
    cpf = request.form['cpf']
    senha = request.form['senha']

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO pacientes (nome, data_nascimento, cpf, senha) VALUES (%s, %s, %s, %s)",
              (nome, data_nascimento, cpf, senha))
    conn.commit()
    c.execute("SELECT LASTVAL()")
    paciente_id = c.fetchone()['lastval']
    conn.close()

    return redirect(url_for('dashboard', paciente_id=paciente_id))

#Recebe imagem do formulario e salva no banco
@app.route('/upload/<int:paciente_id>', methods=['POST'])
def upload(paciente_id):
    img_bytes = request.files['imagem']
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO imagens (paciente_id, imagem, data) VALUES (%s, %s, %s)",
                (paciente_id, psycopg2.Binary(img_bytes), time.strftime("%Y-%m-%d")))
    conn.commit()

    conn.close()

    return redirect(url_for('dashboard', paciente_id=paciente_id))

#Roda o arquivo para desenhar e a espera é em uma pagina aguarde 
@app.route('/desenhar_mao/<int:paciente_id>')
def desenhar_mao_threaded(paciente_id):
    '''def executar_desenho():
        os.system(f"python desenhar_mao.py {paciente_id}")
    threading.Thread(target=executar_desenho).start()'''
    return redirect(url_for('aguarde', paciente_id=paciente_id))

if __name__ == '__main__':
    app.run(debug=True)
