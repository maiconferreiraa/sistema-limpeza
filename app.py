import os
import pdfkit
import base64
import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import (Flask, render_template, request, redirect, url_for, 
                   g, flash, jsonify, make_response, session)
from datetime import datetime, date
from functools import wraps
from google.cloud.firestore_v1.base_query import FieldFilter 

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-muito-segura' 

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
try:
    cred = credentials.Certificate("firebase-credentials.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase conectado com sucesso!")
except Exception as e:
    print(f"ERRO CRÍTICO FIREBASE: {e}")
    db = None

# --- DECORATOR DE PROTEÇÃO DE ROTA ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_db():
    """Referência para a coleção do usuário logado no Firestore."""
    user_id = session['user_id']
    return db.collection('usuarios').document(user_id)

@app.context_processor
def inject_empresa():
    """Injeta dados do emissor em todos os templates para ficarem como padrão."""
    if 'user_id' in session:
        try:
            user_ref = get_user_db()
            config = user_ref.collection('configuracoes').document('perfil').get()
            if config.exists:
                return {'empresa': config.to_dict()}
        except:
            pass
    return {'empresa': {'nome_empresa': 'Sistema de Limpeza', 'logo_base64': None}}

# --- AUTENTICAÇÃO ---

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login/session', methods=['POST'])
def login_session():
    data = request.get_json()
    id_token = data.get('token')
    try:
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

# --- CONFIGURAÇÃO DO EMISSOR (DADOS DEFAULT) ---

@app.route('/config/empresa', methods=['POST'])
@login_required
def salvar_config_empresa():
    user_ref = get_user_db()
    dados_config = {
        'nome_empresa': request.form.get('nome_empresa'),
        'instagram': request.form.get('instagram'),
        'whatsapp': request.form.get('whatsapp'),
        'documento': request.form.get('documento'), # CPF/CNPJ
        'endereco': request.form.get('endereco')    # Endereço Fixo
    }

    logo_file = request.files.get('logo_empresa')
    if logo_file and logo_file.filename != '':
        logo_read = logo_file.read()
        logo_base64 = base64.b64encode(logo_read).decode('utf-8')
        dados_config['logo_base64'] = f"data:image/png;base64,{logo_base64}"

    user_ref.collection('configuracoes').document('perfil').set(dados_config, merge=True)
    flash("Dados do Emissor atualizados e salvos como padrão!", "success")
    return redirect(request.referrer)

# --- CLIENTES ---

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
    servicos_docs = user_ref.collection('servicos_registrados').where(filter=FieldFilter('cliente_id', '==', cliente_id)).order_by('data', direction='DESCENDING').stream()
    servicos_registrados = [doc.to_dict() for doc in servicos_docs]
    total_gasto = sum(s['valor_pago'] for s in servicos_registrados)
    return render_template('cliente_detalhe.html', cliente=cliente_doc.to_dict(), servicos=servicos_registrados, total_gasto=total_gasto)

