import requests

def obter_clima(cidade):
    try:
        # 1. Pega as coordenadas (Latitude e Longitude) da cidade digitada
        url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={cidade}&count=1&language=pt"
        res_geo = requests.get(url_geo).json()
        
        if not res_geo.get("results"):
            return None, "Cidade não encontrada"
            
        lat = res_geo["results"][0]["latitude"]
        lon = res_geo["results"][0]["longitude"]
        
        # 2. Pega o clima atual e a temperatura nessas coordenadas
        url_weather = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res_weather = requests.get(url_weather).json()
        
        clima_atual = res_weather["current_weather"]
        temperatura = clima_atual["temperature"]
        codigo_clima = clima_atual["weathercode"]
        
        # 3. Traduz o código do clima para risco logístico
        # Tabela oficial da WMO (World Meteorological Organization)
        if codigo_clima in [0, 1, 2, 3]:
            condicao = "Céu Limpo / Pouco Nublado"
            fator_risco_clima = 1.0
        elif codigo_clima in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            condicao = "Chuva Ativa"
            fator_risco_clima = 1.6
        elif codigo_clima in [71, 73, 75, 95, 96, 99]:
            condicao = "Alerta: Tempestade/Neve"
            fator_risco_clima = 2.5
        else:
            condicao = "Clima Instável"
            fator_risco_clima = 1.3
            
        # Punição extra se estiver muito quente (afeta perecíveis)
        if temperatura > 30:
            condicao += " (Calor Intenso)"
            fator_risco_clima *= 1.4
            
        return {
            "temperatura": temperatura,
            "condicao": condicao,
            "fator_risco": fator_risco_clima
        }, None
        
    except Exception as e:
        return None, f"Erro de conexão: {e}"