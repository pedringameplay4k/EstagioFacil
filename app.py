from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Configuração inicial do aplicativo
app = Flask(__name__)
app.secret_key = 'chave_secreta_segura' # Necessário para mensagens de feedback
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site_estagios.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Garantir que a pasta de uploads existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Extensões permitidas para o currículo
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

db = SQLAlchemy(app)

# --- Modelo da Base de Dados ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False) # 'aluno', 'empresa' ou 'admin'
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    
    # Dados específicos de Aluno
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    curriculo = db.Column(db.String(120), nullable=True)
    
    # Dados específicos de Empresa
    cnpj = db.Column(db.String(20), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    
    # REMOVEMOS as colunas data_criacao e data_atualizacao para compatibilidade

# Função auxiliar para verificar extensão do ficheiro
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Rotas do Site ---

@app.route('/')
def home():
    # Se já estiver logado, redireciona conforme tipo
    if 'user_id' in session:
        if session['user_type'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['user_type'] == 'empresa':
            return redirect(url_for('empresa_dashboard'))
        else:  # aluno
            return redirect(url_for('vagas'))
    
    # Se não estiver logado, mostra página inicial
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # Recolher dados comuns
        tipo = request.form.get('tipo_usuario')
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        telefone = request.form.get('telefone')

        # Verificar se email já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Erro: Este email já está registrado!')
            return redirect(url_for('cadastro'))

        # Lógica para ALUNO
        if tipo == 'aluno':
            cpf = request.form.get('cpf')
            
            # Verificar se CPF já existe
            usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
            if usuario_existente:
                flash('Erro: Este CPF já está registrado!')
                return redirect(url_for('cadastro'))

            # Upload do Currículo
            arquivo_cv = request.files.get('curriculo')
            nome_cv = ''
            if arquivo_cv and allowed_file(arquivo_cv.filename):
                filename = secure_filename(arquivo_cv.filename)
                arquivo_cv.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                nome_cv = filename
            
            novo_usuario = Usuario(
                tipo='aluno', 
                nome=nome, 
                email=email, 
                senha=generate_password_hash(senha),  # Senha com hash
                telefone=telefone, 
                cpf=cpf, 
                curriculo=nome_cv
            )

        # Lógica para EMPRESA
        else:
            cnpj = request.form.get('cnpj')
            endereco = request.form.get('endereco')
            
            # Verificar se CNPJ já existe
            if cnpj:
                usuario_existente = Usuario.query.filter_by(cnpj=cnpj).first()
                if usuario_existente:
                    flash('Erro: Este CNPJ já está registrado!')
                    return redirect(url_for('cadastro'))
            
            novo_usuario = Usuario(
                tipo='empresa', 
                nome=nome, 
                email=email, 
                senha=generate_password_hash(senha),  # Senha com hash
                telefone=telefone, 
                cnpj=cnpj, 
                endereco=endereco
            )

        # Salvar na base de dados
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso! Faça login para acessar sua conta.')
        return redirect(url_for('login'))

    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        tipo_usuario = request.form.get('tipo_usuario')
        
        # Busca usuário no banco
        usuario = Usuario.query.filter_by(email=email, tipo=tipo_usuario).first()
        
        if usuario:
            # Verifica a senha com hash
            if check_password_hash(usuario.senha, senha):
                # Cria sessão
                session['user_id'] = usuario.id
                session['user_type'] = usuario.tipo
                session['user_email'] = usuario.email
                session['user_name'] = usuario.nome
                
                # Mensagem de boas-vindas
                flash(f'Bem-vindo(a), {usuario.nome}!')
                
                # Redireciona conforme tipo
                if usuario.tipo == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif usuario.tipo == 'empresa':
                    return redirect(url_for('empresa_dashboard'))
                else:  # aluno
                    return redirect(url_for('vagas'))
            else:
                flash('Senha incorreta.')
        else:
            flash('Usuário não encontrado.')
        
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    # Verifica se o usuário está logado e é admin
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acesso não autorizado. Faça login como administrador.')
        return redirect(url_for('login'))
    
    # Coleta dados para o dashboard
    total_usuarios = Usuario.query.count()
    total_alunos = Usuario.query.filter_by(tipo='aluno').count()
    total_empresas = Usuario.query.filter_by(tipo='empresa').count()
    total_admins = Usuario.query.filter_by(tipo='admin').count()
    
    # Últimos usuários cadastrados (sem ordenar por data_criacao)
    ultimos_usuarios = Usuario.query.order_by(Usuario.id.desc()).limit(10).all()
    
    # Estatísticas por tipo
    usuarios_por_tipo = {
        'alunos': total_alunos,
        'empresas': total_empresas,
        'admins': total_admins
    }
    
    return render_template('admin_dashboard.html', 
                         total_usuarios=total_usuarios,
                         total_alunos=total_alunos,
                         total_empresas=total_empresas,
                         usuarios_por_tipo=usuarios_por_tipo,
                         ultimos_usuarios=ultimos_usuarios,
                         user_name=session.get('user_name'))

@app.route('/empresa/dashboard')
def empresa_dashboard():
    if 'user_type' not in session or session['user_type'] != 'empresa':
        flash('Acesso não autorizado.')
        return redirect(url_for('login'))
    
    return render_template('empresa_dashboard.html', user_name=session.get('user_name'))

@app.route('/aluno/dashboard')
def aluno_dashboard():
    if 'user_type' not in session or session['user_type'] != 'aluno':
        flash('Acesso não autorizado.')
        return redirect(url_for('login'))
    
    # Buscar dados do aluno atual
    aluno = Usuario.query.get(session['user_id'])
    
    return render_template('aluno_dashboard.html', 
                         user_name=session.get('user_name'),
                         aluno=aluno)

@app.route('/vagas')
def vagas():
    # Se estiver logado, mostrar nome do usuário
    user_name = session.get('user_name') if 'user_id' in session else None
    user_type = session.get('user_type') if 'user_id' in session else None
    
    return render_template('vagas.html', 
                         user_name=user_name,
                         user_type=user_type,
                         logged_in='user_id' in session)

@app.route('/logout')
def logout():
    user_name = session.get('user_name')
    session.clear()
    if user_name:
        flash(f'Até logo, {user_name}! Você foi desconectado com sucesso.')
    else:
        flash('Você foi desconectado com sucesso.')
    return redirect(url_for('home'))

# Rota para gerenciar usuários (admin)
@app.route('/admin/usuarios')
def admin_usuarios():
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acesso não autorizado.')
        return redirect(url_for('login'))
    
    # Buscar todos os usuários
    usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
    
    return render_template('admin_usuarios.html',
                         usuarios=usuarios,
                         user_name=session.get('user_name'))

# Rota para excluir usuário (admin)
@app.route('/admin/usuario/excluir/<int:id>')
def excluir_usuario(id):
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acesso não autorizado.')
        return redirect(url_for('login'))
    
    # Evitar que o admin exclua a si mesmo
    if id == session['user_id']:
        flash('Você não pode excluir sua própria conta.')
        return redirect(url_for('admin_usuarios'))
    
    usuario = Usuario.query.get(id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuário {usuario.nome} excluído com sucesso.')
    else:
        flash('Usuário não encontrado.')
    
    return redirect(url_for('admin_usuarios'))

# Rota para perfil do usuário
@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        flash('Faça login para acessar seu perfil.')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    return render_template('perfil.html',
                         usuario=usuario,
                         user_name=session.get('user_name'))

# Rota para atualizar perfil
@app.route('/perfil/atualizar', methods=['POST'])
def atualizar_perfil():
    if 'user_id' not in session:
        flash('Faça login para atualizar seu perfil.')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    if usuario:
        usuario.nome = request.form.get('nome', usuario.nome)
        usuario.telefone = request.form.get('telefone', usuario.telefone)
        
        # Se for aluno, atualizar CPF
        if usuario.tipo == 'aluno':
            usuario.cpf = request.form.get('cpf', usuario.cpf)
        
        # Se for empresa, atualizar CNPJ e endereço
        if usuario.tipo == 'empresa':
            usuario.cnpj = request.form.get('cnpj', usuario.cnpj)
            usuario.endereco = request.form.get('endereco', usuario.endereco)
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!')
    
    return redirect(url_for('perfil'))

# Rota para alterar senha
@app.route('/perfil/alterar-senha', methods=['POST'])
def alterar_senha():
    if 'user_id' not in session:
        flash('Faça login para alterar sua senha.')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    if usuario:
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        # Verificar senha atual
        if not check_password_hash(usuario.senha, senha_atual):
            flash('Senha atual incorreta.')
            return redirect(url_for('perfil'))
        
        # Verificar se as novas senhas coincidem
        if nova_senha != confirmar_senha:
            flash('As novas senhas não coincidem.')
            return redirect(url_for('perfil'))
        
        # Atualizar senha
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        flash('Senha alterada com sucesso!')
    
    return redirect(url_for('perfil'))

# Cria as tabelas do banco de dados se não existirem
with app.app_context():
    # Primeiro, apaga o banco de dados existente para recriar com novas colunas
    db.drop_all()  # CUIDADO: Isso apaga todos os dados existentes!
    db.create_all()
    
    # Cria usuário admin padrão
    admin = Usuario(
        tipo='admin',
        nome='Administrador',
        email='admin@portal.com',
        senha=generate_password_hash('admin123'),
        telefone='(00) 00000-0000'
    )
    db.session.add(admin)
    db.session.commit()
    print("Usuário admin criado: admin@portal.com / admin123")
    
    # Cria alguns usuários de exemplo
    usuarios_exemplo = [
        Usuario(
            tipo='aluno',
            nome='João Silva',
            email='joao.silva@email.com',
            senha=generate_password_hash('aluno123'),
            telefone='(11) 99999-9999',
            cpf='123.456.789-00',
            curriculo=''
        ),
        Usuario(
            tipo='aluno',
            nome='Maria Santos',
            email='maria.santos@email.com',
            senha=generate_password_hash('aluno123'),
            telefone='(11) 98888-8888',
            cpf='987.654.321-00',
            curriculo=''
        ),
        Usuario(
            tipo='empresa',
            nome='Tech Solutions',
            email='contato@techsolutions.com',
            senha=generate_password_hash('empresa123'),
            telefone='(11) 97777-7777',
            cnpj='12.345.678/0001-90',
            endereco='Rua das Flores, 123, São Paulo - SP'
        ),
    ]
    
    db.session.add_all(usuarios_exemplo)
    db.session.commit()
    print("Usuários de exemplo criados com sucesso!")

if __name__ == '__main__':
    app.run(debug=True)
with app.app_context():
    try:
        # Tenta adicionar as colunas sem apagar o banco
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE usuario ADD COLUMN data_criacao TIMESTAMP"))
            conn.execute(text("ALTER TABLE usuario ADD COLUMN data_atualizacao TIMESTAMP"))
            conn.commit()
        print("Colunas adicionadas com sucesso!")
    except Exception as e:
        print(f"Erro ao adicionar colunas: {e}")
        print("As colunas podem já existir.")