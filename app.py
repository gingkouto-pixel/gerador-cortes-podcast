import streamlit as st
import os
import subprocess
import yt_dlp
from openai import OpenAI
import json

st.set_page_config(page_title="Gerador de Cortes Virais Pro (Ultra Retention)", layout="centered")

st.title("⚡ Gerador de Cortes Virais Pro (Ultra Retenção)")
st.write("Análise inteligente por ganchos, legendas animadas estilo Hormozi, enquadramento 9:16 e normalização de áudio!")

api_key_input = st.text_input("Cole sua Chave da OpenAI (API Key):", type="password")
url_video = st.text_input("Cole o link do YouTube do podcast:")
instrucao_usuario = st.text_area("Instruções adicionais para a IA:", "Foque nos momentos mais impactantes, polêmicos, inspiradores ou engraçados.")

def baixar_video_por_link(url):
    st.info("⬇️ Baixando o vídeo/áudio do link com alta qualidade...")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'video_baixado.mp4',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "video_baixado.mp4"

def extrair_audio(video_path):
    st.info("🎧 Extraindo e preparando áudio...")
    audio_path = "audio_extraido.mp3"
    cmd = f"ffmpeg -y -i {video_path} -vn -acodec libmp3lame -ar 16000 -ac 1 -b:a 64k {audio_path}"
    subprocess.run(cmd, shell=True, check=True)
    return audio_path

def transcrever_audio(client, audio_path):
    st.info("🎙️ Transcrevendo palavras exatas com o Whisper...")
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"]
        )
    return transcript

def identificar_cortes_inteligentes(client, transcricao_com_timestamps, instrucao):
    st.info("🧠 IA analisando ganchos de retenção e pausas de fala...")
    prompt = f"""
    Você é um editor de elite especializado em vídeos virais de altíssima retenção (TikTok, Reels, Shorts).
    Sua missão é selecionar os momentos de MAIOR IMPACTO da transcrição abaixo.

    REGRAS DE OURO:
    1. Cada corte deve ter entre 55 e 75 segundos.
    2. O corte deve COMEÇAR com um GANCHO FORTE (uma frase intrigante) e TERMINAR num final de raciocínio impactante ou suspense (cliffhanger).
    3. Nunca corte no meio de uma frase.
    4. Instrução do usuário: {instrucao}

    Transcrição com timestamps:
    {transcricao_com_timestamps}

    Retorne ESTRITAMENTE um JSON no formato de lista:
    [
        {{
            "inicio": 120.5,
            "fim": 185.2,
            "titulo": "🔥 O SEGREDO QUE NINGUÉM TE CONTA SOBRE SUCESSO",
            "legenda": "Concorda com este ponto de vista? Deixe sua opinião nos comentários e siga para mais conteúdos diários! 👇",
            "hashtags": "#podcast #sucesso #desenvolvimentopessoal #cortesvirais #mindset"
        }}
    ]
    Não inclua nada além do JSON.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    conteudo = response.choices[0].message.content.strip()
    if conteudo.startswith("```json"):
        conteudo = conteudo.replace("```json", "").replace("```", "").strip()
    return json.loads(conteudo)

def formatar_tempo_ass(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    centos = int((segundos - int(segundos)) * 100)
    return f"{horas}:{minutos:02d}:{segs:02d}.{centos:02d}"

def criar_legenda_ass_estilizada(palavras, inicio_corte, fim_corte, ass_path):
    # Gera arquivo .ass com estilos avançados (tipo Alex Hormozi)
    palavras_corte = [p for p in palavras if p['start'] >= inicio_corte and p['end'] <= fim_corte]
    
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,Impact,75,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,2,10,10,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header)
        grupo_tamanho = 2  # 2 palavras por bloco para dinamismo extremo
        for i in range(0, len(palavras_corte), grupo_tamanho):
            bloco = palavras_corte[i:i+grupo_tamanho]
            if not bloco:
                continue
            
            t_ini = max(0, bloco[0]['start'] - inicio_corte)
            t_fim = bloco[-1]['end'] - inicio_corte
            
            texto_formatado = ""
            for idx, p in enumerate(bloco):
                palavra = p['word'].strip().upper()
                # Destaca a primeira palavra do grupo em Amarelo Ouro e a segunda em Verde Neon
                cor = r"{\c&H0000FFFF&}" if idx == 0 else r"{\c&H0000FF00&}"
                texto_formatado += f"{cor}{palavra} "
                
            line = f"Dialogue: 0,{formatar_tempo_ass(t_ini)},{formatar_tempo_ass
