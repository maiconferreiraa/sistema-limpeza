import os
import pdfkit
from flask import (Flask, render_template, request, redirect, url_for, 
                   g, flash, jsonify, make_response, session) # Adicionado 'session'
from datetime import datetime, date
from functools import wraps # Necessário para proteger rotas

# --- IMPORTAÇÕES DO FIREBASE ---
import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.cloud.firestore_v1.base_query import FieldFilter 

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-muito-segura' 

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
try:
    cred = credentials.Certificate("firebase-credentials.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase conectado!")
except Exception as e:
    print(f"ERRO CRÍTICO FIREBASE: {e}")
    db = None

# --- SISTEMA DE LOGIN E PROTEÇÃO ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_db():
    """Retorna a referência para a coleção exclusiva do usuário logado."""
    user_id = session['user_id']
    # O banco de dados agora fica dentro de: usuarios / {ID do Usuario} / ...
    return db.collection('usuarios').document(user_id)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login/session', methods=['POST'])
def login_session():
    """Recebe o token do JavaScript e cria a sessão no Python."""
    data = request.get_json()
    id_token = data.get('token')
    try:
        # Verifica se o token é válido lá no Google
        decoded_token = auth.verify_id_token(id_token)
        session['user_id'] = decoded_token['uid']
        session['user_email'] = decoded_token['email']
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ROTAS DO SISTEMA (Agora Protegidas) ---

@app.route('/', methods=['GET', 'POST'])
@login_required # <--- Proteção
def relatorios():
    user_ref = get_user_db() # <--- Pega o banco DO USUÁRIO
    
    data_inicio_default = date.today().replace(day=1).isoformat()
    data_fim_default = date.today().isoformat()
    
    data_inicio = request.form.get('data_inicio', data_inicio_default)
    data_fim = request.form.get('data_fim', data_fim_default)
    cliente_id_filtro = request.form.get('cliente_id_filtro', 'todos')

    # Query agora usa user_ref.collection(...)
    query = user_ref.collection('servicos_registrados').where(filter=FieldFilter('data', '>=', data_inicio)).where(filter=FieldFilter('data', '<=', data_fim))

    if cliente_id_filtro != 'todos':
        query = query.where(filter=FieldFilter('cliente_id', '==', cliente_id_filtro))

    servicos_docs = query.order_by('data', direction='DESCENDING').stream()
    servicos_registrados = [doc.to_dict() for doc in servicos_docs]
    total_periodo = sum(s['valor_pago'] for s in servicos_registrados)
    
    # Busca apenas clientes deste usuário
    clientes_docs = user_ref.collection('clientes').order_by('nome').stream()
    
    return render_template('relatorios.html', 
                           servicos=servicos_registrados, 
                           total=total_periodo,
                           clientes=clientes_docs,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           cliente_filtro=cliente_id_filtro)

@app.route('/registrar_servico', methods=['GET', 'POST'])
@login_required
def registrar_servico():
    user_ref = get_user_db()
    
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        servico_id = request.form['servico_id']
        data = request.form['data']
        valor_pago = request.form['valor_pago']
        
        cliente_doc = user_ref.collection('clientes').document(cliente_id).get()
        cliente_nome = cliente_doc.to_dict().get('nome', 'N/A') if cliente_doc.exists else "Inválido"
        
        servico_doc = user_ref.collection('tipos_servicos').document(servico_id).get()
        servico_nome = servico_doc.to_dict().get('nome', 'N/A') if servico_doc.exists else "Inválido"
        servico_categoria = servico_doc.to_dict().get('categoria', 'N/A') if servico_doc.exists else "N/A"

        novo_registro = {
            'cliente_id': cliente_id,
            'cliente_nome': cliente_nome,
            'servico_id': servico_id,
            'servico_nome': servico_nome,
            'servico_categoria': servico_categoria,
            'data': data,
            'valor_pago': float(valor_pago)
        }
        
        user_ref.collection('servicos_registrados').add(novo_registro)
        flash('Serviço registrado com sucesso!', 'success')
        return redirect(url_for('relatorios'))

    clientes_docs = user_ref.collection('clientes').order_by('nome').stream()
    servicos_docs = user_ref.collection('tipos_servicos').order_by('nome').stream()
    
    return render_template('registrar_servico.html', 
                           clientes=clientes_docs, 
                           tipos_servicos=servicos_docs,
                           data_hoje=date.today().isoformat())

@app.route('/clientes', methods=['GET', 'POST'])
@login_required
def gerenciar_clientes():
    user_ref = get_user_db()

    if request.method == 'POST':
        data = request.form.to_dict()
        user_ref.collection('clientes').add(data)
        flash(f"Cliente '{data['nome']}' cadastrado!", 'success')
        return redirect(url_for('gerenciar_clientes'))

    clientes_docs = user_ref.collection('clientes').order_by('nome').stream()
    return render_template('clientes.html', clientes=clientes_docs)

@app.route('/cliente/<string:cliente_id>')
@login_required
def cliente_detalhe(cliente_id):
    user_ref = get_user_db()
    
    cliente_doc = user_ref.collection('clientes').document(cliente_id).get()
    if not cliente_doc.exists:
        return "Cliente não encontrado", 404
        
    servicos_docs = user_ref.collection('servicos_registrados').where(filter=FieldFilter('cliente_id', '==', cliente_id)).order_by('data', direction='DESCENDING').stream()
    
    servicos_registrados = [doc.to_dict() for doc in servicos_docs]
    total_gasto = sum(s['valor_pago'] for s in servicos_registrados)
    
    return render_template('cliente_detalhe.html', 
                           cliente=cliente_doc.to_dict(), 
                           servicos=servicos_registrados, 
                           total_gasto=total_gasto)

