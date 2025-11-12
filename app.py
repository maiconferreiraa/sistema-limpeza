import os
import pdfkit
from flask import (Flask, render_template, request, redirect, url_for, 
                   g, flash, jsonify, make_response)
from datetime import datetime, date

# --- IMPORTAÇÕES DO FIREBASE ---
import firebase_admin
from firebase_admin import credentials, firestore
# Importação corrigida para a nova sintaxe de filtros
from google.cloud.firestore_v1.base_query import FieldFilter 

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-muito-segura' 

# --- CONFIGURAÇÃO DO BANCO DE DADOS (FIREBASE) ---
try:
    cred = credentials.Certificate("firebase-credentials.json")
    
    # Verifica se o app já foi inicializado (necessário para o reloader)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        print("Conectado ao Firebase pela primeira vez!")
    else:
        print("Firebase já conectado (reloader).")
    
    db = firestore.client() # Este é o nosso 'db'

except FileNotFoundError:
    print("-----------------------------------------------------------------")
    print("ERRO CRÍTICO: Arquivo 'firebase-credentials.json' não encontrado.")
    print("-----------------------------------------------------------------")
    db = None
except Exception as e:
    print(f"ERRO AO CONECTAR NO FIREBASE: {e}")
    db = None

# --- Rota Principal: Relatórios ---

@app.route('/', methods=['GET', 'POST'])
def relatorios():
    """Página principal: Relatórios de serviços prestados."""
    
    data_inicio_default = date.today().replace(day=1).isoformat()
    data_fim_default = date.today().isoformat()
    
    data_inicio = request.form.get('data_inicio', data_inicio_default)
    data_fim = request.form.get('data_fim', data_fim_default)
    cliente_id_filtro = request.form.get('cliente_id_filtro', 'todos')

    # Query base no Firestore (SINTAXE CORRIGIDA)
    query = db.collection('servicos_registrados').where(filter=FieldFilter('data', '>=', data_inicio)).where(filter=FieldFilter('data', '<=', data_fim))

    if cliente_id_filtro != 'todos':
        # SINTAXE CORRIGIDA
        query = query.where(filter=FieldFilter('cliente_id', '==', cliente_id_filtro))

    # Executa a query
    servicos_docs = query.order_by('data', direction='DESCENDING').stream()
    
    servicos_registrados = [doc.to_dict() for doc in servicos_docs]
    total_periodo = sum(s['valor_pago'] for s in servicos_registrados)
    
    # Buscar clientes para o dropdown
    clientes_docs = db.collection('clientes').order_by('nome').stream()
    
    return render_template('relatorios.html', 
                           servicos=servicos_registrados, 
                           total=total_periodo,
                           clientes=clientes_docs,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           cliente_filtro=cliente_id_filtro)

# --- Rota: Registrar Serviço ---

@app.route('/registrar_servico', methods=['GET', 'POST'])
def registrar_servico():
    """Página para lançar um novo serviço prestado."""
    
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        servico_id = request.form['servico_id']
        data = request.form['data']
        valor_pago = request.form['valor_pago']
        
        # --- Lógica de Desnormalização (NoSQL) ---
        cliente_doc = db.collection('clientes').document(cliente_id).get()
        cliente_nome = cliente_doc.to_dict().get('nome', 'Cliente Deletado') if cliente_doc.exists else "ID Cliente Inválido"
        
        servico_doc = db.collection('tipos_servicos').document(servico_id).get()
        servico_nome = servico_doc.to_dict().get('nome', 'Serviço Deletado') if servico_doc.exists else "ID Serviço Inválido"

        novo_registro = {
            'cliente_id': cliente_id,
            'cliente_nome': cliente_nome,
            'servico_id': servico_id,
            'servico_nome': servico_nome,
            'data': data,
            'valor_pago': float(valor_pago)
        }
        
        db.collection('servicos_registrados').add(novo_registro)
        
        flash('Serviço registrado com sucesso!', 'success')
        return redirect(url_for('relatorios'))

    # GET: Carrega os dados para os dropdowns
    clientes_docs = db.collection('clientes').order_by('nome').stream()
    servicos_docs = db.collection('tipos_servicos').order_by('nome').stream()
    
    return render_template('registrar_servico.html', 
                           clientes=clientes_docs, 
                           tipos_servicos=servicos_docs,
                           data_hoje=date.today().isoformat())

# --- Rota: Gerenciar Clientes (CRUD) ---

@app.route('/clientes', methods=['GET', 'POST'])
def gerenciar_clientes():
    """Página para listar e cadastrar novos clientes."""
    
    if request.method == 'POST':
        data = request.form.to_dict()
        db.collection('clientes').add(data)
        
        flash(f"Cliente '{data['nome']}' cadastrado com sucesso!", 'success')
        return redirect(url_for('gerenciar_clientes'))

    clientes_docs = db.collection('clientes').order_by('nome').stream()
    return render_template('clientes.html', clientes=clientes_docs)

