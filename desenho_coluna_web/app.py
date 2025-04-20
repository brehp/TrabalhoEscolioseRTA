from flask import Flask, render_template, request, redirect, url_for
from psycopg2 import connect, sql
import psycopg2.extras

app = Flask(__name__)

# Configuração do banco de dados
DATABASE_URL = "postgresql://pacientes_web_user:uKk2h90mdG3FVesUsIBf2AuZqCbmfwnZ@dpg-cvu4v9h5pdvs73e4qec0-a.oregon-postgres.render.com/pacientes_web"

# Função para conectar ao banco de dados
def get_db_connection():
    conn = connect(DATABASE_URL, sslmode='require')
    return conn




#Pagina de Login###################################################################




# Redireciona inicio para ser login.html
@app.route('/')
def index():
    return render_template('login.html')

# Rota para realizar o login e ser redirecionado a pagina de paciente ainda não feita 
@app.route('/login', methods=['POST'])
def login():
    cpf = request.form['cpf']
    senha = request.form['senha']

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    query = sql.SQL("SELECT * FROM pacientes WHERE cpf = %s AND senha = %s")
    cursor.execute(query, (cpf, senha))
    user = cursor.fetchone()

    conn.close()
 
    if user:
        return render_template('dashboard.html')  # Página de sucesso após login
    else:
        return "CPF ou senha inválidos", 401

# Redireciona de login para a pagina cadastro
@app.route('/redireciona_Login_Cadastro')
def redirecionar_LoginCadastro():
    return render_template('cadastro.html')

# Redireciona de cadastro para a pagina login
@app.route('/redireciona_Cadastro_Login')
def redirecionar_CadastroLogin():
    return render_template('login.html')

# Cadastro de paciente e redirecionamento a pagina de paciente ainda não feita 
@app.route('/cadastro', methods=['POST'])
def cadastro():
    nome = request.form['nome']
    data_nascimento = request.form['data_nascimento']
    cpf = request.form['cpf']
    senha = request.form['senha']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verifica se o CPF já está cadastrado
    query = sql.SQL("SELECT * FROM pacientes WHERE cpf = %s")
    cursor.execute(query, (cpf,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return "Este CPF já está cadastrado.", 400

    # Cadastrar novo usuário
    insert_query = sql.SQL("""
        INSERT INTO pacientes (nome, data_nascimento, cpf, senha)
        VALUES (%s, %s, %s, %s)
    """)
    cursor.execute(insert_query, (nome, data_nascimento, cpf, senha))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))  # Redireciona para a página de login após cadastro

#Pagina de teste 















# Página de sucesso após o login (exemplo de dashboard)


if __name__ == '__main__':
    app.run(debug=True)