@app.route('/cliente/editar/<string:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    user_ref = get_user_db()
    cliente_ref = user_ref.collection('clientes').document(cliente_id)
    
    if request.method == 'POST':
        cliente_ref.update(request.form.to_dict())
        flash("Cliente atualizado!", 'success')
        return redirect(url_for('gerenciar_clientes'))

    cliente = cliente_ref.get()
    return render_template('editar_cliente.html', cliente=cliente.to_dict(), cliente_id=cliente.id)

@app.route('/cliente/apagar/<string:cliente_id>', methods=['POST'])
@login_required
def apagar_cliente(cliente_id):
    user_ref = get_user_db()
    try:
        user_ref.collection('clientes').document(cliente_id).delete()
        flash("Cliente apagado.", 'success')
    except Exception as e:
        flash(f"Erro: {e}", 'danger')
    return redirect(url_for('gerenciar_clientes'))

@app.route('/servicos', methods=['GET', 'POST'])
@login_required
def gerenciar_servicos():
    user_ref = get_user_db()
    
    if request.method == 'POST':
        data = request.form.to_dict()
        
        categoria_selecionada = data.get('categoria')
        if categoria_selecionada == 'Outro':
            data['categoria'] = data.get('categoria_outra', 'Outro').strip()
        if 'categoria_outra' in data:
            del data['categoria_outra']
            
        data['preco_padrao'] = float(data['preco_padrao'])
        user_ref.collection('tipos_servicos').add(data)
        
        flash(f"Serviço '{data['nome']}' cadastrado!", 'success')
        return redirect(url_for('gerenciar_servicos'))

    servicos_docs = user_ref.collection('tipos_servicos').order_by('categoria').order_by('nome').stream()
    return render_template('servicos.html', servicos=servicos_docs)

@app.route('/servico/editar/<string:servico_id>', methods=['GET', 'POST'])
@login_required
def editar_servico(servico_id):
    user_ref = get_user_db()
    servico_ref = user_ref.collection('tipos_servicos').document(servico_id)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        if data.get('categoria') == 'Outro':
             data['categoria'] = data.get('categoria_outra', 'Outro').strip()
        if 'categoria_outra' in data: del data['categoria_outra']
        
        data['preco_padrao'] = float(data['preco_padrao'])
        servico_ref.update(data)
        flash("Serviço atualizado!", 'success')
        return redirect(url_for('gerenciar_servicos'))

    servico = servico_ref.get()
    return render_template('editar_servico.html', servico=servico.to_dict(), servico_id=servico.id)

@app.route('/servico/apagar/<string:servico_id>', methods=['POST'])
@login_required
def apagar_servico(servico_id):
    user_ref = get_user_db()
    try:
        user_ref.collection('tipos_servicos').document(servico_id).delete()
        flash("Serviço apagado.", 'success')
    except Exception as e:
        flash(f"Erro: {e}", 'danger')
    return redirect(url_for('gerenciar_servicos'))

@app.route('/relatorio/pdf')
@login_required
def gerar_relatorio_pdf():
    user_ref = get_user_db()
    
    data_inicio = request.args.get('data_inicio', date.today().replace(day=1).isoformat())
    data_fim = request.args.get('data_fim', date.today().isoformat())
    cliente_id_filtro = request.args.get('cliente_id_filtro')

    query = user_ref.collection('servicos_registrados').where(filter=FieldFilter('data', '>=', data_inicio)).where(filter=FieldFilter('data', '<=', data_fim))

    cliente_nome_filtro = "Todos"
    if cliente_id_filtro and cliente_id_filtro != 'todos':
        query = query.where(filter=FieldFilter('cliente_id', '==', cliente_id_filtro))
        cliente = user_ref.collection('clientes').document(cliente_id_filtro).get()
        if cliente.exists:
            cliente_nome_filtro = cliente.to_dict().get('nome')
            
    servicos_docs = query.order_by('data', direction='DESCENDING').stream()
    servicos_registrados = [doc.to_dict() for doc in servicos_docs]
    total_periodo = sum(s['valor_pago'] for s in servicos_registrados)

    html_para_pdf = render_template('relatorio_pdf.html',
                                    servicos=servicos_registrados,
                                    total=total_periodo,
                                    data_inicio=data_inicio,
                                    data_fim=data_fim,
                                    cliente_filtro=cliente_nome_filtro,
                                    data_emissao=datetime.now().strftime("%d/%m/%Y às %H:%M"))
    
    pdf = pdfkit.from_string(html_para_pdf, False, options={"enable-local-file-access": ""})
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio.pdf'
    return response

@app.route('/api/get_servico_preco/<string:servico_id>')
@login_required
def get_servico_preco(servico_id):
    user_ref = get_user_db()
    doc = user_ref.collection('tipos_servicos').document(servico_id).get()
    if doc.exists:
        return jsonify({'preco_padrao': doc.to_dict().get('preco_padrao')})
    return jsonify({'erro': 'Serviço não encontrado'}), 404

if __name__ == '__main__':
    app.run(debug=True)