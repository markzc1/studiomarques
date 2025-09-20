# Importa as bibliotecas necessárias, incluindo 'session'
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import urllib.parse
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agenda.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ATENÇÃO: Troque a senha secreta por uma de sua preferência
app.secret_key = '041004' 
db = SQLAlchemy(app)
# --- FIM DA CONFIGURAÇÃO ---


# --- MODELOS DO BANCO DE DADOS ---
class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_telefone = db.Column(db.String(20))
    servico = db.Column(db.String(100), nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    profissional_id = db.Column(db.String(50), nullable=False)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    profissional_id = db.Column(db.String(50), nullable=False)
# --- FIM DOS MODELOS ---


# Dicionário de profissionais
PROFISSIONAIS = {
    "anne": {"nome": "Anne Katleen", "profissao": "Nail Designer", "whatsapp": "556294804440"},
    "silesia": {"nome": "Silesia", "profissao": "Cabeleireira", "whatsapp": "556293407265"}
}


# --- ROTAS DO SITE ---
@app.route("/", methods=["GET", "POST"])
def index():
    # ... (Sua rota index continua exatamente a mesma)
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
                flash('Não é possível agendar em uma data passada. Por favor, escolha outra data.')
                return redirect(url_for('index'))
        except ValueError:
            flash('O formato da data que você digitou é inválido.')
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
        profissionais_com_servicos[key] = {
            "nome": info["nome"],
            "profissao": info["profissao"],
            "whatsapp": info["whatsapp"],
            "servicos": [s.nome for s in servicos_da_profissional]
        }
    return render_template("index.html", profissionais=profissionais_com_servicos)


# --- ROTAS DE AUTENTICAÇÃO (NOVAS) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == app.secret_key: # Compara com a senha definida na configuração
            session['logged_in'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Senha incorreta!', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Você saiu da sua conta.', 'success')
    return redirect(url_for('index'))


# --- ROTAS DO ADMIN (AGORA PROTEGIDAS) ---
@app.route("/admin", methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # ... (lógica de salvar agendamento) ...
        profissional_id = request.form.get('profissional')
        cliente_nome = request.form.get('cliente_nome')
        cliente_telefone = request.form.get('cliente_telefone')
        servico = request.form.get('servico')
        data_str = request.form.get('data')
        hora_str = request.form.get('hora')
        if servico == 'outro':
            servico = request.form.get('servico_outro')
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
        hora = datetime.strptime(hora_str, '%H:%M').time()
        novo_agendamento = Agendamento( profissional_id=profissional_id, cliente_nome=cliente_nome, cliente_telefone=cliente_telefone, servico=servico, data=data, hora=hora )
        db.session.add(novo_agendamento)
        db.session.commit()
        flash('Agendamento salvo com sucesso!', 'success')
        return redirect(url_for('admin'))

    agendamentos = Agendamento.query.order_by(Agendamento.data, Agendamento.hora).all()
    servicos_objetos = Servico.query.all()
    servicos_json = [ {'id': s.id, 'nome': s.nome, 'profissional_id': s.profissional_id} for s in servicos_objetos ]
    return render_template("admin.html", agendamentos=agendamentos, servicos=servicos_json)

@app.route('/admin/add_service', methods=['POST'])
def add_service():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    nome_servico = request.form.get('nome_servico')
    profissional_id = request.form.get('profissional_id')
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
    db.session.delete(servico_para_deletar)
    db.session.commit()
    flash('Serviço removido com sucesso!', 'success')
    return redirect(url_for('admin'))


# Bloco final para rodar o app
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)