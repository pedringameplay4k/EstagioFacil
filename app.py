from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
import random

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

    sobre_mim = db.Column(db.Text, nullable=True)
    
    # NOVOS CAMPOS
    dados_bancarios = db.Column(db.String(200), nullable=True) # Ex: Nubank, Ag 0001, Cc 123-4
    cursos_extras = db.Column(db.Text, nullable=True) # Lista de cursos

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

class Candidatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    vaga_id = db.Column(db.Integer, db.ForeignKey('vaga.id'), nullable=False)
    data_aplicacao = db.Column(db.DateTime, server_default=db.func.now())
    
    usuario = db.relationship('Usuario', backref=db.backref('candidaturas', lazy=True))
    vaga = db.relationship('Vaga', backref=db.backref('candidaturas', lazy=True))
# --- Adicione junto com as outras rotas ---

@app.route('/setup/popular-banco')
def popular_banco():
    # 1. Cria ADMIN (Se não existir)
    if not Usuario.query.filter_by(email='admin@portal.com').first():
        admin = Usuario(tipo='admin', nome='Administrador', email='admin@portal.com', senha=generate_password_hash('admin123'))
        db.session.add(admin)

    # 2. Cria EMPRESAS Fakes
    empresas_dados = [
        {'nome': 'Google Brasil', 'email': 'vagas@google.com', 'cnpj': '00.000.000/0001-01', 'end': 'São Paulo, SP'},
        {'nome': 'Nubank', 'email': 'jobs@nubank.com.br', 'cnpj': '11.111.111/0001-01', 'end': 'Remoto / SP'},
        {'nome': 'Amazon AWS', 'email': 'aws@amazon.com', 'cnpj': '22.222.222/0001-01', 'end': 'Rio de Janeiro, RJ'}
    ]
    
    lista_empresas_objs = []
    for emp in empresas_dados:
        if not Usuario.query.filter_by(email=emp['email']).first():
            nova_empresa = Usuario(
                tipo='empresa',
                nome=emp['nome'],
                email=emp['email'],
                senha=generate_password_hash('123456'), # Senha padrão
                telefone='(11) 99999-9999',
                cnpj=emp['cnpj'],
                endereco=emp['end'],
                sobre_mim=f"Somos a {emp['nome']}, líderes em inovação e tecnologia."
            )
            db.session.add(nova_empresa)
            lista_empresas_objs.append(nova_empresa)
    
    db.session.commit() # Salva empresas para gerar os IDs

    # 3. Cria ALUNOS Fakes
    alunos_dados = [
        {'nome': 'Ana Silva', 'email': 'ana@aluno.com'},
        {'nome': 'Carlos Souza', 'email': 'carlos@aluno.com'},
        {'nome': 'Beatriz Lima', 'email': 'bia@aluno.com'}
    ]
    
    lista_alunos_objs = []
    for alu in alunos_dados:
        if not Usuario.query.filter_by(email=alu['email']).first():
            novo_aluno = Usuario(
                tipo='aluno',
                nome=alu['nome'],
                email=alu['email'],
                senha=generate_password_hash('123456'),
                telefone='(11) 98888-8888',
                cpf='123.456.789-00',
                cursos_extras='Inglês Avançado, Excel Intermediário, Python Básico',
                dados_bancarios='Nubank, Ag 0001, Conta 12345-6'
            )
            db.session.add(novo_aluno)
            lista_alunos_objs.append(novo_aluno)
            
    db.session.commit() # Salva alunos

    # Recarrega as empresas do banco para garantir que temos os objetos conectados
    empresas_no_banco = Usuario.query.filter_by(tipo='empresa').all()

    # 4. Cria VAGAS Fakes
    if empresas_no_banco:
        vagas_titulos = [
            ('Desenvolvedor Python Jr', 'ti', 'R$ 2.500'),
            ('Estágio em Marketing', 'mkt', 'R$ 1.200'),
            ('Assistente Administrativo', 'adm', 'R$ 1.500'),
            ('Analista de Dados Pleno', 'ti', 'R$ 4.000'),
            ('Estágio em RH', 'rh', 'R$ 1.300'),
            ('Engenheiro Civil Trainee', 'eng', 'R$ 3.000')
        ]
        
        for titulo, area, salario in vagas_titulos:
            # Escolhe uma empresa aleatória para ser dona da vaga
            empresa_dona = random.choice(empresas_no_banco)
            
            nova_vaga = Vaga(
                titulo=titulo,
                descricao=f"Vaga incrível para {titulo}. Necessário proatividade e vontade de aprender.\n\nRequisitos:\n- Conhecimento básico na área\n- Boa comunicação.",
                salario=salario,
                localizacao=empresa_dona.endereco,
                tipo=random.choice(['Presencial', 'Remoto', 'Híbrido']),
                area=area,
                beneficios="VR, VT, Plano de Saúde, Gympass",
                empresa_id=empresa_dona.id
            )
            db.session.add(nova_vaga)
        
        db.session.commit()

    # 5. Cria CANDIDATURAS Fakes (Alunos se aplicando)
    alunos_no_banco = Usuario.query.filter_by(tipo='aluno').all()
    vagas_no_banco = Vaga.query.all()
    
    if alunos_no_banco and vagas_no_banco:
        for aluno in alunos_no_banco:
            # Cada aluno se candidata a 2 vagas aleatórias
            vagas_escolhidas = random.sample(vagas_no_banco, k=min(2, len(vagas_no_banco)))
            for vaga in vagas_escolhidas:
                # Verifica se já existe para não duplicar
                if not Candidatura.query.filter_by(usuario_id=aluno.id, vaga_id=vaga.id).first():
                    cand = Candidatura(usuario_id=aluno.id, vaga_id=vaga.id)
                    db.session.add(cand)
        
        db.session.commit()

    flash('🤖 Bot executado! Banco de dados populado com sucesso.', 'success')
    return redirect(url_for('home'))

