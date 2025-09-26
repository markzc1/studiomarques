# Importa as bibliotecas necessárias
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.parse
from datetime import datetime, timedelta

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agenda.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '041004' 
db = SQLAlchemy(app)
# --- FIM DA CONFIGURAÇÃO ---


# --- MODELOS DO BANCO DE DADOS ---
class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_nome = db.Column(db.String(100), nullable=True)
    cliente_telefone = db.Column(db.String(20), nullable=True)
    servico = db.Column(db.String(100), nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    duracao = db.Column(db.Integer, nullable=False)
    profissional_id = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='cliente')

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    profissional_id = db.Column(db.String(50), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    servico_preferencial = db.Column(db.String(100))
    profissional_id = db.Column(db.String(50), nullable=False)
# --- FIM DOS MODELOS ---


# Dicionário de profissionais (para nomes e detalhes)
PROFISSIONAIS = {
    "anne": {"nome": "Anne Katleen", "profissao": "Nail Designer", "whatsapp": "556294804440"},
    "silesia": {"nome": "Silesia", "profissao": "Cabeleireira", "whatsapp": "556293407265"}
}


# --- ROTAS DO SITE ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        profissional_key = request.form.get("profissional")
        servico = request.form.get("servico")
        data_str = request.form.get("data")
        hora = request.form.get("hora")
        mensagem = request.form.get("mensagem")
        try:
            data_agendamento = datetime.strptime(data_str, '%Y-%m-%d').date()
            hoje = datetime.now().date()
            if data_agendamento < hoje:
                flash('Não é possível agendar numa data passada. Por favor, escolha outra data.')
                return redirect(url_for('index'))
        except ValueError:
            flash('O formato da data que digitou é inválido.')
            return redirect(url_for('index'))
        profissional = PROFISSIONAIS.get(profissional_key, {})
        if not profissional:
            flash('Profissional não encontrada.')
            return redirect(url_for('index'))
        texto_mensagem = ( f"Olá, gostaria de agendar um horário com {profissional['nome']} ({profissional['profissao']}).\n" f"Nome: {nome}\n" f"Telefone: {telefone}\n" f"Serviço: {servico}\n" f"Data: {data_str}\n" f"Hora: {hora}" )
        if mensagem:
            texto_mensagem += f"\nMensagem adicional: {mensagem}"
        texto_codificado = urllib.parse.quote(texto_mensagem)
        numero_whatsapp = profissional["whatsapp"]
        url = f"https://wa.me/{numero_whatsapp}?text={texto_codificado}"
        return redirect(url)
    
    profissionais_com_servicos = {}
    for key, info in PROFISSIONAIS.items():
        servicos_da_profissional = Servico.query.filter_by(profissional_id=key).all()
        profissionais_com_servicos[key] = {**info, "servicos": [s.nome for s in servicos_da_profissional]}
    return render_template("index.html", profissionais=profissionais_com_servicos)


# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['logged_in'] = True
            session['user_id'] = user.username
            return redirect(url_for('admin'))
        else:
            flash('Utilizador ou senha incorretos.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Saiu da sua conta.', 'success')
    return redirect(url_for('index'))


# --- ROTAS DO ADMIN ---
@app.route("/admin", methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    profissional_id = session['user_id']
    
    if request.method == 'POST':
        cliente_nome = request.form.get('cliente_nome')
        cliente_telefone = request.form.get('cliente_telefone')
        servico = request.form.get('servico')
        data_str = request.form.get('data')
        hora_str = request.form.get('hora')
        duracao_str = request.form.get('duracao')
        
        if servico == 'outro':
            servico = request.form.get('servico_outro')

        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
            hora = datetime.strptime(hora_str, '%H:%M').time()
            duracao = int(duracao_str)
        except (ValueError, TypeError):
            flash('Dados de data, hora ou duração inválidos.', 'error')
            return redirect(url_for('admin'))
            
        horario_inicio = datetime.combine(data, hora)
        horario_fim = horario_inicio + timedelta(minutes=duracao)

        if horario_inicio.weekday() == 6:
            flash('Não é possível agendar aos domingos.', 'error')
            return redirect(url_for('admin'))
        
        if horario_inicio.weekday() == 5 and horario_inicio.hour >= 16:
            flash('Agendamentos aos sábados são permitidos somente até às 15:59.', 'error')
            return redirect(url_for('admin'))

        agendamentos_no_dia = Agendamento.query.filter_by(data=data, profissional_id=profissional_id).all()
        for agendamento_existente in agendamentos_no_dia:
            inicio_existente = datetime.combine(agendamento_existente.data, agendamento_existente.hora)
            fim_existente = inicio_existente + timedelta(minutes=agendamento_existente.duracao)
            
            if horario_inicio < fim_existente and horario_fim > inicio_existente:
                flash(f'ERRO: Conflito com agendamento das {inicio_existente.strftime("%H:%M")} às {fim_existente.strftime("%H:%M")}.', 'error')
                return redirect(url_for('admin'))
        
        novo_agendamento = Agendamento(
            profissional_id=profissional_id,
            cliente_nome=cliente_nome,
            cliente_telefone=cliente_telefone,
            servico=servico,
            data=data,
            hora=hora,
            duracao=duracao,
            tipo='cliente'
        )
        db.session.add(novo_agendamento)
        db.session.commit()
        
        flash('Agendamento salvo com sucesso!', 'success')
        return redirect(url_for('admin'))

    cliente_para_agendar = None
    cliente_id = request.args.get('cliente_id', type=int)
    if cliente_id:
        cliente_obj = Cliente.query.get(cliente_id)
        if cliente_obj and cliente_obj.profissional_id == profissional_id:
            cliente_para_agendar = { "nome": cliente_obj.nome, "telefone": cliente_obj.telefone, "servico_preferencial": cliente_obj.servico_preferencial }

    agendamentos = Agendamento.query.filter_by(profissional_id=profissional_id).order_by(Agendamento.data, Agendamento.hora).all()
    servicos_objetos = Servico.query.all()
    
    eventos_calendario = []
    for agendamento in agendamentos:
        inicio = datetime.combine(agendamento.data, agendamento.hora)
        fim = inicio + timedelta(minutes=agendamento.duracao)
        cor = '#c94a4a' if agendamento.tipo == 'compromisso' else '#968b60ff'
        eventos_calendario.append({
            'id': agendamento.id,
            'title': agendamento.servico if agendamento.tipo == 'compromisso' else f"{agendamento.cliente_nome} ({agendamento.servico})",
            'start': inicio.isoformat(),
            'end': fim.isoformat(),
            'backgroundColor': cor,
            'borderColor': cor,
            'extendedProps': {
                'tipo': agendamento.tipo,
                'cliente_nome': agendamento.cliente_nome,
                'cliente_telefone': agendamento.cliente_telefone,
                'servico': agendamento.servico,
                'data': agendamento.data.strftime('%d/%m/%Y'),
                'hora': agendamento.hora.strftime('%H:%M'),
                'profissional_nome': PROFISSIONAIS.get(agendamento.profissional_id, {}).get('nome', 'N/A')
            }
        })

    servicos_json = [ {'id': s.id, 'nome': s.nome, 'profissional_id': s.profissional_id} for s in servicos_objetos ]
    return render_template("admin.html", servicos=servicos_json, eventos_calendario=eventos_calendario, PROFISSIONAIS=PROFISSIONAIS, cliente_para_agendar=cliente_para_agendar)

@app.route('/admin/add_compromisso', methods=['POST'])
def add_compromisso():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    profissional_id = session['user_id']
    compromisso_nome = request.form.get('compromisso_nome')
    data_str = request.form.get('data')
    hora_str = request.form.get('hora')
    duracao_str = request.form.get('duracao')

    try:
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
        hora = datetime.strptime(hora_str, '%H:%M').time()
        duracao = int(duracao_str)
    except (ValueError, TypeError):
        flash('Dados de data, hora ou duração inválidos.', 'error')
        return redirect(url_for('admin'))
            
    horario_inicio = datetime.combine(data, hora)
    horario_fim = horario_inicio + timedelta(minutes=duracao)

    if horario_inicio.weekday() == 6:
        flash('Não é possível agendar aos domingos.', 'error')
        return redirect(url_for('admin'))
        
    if horario_inicio.weekday() == 5 and horario_inicio.hour >= 16:
        flash('Agendamentos aos sábados são permitidos somente até às 15:59.', 'error')
        return redirect(url_for('admin'))

    agendamentos_no_dia = Agendamento.query.filter_by(data=data, profissional_id=profissional_id).all()
    for agendamento_existente in agendamentos_no_dia:
        inicio_existente = datetime.combine(agendamento_existente.data, agendamento_existente.hora)
        fim_existente = inicio_existente + timedelta(minutes=agendamento_existente.duracao)
        
        if horario_inicio < fim_existente and horario_fim > inicio_existente:
            flash(f'ERRO: Conflito com agendamento das {inicio_existente.strftime("%H:%M")} às {fim_existente.strftime("%H:%M")}.', 'error')
            return redirect(url_for('admin'))

    novo_compromisso = Agendamento(
        profissional_id=profissional_id,
        cliente_nome=None,
        cliente_telefone=None,
        servico=compromisso_nome,
        data=data,
        hora=hora,
        duracao=duracao,
        tipo='compromisso'
    )
    db.session.add(novo_compromisso)
    db.session.commit()
    
    flash('Compromisso salvo na agenda!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add_service', methods=['POST'])
def add_service():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    nome_servico = request.form.get('nome_servico')
    profissional_id = session['user_id']
    if nome_servico and profissional_id:
        novo_servico = Servico(nome=nome_servico, profissional_id=profissional_id)
        db.session.add(novo_servico)
        db.session.commit()
        flash('Serviço adicionado com sucesso!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    servico_para_deletar = Servico.query.get_or_404(service_id)
    if servico_para_deletar.profissional_id == session['user_id']:
        db.session.delete(servico_para_deletar)
        db.session.commit()
        flash('Serviço removido com sucesso!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    agendamento_para_deletar = Agendamento.query.get_or_404(appointment_id)
    if agendamento_para_deletar.profissional_id == session['user_id']:
        db.session.delete(agendamento_para_deletar)
        db.session.commit()
        flash('Agendamento cancelado com sucesso!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/clientes')
def clientes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    profissional_id = session['user_id']
    lista_clientes = Cliente.query.filter_by(profissional_id=profissional_id).order_by(Cliente.nome).all()
    
    return render_template("clientes.html", clientes=lista_clientes, PROFISSIONAIS=PROFISSIONAIS)

@app.route('/admin/add_client', methods=['POST'])
def add_client():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    profissional_id = session['user_id']
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    servico = request.form.get('servico_preferencial')
    
    if nome and telefone:
        novo_cliente = Cliente(
            nome=nome,
            telefone=telefone,
            servico_preferencial=servico,
            profissional_id=profissional_id
        )
        db.session.add(novo_cliente)
        db.session.commit()
        flash('Cliente adicionada com sucesso!', 'success')
        
    return redirect(url_for('clientes'))

@app.route('/admin/delete_client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    cliente_para_deletar = Cliente.query.get_or_404(client_id)
    if cliente_para_deletar.profissional_id == session['user_id']:
        db.session.delete(cliente_para_deletar)
        db.session.commit()
        flash('Cliente removida com sucesso!', 'success')
        
    return redirect(url_for('clientes'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

