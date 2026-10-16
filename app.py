import streamlit as st
import os
import subprocess
from openai import OpenAI
import json

st.set_page_config(page_title="Gerador de Cortes Virais Pro (Ultra Retention)", layout="centered")

st.title("⚡ Gerador de Cortes Virais Pro (Upload Direto)")
st.write("Carregue o ficheiro de vídeo do seu podcast e receba os cortes verticais (9:16) com legendas dinâmicas estilo Hormozi e hashtags virais!")

# Configuração da API Key
api_key_input = st.text_input("Cole sua Chave da OpenAI (API Key):", type="password")

# Upload direto do ficheiro de vídeo
uploaded_file = st.file_uploader("Escolha ou arraste o ficheiro de vídeo do podcast (.mp4, .mov, .mkv):", type=["mp4", "mov", "mkv"])

instrucao_usuario = st.text_area("Instruções adicionais para a IA:", "Foque nos momentos mais impactantes, polêmicos, inspiradores ou engraçados.")

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
        grupo_tamanho = 2
        for i in range(0, len(palavras_corte), grupo_tamanho):
            bloco = palavras_corte[i:i+grupo_tamanho]
            if not bloco:
                continue
            
            t_ini = max(0, bloco[0]['start'] - inicio_corte)
            t_fim = bloco[-1]['end'] - inicio_corte
            
            texto_formatado = ""
            for idx, p in enumerate(bloco):
                palavra = p['word'].strip().upper()
                cor = r"{\c&H0000FFFF&}" if idx == 0 else r"{\c&H0000FF00&}"
                texto_formatado += f"{cor}{palavra} "
                
            tempo_inicio_str = formatar_tempo_ass(t_ini)
            tempo_fim_str = formatar_tempo_ass(t_fim)
            line = f"Dialogue: 0,{tempo_inicio_str},{tempo_fim_str},Hormozi,,0,0,0,,{texto_formatado.strip()}\n"
            f.write(line)

def processar_video_ultra_retencao(video_path, inicio, fim, ass_path, output_path):
    duracao = fim - inicio
    filtro_video = f"crop=ih*9/16:ih,scale=1080:1920,ass={ass_path}"
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(inicio),
        "-i", video_path,
        "-t", str(duracao),
        "-vf", filtro_video,
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, check=True)

if st.button("🚀 Gerar Cortes de Alta Retenção"):
    if not api_key_input:
        st.error("Por favor, insira sua Chave da OpenAI.")
        st.stop()
    if uploaded_file is None:
        st.error("Por favor, selecione ou faça upload de um ficheiro de vídeo.")
        st.stop()
        
    try:
        client = OpenAI(api_key=api_key_input)
        
        # Salva o vídeo enviado no servidor
        arquivo_