@app.route('/vaga/candidatar/<int:vaga_id>')
def candidatar_vaga(vaga_id):
    # 1. Verifica se está logado
    if 'user_id' not in session:
        flash('Faça login para se candidatar.', 'warning')
        return redirect(url_for('login'))
    
    # 2. Verifica se é Aluno (Empresa/Admin não candidata)
    if session['user_type'] != 'aluno':
        flash('Apenas alunos podem se candidatar a vagas.', 'error')
        return redirect(url_for('home'))
        
    # 3. Verifica se JÁ se candidatou antes (Evita duplicidade)
    ja_aplicou = Candidatura.query.filter_by(usuario_id=session['user_id'], vaga_id=vaga_id).first()
    if ja_aplicou:
        flash('Você já se candidatou para esta vaga!', 'info')
        return redirect(url_for('home'))
    
    # 4. Salva a candidatura
    nova_candidatura = Candidatura(usuario_id=session['user_id'], vaga_id=vaga_id)
    db.session.add(nova_candidatura)
    db.session.commit()
    
    flash('Candidatura enviada com sucesso! Boa sorte 🚀', 'success')
    return redirect(url_for('home'))        

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
        flash('Acesso restrito.', 'warning')
        return redirect(url_for('login'))
    
    # Busca candidaturas e dados do aluno
    minhas_candidaturas = Candidatura.query.filter_by(usuario_id=session['user_id']).order_by(Candidatura.data_aplicacao.desc()).all()
    aluno = Usuario.query.get(session['user_id'])
    
    return render_template('aluno_dashboard.html', 
                         user_name=session.get('user_name'),
                         candidaturas=minhas_candidaturas,
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
            usuario.dados_bancarios = request.form.get('dados_bancarios', usuario.dados_bancarios)
            usuario.cursos_extras = request.form.get('cursos_extras', usuario.cursos_extras)
            
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