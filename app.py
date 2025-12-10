from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

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
    foto_perfil = db.Column(db.String(120), nullable=True)
    sobre_mim = db.Column(db.Text, nullable=True) # Text permite textos longos
    
    # Dados específicos de Aluno
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    curriculo = db.Column(db.String(120), nullable=True)
    
    # Dados específicos de Empresa
    cnpj = db.Column(db.String(20), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    
    # Colunas de timestamp
    data_criacao = db.Column(db.DateTime, server_default=db.func.now())
    data_atualizacao = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


    # --- Adicione isso ABAIXO da class Usuario no app.py ---

class Vaga(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    salario = db.Column(db.String(50))
    localizacao = db.Column(db.String(100))
    tipo = db.Column(db.String(50)) # Presencial, Remoto, Híbrido
    beneficios = db.Column(db.Text)
    area = db.Column(db.String(50)) # TI, ADM, RH...
    
    # Relacionamento: Quem criou a vaga?
    empresa_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    empresa = db.relationship('Usuario', backref=db.backref('vagas', lazy=True))
    
    data_criacao = db.Column(db.DateTime, server_default=db.func.now())
# Função auxiliar para verificar extensão do ficheiro
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Rotas do Site ---

@app.route('/')
def home():
    user_name = session.get('user_name') if 'user_id' in session else None
    
    # Renderiza o index.html (que agora tem o código das vagas)
    vagas = Vaga.query.order_by(Vaga.data_criacao.desc()).all()
    
    return render_template('index.html', user_name=user_name, session=session, vagas=vagas)

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
            flash('Erro: Este email já está registrado!', 'error')
            return redirect(url_for('cadastro'))

        # Lógica para ALUNO
        if tipo == 'aluno':
            cpf = request.form.get('cpf')
            
            # Verificar se CPF já existe
            usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
            if usuario_existente:
                flash('Erro: Este CPF já está registrado!', 'error')
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
                    flash('Erro: Este CNPJ já está registrado!', 'error')
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
        
        flash('Cadastro realizado com sucesso! Faça login para acessar sua conta.', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        tipo_usuario = request.form.get('tipo_usuario')
        
        usuario = Usuario.query.filter_by(email=email, tipo=tipo_usuario).first()
        
        if usuario and check_password_hash(usuario.senha, senha):
            session['user_id'] = usuario.id
            session['user_type'] = usuario.tipo
            session['user_email'] = usuario.email
            session['user_name'] = usuario.nome
            
            flash(f'Bem-vindo(a), {usuario.nome}!', 'success')
            
            # MUDANÇA AQUI: Todo mundo vai para a HOME (Lista de Vagas)
            # O Admin vai para lá também, mas terá o botão "Painel Admin" no topo
            return redirect(url_for('home'))
            
        else:
            flash('Login inválido.', 'error')
            
    return render_template('login.html')

@app.route('/empresa/dashboard', methods=['GET', 'POST'])
def empresa_dashboard():
    # Segurança
    if 'user_type' not in session or session['user_type'] != 'empresa':
        flash('Acesso restrito para empresas.', 'warning')
        return redirect(url_for('login'))
    
    # SE FOR POST: SALVAR NOVA VAGA
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        salario = request.form.get('salario')
        localizacao = request.form.get('localizacao')
        tipo = request.form.get('tipo')
        area = request.form.get('area')
        beneficios = request.form.get('beneficios')
        
        nova_vaga = Vaga(
            titulo=titulo,
            descricao=descricao,
            salario=salario,
            localizacao=localizacao,
            tipo=tipo,
            area=area,
            beneficios=beneficios,
            empresa_id=session['user_id'] # Pega o ID da empresa logada
        )
        
        db.session.add(nova_vaga)
        db.session.commit()
        flash('Vaga publicada com sucesso!', 'success')
        return redirect(url_for('empresa_dashboard'))

    # SE FOR GET: MOSTRAR AS VAGAS DESSA EMPRESA
    minhas_vagas = Vaga.query.filter_by(empresa_id=session['user_id']).order_by(Vaga.data_criacao.desc()).all()
    
    return render_template('empresa_dashboard.html', 
                         user_name=session.get('user_name'),
                         vagas=minhas_vagas)

@app.route('/vaga/excluir/<int:id>')
def excluir_vaga(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    vaga = Vaga.query.get(id)
    # Só deixa excluir se a vaga for da própria empresa
    if vaga and vaga.empresa_id == session['user_id']:
        db.session.delete(vaga)
        db.session.commit()
        flash('Vaga removida.', 'success')
    
    return redirect(url_for('empresa_dashboard'))

@app.route('/aluno/dashboard')
def aluno_dashboard():
    if 'user_type' not in session or session['user_type'] != 'aluno':
        flash('Acesso não autorizado.', 'warning')
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

@app.route('/admin/dashboard')
def admin_dashboard():
    # 1. Proteção: Só entra se for admin
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Área restrita.', 'warning')
        return redirect(url_for('home'))
    
    try:
        total_usuarios = Usuario.query.count()
        total_alunos = Usuario.query.filter_by(tipo='aluno').count()
        total_empresas = Usuario.query.filter_by(tipo='empresa').count()
        
        # Pega os 5 usuários mais recentes
        ultimos_usuarios = Usuario.query.order_by(Usuario.data_criacao.desc()).limit(5).all()
        
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        total_usuarios = 0
        total_alunos = 0
        total_empresas = 0
        ultimos_usuarios = []

    # 3. Envia os dados para o HTML (Servindo a mesa)
    return render_template('admin_dashboard.html', 
                         user_name=session.get('user_name'), # Resolve o "Olá, None"
                         total_usuarios=total_usuarios,      # Preenche o card azul
                         total_alunos=total_alunos,          # Preenche o card verde
                         total_empresas=total_empresas,      # Preenche o card laranja
                         ultimos_usuarios=ultimos_usuarios)  # Preenche a tabela

@app.route('/logout')
def logout():
    user_name = session.get('user_name')
    session.clear()
    if user_name:
        flash(f'Até logo, {user_name}! Você foi desconectado com sucesso.', 'info')
    else:
        flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('home'))

# Rota para gerenciar usuários (admin)
@app.route('/admin/usuarios')
def admin_usuarios():
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acesso não autorizado.', 'warning')
        return redirect(url_for('login'))
    
    # Buscar todos os usuários
    usuarios = Usuario.query.order_by(Usuario.data_criacao.desc()).all()
    
    return render_template('admin_usuarios.html',
                         usuarios=usuarios,
                         user_name=session.get('user_name'))

# Rota para excluir usuário (admin)
@app.route('/admin/usuario/excluir/<int:id>')
def excluir_usuario(id):
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acesso não autorizado.', 'warning')
        return redirect(url_for('login'))
    
    # Evitar que o admin exclua a si mesmo
    if id == session['user_id']:
        flash('Você não pode excluir sua própria conta.', 'warning')
        return redirect(url_for('admin_usuarios'))
    
    usuario = Usuario.query.get(id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuário {usuario.nome} excluído com sucesso.', 'success')
    else:
        flash('Usuário não encontrado.', 'error')
    
    return redirect(url_for('admin_usuarios'))

# Rota para perfil do usuário
@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        flash('Faça login para acessar seu perfil.', 'warning')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    return render_template('perfil.html',
                         usuario=usuario,
                         user_name=session.get('user_name'))

# Rota para atualizar perfil
@app.route('/perfil/atualizar', methods=['POST'])
def atualizar_perfil():
    if 'user_id' not in session:
        flash('Faça login para atualizar seu perfil.', 'warning')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    if usuario:
        # Atualiza dados básicos
        usuario.nome = request.form.get('nome', usuario.nome)
        usuario.telefone = request.form.get('telefone', usuario.telefone)
        usuario.sobre_mim = request.form.get('sobre_mim', usuario.sobre_mim) # Novo campo
        
        # Atualiza dados específicos
        if usuario.tipo == 'aluno':
            usuario.cpf = request.form.get('cpf', usuario.cpf)
        elif usuario.tipo == 'empresa':
            usuario.cnpj = request.form.get('cnpj', usuario.cnpj)
            usuario.endereco = request.form.get('endereco', usuario.endereco)
            
        # Lógica da FOTO DE PERFIL
        arquivo_foto = request.files.get('foto_perfil')
        if arquivo_foto and arquivo_foto.filename != '':
            # Aceita apenas imagens
            if '.' in arquivo_foto.filename and arquivo_foto.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}:
                filename = secure_filename(f"user_{usuario.id}_{arquivo_foto.filename}")
                arquivo_foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                usuario.foto_perfil = filename
            else:
                flash('Formato de imagem inválido. Use PNG ou JPG.', 'error')
                return redirect(url_for('perfil'))

        db.session.commit()
        session['user_name'] = usuario.nome
        flash('Perfil atualizado com sucesso!', 'success')
    
    return redirect(url_for('perfil'))
# Rota para alterar senha
@app.route('/perfil/alterar-senha', methods=['POST'])
def alterar_senha():
    if 'user_id' not in session:
        flash('Faça login para alterar sua senha.', 'warning')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    if usuario:
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        # Verificar senha atual
        if not check_password_hash(usuario.senha, senha_atual):
            flash('Senha atual incorreta.', 'error')
            return redirect(url_for('perfil'))
        
        # Verificar se as novas senhas coincidem
        if nova_senha != confirmar_senha:
            flash('As novas senhas não coincidem.', 'error')
            return redirect(url_for('perfil'))
        
        # Atualizar senha
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        flash('Senha alterada com sucesso!', 'success')
    
    return redirect(url_for('perfil'))

# Rota para dashboard principal
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Faça login para acessar o dashboard.', 'warning')
        return redirect(url_for('login'))
    
    # Redireciona conforme tipo de usuário
    if session['user_type'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif session['user_type'] == 'empresa':
        return redirect(url_for('empresa_dashboard'))
    else:  # aluno
        return redirect(url_for('aluno_dashboard'))

# Rota para ver currículo (apenas para alunos)
@app.route('/curriculo')
def ver_curriculo():
    if 'user_id' not in session or session['user_type'] != 'aluno':
        flash('Acesso não autorizado.', 'warning')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    if usuario.curriculo and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], usuario.curriculo)):
        # Aqui você poderia retornar o arquivo para download
        flash('Currículo disponível para download.', 'info')
        return redirect(url_for('aluno_dashboard'))
    else:
        flash('Nenhum currículo enviado.', 'info')
        return redirect(url_for('aluno_dashboard'))

# Rota para upload de currículo
@app.route('/curriculo/upload', methods=['POST'])
def upload_curriculo():
    if 'user_id' not in session or session['user_type'] != 'aluno':
        flash('Acesso não autorizado.', 'warning')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    arquivo_cv = request.files.get('curriculo')
    if arquivo_cv and allowed_file(arquivo_cv.filename):
        filename = secure_filename(arquivo_cv.filename)
        arquivo_cv.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        usuario.curriculo = filename
        db.session.commit()
        flash('Currículo enviado com sucesso!', 'success')
    else:
        flash('Formato de arquivo inválido. Use PDF, DOC ou DOCX.', 'error')
    
    return redirect(url_for('aluno_dashboard'))

# Inicialização do banco de dados
with app.app_context():
    try:
        # Tentar criar as tabelas
        db.create_all()
        
        # Verificar se as colunas de timestamp existem, se não, adicionar
        try:
            # Tenta fazer uma consulta que use as colunas
            test = Usuario.query.first()
        except Exception as e:
            print(f"Erro ao acessar colunas de timestamp: {e}")
            print("Tentando adicionar colunas...")
            
            # Adiciona as colunas se não existirem
            with db.engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE usuario ADD COLUMN data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                    print("Coluna data_criacao adicionada.")
                except:
                    print("Coluna data_criacao já existe.")
                
                try:
                    conn.execute(text("ALTER TABLE usuario ADD COLUMN data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                    print("Coluna data_atualizacao adicionada.")
                except:
                    print("Coluna data_atualizacao já existe.")
                
                conn.commit()
        
        # Cria usuário admin padrão se não existir
        admin_existente = Usuario.query.filter_by(email='admin@portal.com').first()
        if not admin_existente:
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
        
        # Verifica se existem usuários de exemplo, se não, cria
        total_usuarios = Usuario.query.count()
        if total_usuarios <= 1:  # Se só tem o admin ou nenhum
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
            
            for usuario in usuarios_exemplo:
                existente = Usuario.query.filter_by(email=usuario.email).first()
                if not existente:
                    db.session.add(usuario)
            
            db.session.commit()
            print("Usuários de exemplo criados com sucesso!")
        
        print("Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")
        print("Tentando recriar o banco...")
        
        # Em caso de erro, recria o banco
        db.drop_all()
        db.create_all()
        
        # Cria usuário admin
        admin = Usuario(
            tipo='admin',
            nome='Administrador',
            email='admin@portal.com',
            senha=generate_password_hash('admin123'),
            telefone='(00) 00000-0000'
        )
        db.session.add(admin)
        db.session.commit()
        print("Banco de dados recriado e admin criado.")

# Rota para exibir fotos de perfil e currículos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)