@app.route('/cliente/<string:cliente_id>')
def cliente_detalhe(cliente_id):
    """Página de detalhes e histórico de um cliente."""
    
    cliente_doc = db.collection('clientes').document(cliente_id).get()
    if not cliente_doc.exists:
        return "Cliente não encontrado", 404
        
    # SINTAXE CORRIGIDA
    servicos_docs = db.collection('servicos_registrados').where(filter=FieldFilter('cliente_id', '==', cliente_id)).order_by('data', direction='DESCENDING').stream()
    
    servicos_registrados = [doc.to_dict() for doc in servicos_docs]
    total_gasto = sum(s['valor_pago'] for s in servicos_registrados)
    
    return render_template('cliente_detalhe.html', 
                           cliente=cliente_doc.to_dict(), 
                           servicos=servicos_registrados, 
                           total_gasto=total_gasto)

@app.route('/cliente/editar/<string:cliente_id>', methods=['GET', 'POST'])
def editar_cliente(cliente_id):
    """Página para editar um cliente existente."""
    
    cliente_ref = db.collection('clientes').document(cliente_id)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        cliente_ref.update(data)
        
        flash(f"Cliente '{data['nome']}' atualizado com sucesso!", 'success')
        return redirect(url_for('gerenciar_clientes'))

    cliente = cliente_ref.get()
    if not cliente.exists:
        flash("Cliente não encontrado.", 'danger')
        return redirect(url_for('gerenciar_clientes'))
        
    return render_template('editar_cliente.html', cliente=cliente.to_dict(), cliente_id=cliente.id)

@app.route('/cliente/apagar/<string:cliente_id>', methods=['POST'])
def apagar_cliente(cliente_id):
    """Rota para apagar um cliente (ignora o histórico)."""
    # Esta é a versão sem trava de segurança, como você pediu
    try:
        db.collection('clientes').document(cliente_id).delete()
        flash("Cliente apagado com sucesso.", 'success')
    except Exception as e:
        flash(f"Ocorreu um erro ao apagar: {e}", 'danger')
    
    return redirect(url_for('gerenciar_clientes'))

# --- Rota: Gerenciar Tipos de Serviço (CRUD) ---

@app.route('/servicos', methods=['GET', 'POST'])
def gerenciar_servicos():
    """Página para cadastrar e listar os *tipos* de serviço."""
    
    if request.method == 'POST':
        data = request.form.to_dict()
        data['preco_padrao'] = float(data['preco_padrao'])
        db.collection('tipos_servicos').add(data)
        
        flash(f"Serviço '{data['nome']}' cadastrado com sucesso!", 'success')
        return redirect(url_for('gerenciar_servicos'))

    # Sintaxe corrigida (sem 'ASC')
    servicos_docs = db.collection('tipos_servicos').order_by('categoria').order_by('nome').stream()
    return render_template('servicos.html', servicos=servicos_docs)

@app.route('/servico/editar/<string:servico_id>', methods=['GET', 'POST'])
def editar_servico(servico_id):
    """Página para editar um tipo de serviço."""
    
    servico_ref = db.collection('tipos_servicos').document(servico_id)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        data['preco_padrao'] = float(data['preco_padrao'])
        servico_ref.update(data)
        
        flash(f"Serviço '{data['nome']}' atualizado com sucesso!", 'success')
        return redirect(url_for('gerenciar_servicos'))

    servico = servico_ref.get()
    if not servico.exists:
        flash("Serviço não encontrado.", 'danger')
        return redirect(url_for('gerenciar_servicos'))
        
    return render_template('editar_servico.html', servico=servico.to_dict(), servico_id=servico.id)

@app.route('/servico/apagar/<string:servico_id>', methods=['POST'])
def apagar_servico(servico_id):
    """Rota para apagar um tipo de serviço (ignora o histórico)."""
    # Esta é a versão sem trava de segurança, como você pediu
    try:
        db.collection('tipos_servicos').document(servico_id).delete()
        flash("Serviço apagado com sucesso.", 'success')
    except Exception as e:
        flash(f"Ocorreu um erro ao apagar: {e}", 'danger')
    
    return redirect(url_for('gerenciar_servicos'))

# --- Rota: Gerar PDF ---

@app.route('/relatorio/pdf')
def gerar_relatorio_pdf():
    """Gera o relatório em PDF com os filtros aplicados."""
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    cliente_id_filtro = request.args.get('cliente_id_filtro')

    if not data_inicio:
        data_inicio = date.today().replace(day=1).isoformat()
    if not data_fim:
        data_fim = date.today().isoformat()
        
    # SINTAXE CORRIGIDA
    query = db.collection('servicos_registrados').where(filter=FieldFilter('data', '>=', data_inicio)).where(filter=FieldFilter('data', '<=', data_fim))

    cliente_nome_filtro = "Todos"
    if cliente_id_filtro and cliente_id_filtro != 'todos':
        # SINTAXE CORRIGIDA
        query = query.where(filter=FieldFilter('cliente_id', '==', cliente_id_filtro))
        cliente = db.collection('clientes').document(cliente_id_filtro).get()
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
    nome_arquivo = f"relatorio_{data_inicio}_a_{data_fim}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
    
    return response

# --- API Helper (para o formulário de registro) ---

@app.route('/api/get_servico_preco/<string:servico_id>')
def get_servico_preco(servico_id):
    """API que retorna o preço padrão de um serviço."""
    doc = db.collection('tipos_servicos').document(servico_id).get()
    if doc.exists:
        return jsonify({'preco_padrao': doc.to_dict().get('preco_padrao')})
    return jsonify({'erro': 'Serviço não encontrado'}), 404

# --- Inicialização ---
if __name__ == '__main__':
    app.run(debug=True)