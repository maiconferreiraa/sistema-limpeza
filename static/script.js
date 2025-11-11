document.addEventListener('DOMContentLoaded', () => {

    // Seleciona o dropdown de serviços e o campo de valor
    const servicoSelect = document.getElementById('servico_id');
    const valorInput = document.getElementById('valor_pago');

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
});