@app.route('/cliente/editar/<string:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    user_ref = get_user_db()
    cliente_ref = user_ref.collection('clientes').document(cliente_id)
    if request.method == 'POST':
        cliente_ref.update(request.form.to_dict())
        flash("Dados do cliente atualizados!", 'success')
        return redirect(url_for('gerenciar_clientes'))
    cliente = cliente_ref.get()
    return render_template('editar_cliente.html', cliente=cliente.to_dict(), cliente_id=cliente.id)

@app.route('/cliente/apagar/<string:cliente_id>', methods=['POST'])
@login_required
def apagar_cliente(cliente_id):
    user_ref = get_user_db()
    user_ref.collection('clientes').document(cliente_id).delete()
    flash("Cliente removido com sucesso.", 'success')
    return redirect(url_for('gerenciar_clientes'))

# --- SERVIÇOS ---

@app.route('/servicos', methods=['GET', 'POST'])
@login_required
def gerenciar_servicos():
    user_ref = get_user_db()
    if request.method == 'POST':
        data = request.form.to_dict()
        data['preco_padrao'] = float(data['preco_padrao'])
        user_ref.collection('tipos_servicos').add(data)
        flash('Serviço adicionado ao catálogo!', 'success')
        return redirect(url_for('gerenciar_servicos'))
    servicos_docs = user_ref.collection('tipos_servicos').order_by('nome').stream()
    return render_template('servicos.html', servicos=servicos_docs)

@app.route('/servico/editar/<string:servico_id>', methods=['GET', 'POST'])
@login_required
def editar_servico(servico_id):
    user_ref = get_user_db()
    servico_ref = user_ref.collection('tipos_servicos').document(servico_id)
    if request.method == 'POST':
        data = request.form.to_dict()
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
    user_ref.collection('tipos_servicos').document(servico_id).delete()
    flash("Serviço removido.", 'success')
    return redirect(url_for('gerenciar_servicos'))

# --- REGISTRO DE VENDAS/SERVIÇOS ---

@app.route('/registrar_servico', methods=['GET', 'POST'])
@login_required
def registrar_servico():
    user_ref = get_user_db()
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        servico_id = request.form['servico_id']
        c_doc = user_ref.collection('clientes').document(cliente_id).get().to_dict()
        s_doc = user_ref.collection('tipos_servicos').document(servico_id).get().to_dict()

        novo_registro = {
            'cliente_id': cliente_id,
            'cliente_nome': c_doc.get('nome'),
            'servico_nome': s_doc.get('nome'),
            'servico_categoria': s_doc.get('categoria'),
            'data': request.form['data'],
            'valor_pago': float(request.form['valor_pago'])
        }
        user_ref.collection('servicos_registrados').add(novo_registro)
        flash('Serviço registrado no faturamento!', 'success')
        return redirect(url_for('relatorios'))

    clientes = user_ref.collection('clientes').order_by('nome').stream()
    servicos = user_ref.collection('tipos_servicos').order_by('nome').stream()
    return render_template('registrar_servico.html', clientes=clientes, tipos_servicos=servicos, data_hoje=date.today().isoformat())

# --- ORÇAMENTOS (PDF) ---

@app.route('/orcamentos', methods=['GET'])
@login_required
def gerenciar_orcamentos():
    user_ref = get_user_db()
    clientes = user_ref.collection('clientes').order_by('nome').stream()
    servicos = user_ref.collection('tipos_servicos').order_by('nome').stream()
    return render_template('orcamentos.html', clientes=clientes, servicos=servicos)

@app.route('/orcamento/gerar_pdf', methods=['POST'])
@login_required
def gerar_orcamento_pdf():
    user_ref = get_user_db()
    cliente_id = request.form.get('cliente_id')
    servicos_ids = request.form.getlist('servicos[]')
    quantidades = request.form.getlist('quantidades[]')
    
    orcamento_id = datetime.now().strftime("%Y%m%d%H%M") 
    cliente_doc = user_ref.collection('clientes').document(cliente_id).get().to_dict()
    empresa_doc = user_ref.collection('configuracoes').document('perfil').get().to_dict() or {}

    itens = []
    total = 0
    for i in range(len(servicos_ids)):
        s_doc = user_ref.collection('tipos_servicos').document(servicos_ids[i]).get().to_dict()
        sub = s_doc['preco_padrao'] * int(quantidades[i])
        total += sub
        itens.append({'nome': s_doc['nome'], 'qtd': quantidades[i], 'unit': s_doc['preco_padrao'], 'sub': sub})

    html = render_template('orcamento_pdf.html', 
                           cliente=cliente_doc, 
                           itens=itens, 
                           total=total, 
                           validade=request.form.get('validade', '7'), 
                           forma_pagamento=request.form.get('forma_pagamento', 'A combinar'), 
                           observacoes=request.form.get('observacoes', ''), 
                           orcamento_id=orcamento_id, 
                           empresa=empresa_doc, 
                           data_emissao=datetime.now().strftime("%d/%m/%Y"))
    
    pdf = pdfkit.from_string(html, False, options={"enable-local-file-access": ""})
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=orcamento_{orcamento_id}.pdf'
    return response

# --- RELATÓRIOS ---

@app.route('/', methods=['GET', 'POST'])
@login_required
def relatorios():
    user_ref = get_user_db()
    data_inicio = request.form.get('data_inicio', date.today().replace(day=1).isoformat())
    data_fim = request.form.get('data_fim', date.today().isoformat())
    
    query = user_ref.collection('servicos_registrados').where(filter=FieldFilter('data', '>=', data_inicio)).where(filter=FieldFilter('data', '<=', data_fim))
    servicos = [doc.to_dict() for doc in query.order_by('data', direction='DESCENDING').stream()]
    total = sum(s['valor_pago'] for s in servicos)
    clientes = user_ref.collection('clientes').order_by('nome').stream()
    
    return render_template('relatorios.html', servicos=servicos, total=total, clientes=clientes, data_inicio=data_inicio, data_fim=data_fim)

@app.route('/relatorio/pdf')
@login_required
def gerar_relatorio_pdf():
    user_ref = get_user_db()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    empresa_doc = user_ref.collection('configuracoes').document('perfil').get().to_dict() or {}

    query = user_ref.collection('servicos_registrados').where(filter=FieldFilter('data', '>=', data_inicio)).where(filter=FieldFilter('data', '<=', data_fim))
    servicos = [doc.to_dict() for doc in query.order_by('data', direction='DESCENDING').stream()]
    total = sum(s['valor_pago'] for s in servicos)

    html = render_template('relatorio_pdf.html', servicos=servicos, total=total, data_inicio=data_inicio, 
                           data_fim=data_fim, empresa=empresa_doc, data_emissao=datetime.now().strftime("%d/%m/%Y %H:%M"))
    
    pdf = pdfkit.from_string(html, False, options={"enable-local-file-access": ""})
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=relatorio.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)