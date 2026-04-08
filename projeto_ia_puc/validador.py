def validar_logistica(dados):
    # Pega o nome original, mas cria uma versão em MAIÚSCULO para facilitar a busca
    fornecedor_original = str(dados.get('fornecedor', ''))
    fornecedor_limpo = fornecedor_original.strip().upper()
    
    valor_bruto = dados.get('valor_total', 0)
    
    # Conversão inteligente de moeda que fizemos antes
    if isinstance(valor_bruto, (int, float)):
        valor = float(valor_bruto)
    else:
        v_str = str(valor_bruto).replace('R$', '').strip()
        if '.' in v_str and ',' in v_str:
            if v_str.rfind(',') > v_str.rfind('.'):
                v_str = v_str.replace('.', '').replace(',', '.')
            else:
                v_str = v_str.replace(',', '')
        elif ',' in v_str:
            v_str = v_str.replace(',', '.')
            
        try:
            valor = float(v_str)
        except ValueError:
            valor = 0.0
    
    # NOVA LÓGICA: Lista apenas as raízes dos nomes em MAIÚSCULO
    homologados_chaves = [
        "KALUNGA", 
        "AGROTECH", 
        "POMAR DO ZÉ"
    ]
    
    # O sistema agora checa se a palavra "POMAR DO ZÉ" está DENTRO do nome lido
    fornecedor_autorizado = False
    for chave in homologados_chaves:
        if chave in fornecedor_limpo:
            fornecedor_autorizado = True
            break
            
    if not fornecedor_autorizado:
        return "BLOQUEADA", f"Fornecedor '{fornecedor_original}' não reconhecido pelo compliance."
        
    if valor > 5000:
        return "REVISÃO", f"Valor acima do limite (R$ {valor:,.2f})."
    
    return "APROVADA", "Dados em conformidade."