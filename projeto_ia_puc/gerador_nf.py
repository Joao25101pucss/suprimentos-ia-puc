from PIL import Image, ImageDraw, ImageFont
import datetime

def criar_imagem_nf(fornecedor, cnpj, lista_produtos, valor_total):
    # Cria uma tela em branco (Proporção de folha A4)
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        fonte_titulo = ImageFont.truetype("arial.ttf", 36)
        fonte_texto = ImageFont.truetype("arial.ttf", 24)
        fonte_destaque = ImageFont.truetype("arialbd.ttf", 30) # Arial Bold
    except:
        fonte_titulo = None
        fonte_texto = None
        fonte_destaque = None

    data_atual = datetime.datetime.now().strftime("%d/%m/%Y")
    
    # Desenhando as bordas
    draw.rectangle([(20, 20), (780, 980)], outline="black", width=4)
    draw.line([(20, 100), (780, 100)], fill="black", width=2)
    draw.line([(520, 20), (520, 100)], fill="black", width=2) 
    
    # Cabeçalho
    draw.text((40, 45), "DANFE - Documento Auxiliar", fill="black", font=fonte_destaque)
    draw.text((540, 30), "SÉRIE: 1", fill="black", font=fonte_texto)
    draw.text((540, 60), "Nº 000.999.123", fill="black", font=fonte_texto)
    
    # Dados do Emissor
    y = 130
    draw.text((40, y), "DADOS DO EMISSOR:", fill="black", font=fonte_destaque)
    draw.text((40, y+40), f"Razão Social: {fornecedor}", fill="black", font=fonte_texto)
    draw.text((40, y+80), f"CNPJ: {cnpj}", fill="black", font=fonte_texto)
    draw.text((40, y+120), f"Data de Emissão: {data_atual}", fill="black", font=fonte_texto)
    
    draw.line([(20, y+170), (780, y+170)], fill="black", width=2)
    
    # Loop para imprimir Múltiplos Produtos na Nota
    draw.text((40, y+200), "DESCRIÇÃO DOS PRODUTOS / SERVIÇOS", fill="black", font=fonte_destaque)
    
    y_prod = y + 250
    # Limita a 10 linhas para não "vazar" da folha A4
    for i, item in enumerate(lista_produtos[:10]):
        texto_item = f"- {item['quantidade']}x {item['produto']}"
        # Formata o valor unitário
        texto_valor = f"R$ {item['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        draw.text((40, y_prod), texto_item, fill="black", font=fonte_texto)
        draw.text((600, y_prod), texto_valor, fill="black", font=fonte_texto)
        y_prod += 35
        
    if len(lista_produtos) > 10:
        draw.text((40, y_prod), "... (mais itens constam no romaneio original)", fill="black", font=fonte_texto)
    
    # Rodapé com o Valor
    draw.line([(20, 850), (780, 850)], fill="black", width=2)
    valor_formatado = f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    draw.text((40, 880), f"VALOR TOTAL DA NOTA:", fill="black", font=fonte_destaque)
    draw.text((500, 875), valor_formatado, fill="red", font=fonte_titulo)
    
    # Salva a imagem
    caminho_arquivo = "nota_simulada_gerada.png"
    img.save(caminho_arquivo)
    
    return caminho_arquivo, data_atual