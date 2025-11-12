document.addEventListener('DOMContentLoaded', () => {

    // --- LÓGICA 1: Auto-preencher preço (Página /registrar_servico) ---
    
    // Seleciona o dropdown de serviços e o campo de valor
    const servicoSelect = document.getElementById('servico_id');
    const valorInput = document.getElementById('valor_pago');

    // Se o dropdown de serviço existir nesta página...
    if (servicoSelect) {
        // Adiciona um "ouvinte" que dispara quando o serviço é trocado
        servicoSelect.addEventListener('change', () => {
            
            // Pega o <option> que foi selecionado
            const selectedOption = servicoSelect.options[servicoSelect.selectedIndex];
            
            // Pega o preço que guardamos no 'data-preco'
            const precoPadrao = selectedOption.getAttribute('data-preco');

            if (precoPadrao) {
                // Se achou um preço, preenche o campo de valor
                valorInput.value = parseFloat(precoPadrao).toFixed(2);
            } else {
                // Se for a opção "Selecione...", limpa o campo
                valorInput.value = '';
            }
        });
    }


    // --- LÓGICA 2: Mostrar campo "Outra Categoria" (Página /servicos) ---
    
    // Procura os elementos do formulário de /servicos
    const categoriaSelect = document.getElementById('categoria');
    const categoriaOutraDiv = document.getElementById('campo_categoria_outra');
    const categoriaOutraInput = document.getElementById('categoria_outra');

    // Se o <select> de categoria existir nesta página...
    if (categoriaSelect) {
        
        // Adiciona um "ouvinte" de mudança
        categoriaSelect.addEventListener('change', () => {
            
            // Se o valor selecionado for "Outro"
            if (categoriaSelect.value === 'Outro') {
                categoriaOutraDiv.style.display = 'block'; // Mostra o campo de texto
                categoriaOutraInput.required = true;       // Torna-o obrigatório
            } else {
                // Se for qualquer outra opção
                categoriaOutraDiv.style.display = 'none';  // Esconde o campo
                categoriaOutraInput.required = false;      // Deixa de ser obrigatório
                categoriaOutraInput.value = '';            // Limpa o valor (caso o usuário mude de ideia)
            }
        });
    }
    
}); // Fim do 'DOMContentLoaded'