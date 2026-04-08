import pdfplumber
import easyocr
import numpy as np
import os
from pdf2image import convert_from_path

def obter_texto_pdf(caminho_pdf):
    texto = ""
    # 1. Tenta leitura digital
    with pdfplumber.open(caminho_pdf) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t: texto += t + "\n"
    
    # 2. Se for imagem, usa EasyOCR
    if len(texto.strip()) < 20:
        # Pega a pasta bin que está dentro da Library que você acabou de colar
        caminho_poppler = os.path.join(os.getcwd(), 'Library', 'bin')
        
        # Converte PDF para imagem usando o Poppler local
        paginas = convert_from_path(caminho_pdf, poppler_path=caminho_poppler)
        
        reader = easyocr.Reader(['pt'])
        for img in paginas:
            resultado = reader.readtext(np.array(img), detail=0)
            texto += " ".join(resultado) + "\n"
    return texto