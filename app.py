import streamlit as st
import os
import subprocess
import yt_dlp
from openai import OpenAI
import json

st.set_page_config(page_title="Gerador de Cortes Virais Pro", layout="centered")

st.title("🎬 Gerador de Cortes Virais com Retenção Máxima")
st.write("Baixa do YouTube, corta em formato vertical (9:16), gera legendas dinâmicas e entrega títulos e hashtags virais!")

# Configura a chave da OpenAI direto na tela
api_key_input = st.text_input("Cole sua Chave da OpenAI (API Key):", type="password")

url_video = st.text_input("Cole o link do YouTube do podcast:")
instrucao_usuario = st.text_area("O que deseja nos cortes?", "Encontre os momentos mais chamativos, polêmicos ou engraçados.")

def baixar_video_por_link(url):
    st.info("⬇️ Baixando o vídeo/áudio do link...")
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
    st.info("🎧 Extraindo áudio do vídeo...")
    audio_path = "audio_extraido.mp3"
    cmd = f"ffmpeg -y -i {video_path} -vn -acodec libmp3lame -ar 16000 -ac 1 -b:a 64k {audio_path}"
    subprocess.run(cmd, shell=True, check=True)
    return audio_path

def transcrever_audio(client, audio_path):
    st.info("🎙️ Transcrevendo áudio com Whisper da OpenAI...")
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"]
        )
    return transcript

def identificar_cortes(client, transcricao_texto, instrucao):
    st.info("🧠 Analisando os melhores momentos com GPT...")
    prompt = f"""
    Você é um especialista em retenção e vídeos virais (TikTok, Reels, Shorts).
    Analise a transcrição abaixo e selecione os melhores momentos (entre 60 e 75 segundos cada).
    Instrução do usuário: {instrucao}

    Transcrição:
    {transcricao_texto}

    Para cada corte, crie:
    1. 'inicio': tempo de início em segundos (número).
    2. 'fim': tempo de fim em segundos (número).
    3. 'titulo': Título magnético e chamativo.
    4. 'legenda': Legenda persuasiva com chamada para ação (CTA).
    5. 'hashtags': Hashtags virais.

    Retorne ESTRITAMENTE um JSON válido no formato de lista:
    [
        {{
            "inicio": 120.5,
            "fim": 195.0,
            "titulo": "🔥 O SEGREDOS DOS MILIONÁRIOS",
            "legenda": "Concordas? Comenta aqui embaixo! 👇",
            "hashtags": "#podcast #cortes #viral"
        }}
    ]
    Não inclua nenhum texto fora do JSON.
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

def formatar_tempo_srt(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    milisegs = int((segundos - int(segundos)) * 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegs:03d}"

def criar_legendas_srt(palavras, inicio_corte, fim_corte, srt_path):
    # Filtra palavras do intervalo do corte e reajusta o tempo relativas ao início do corte
    palavras_corte = [p for p in palavras if p['start'] >= inicio_corte and p['end'] <= fim_corte]
    
    with open(srt_path, "w", encoding="utf-8") as f:
        # Agrupa de 3 em 3 palavras para uma leitura dinâmica ideal na tela
        grupo_tamanho = 3
        for i in range(0, len(palavras_corte), grupo_tamanho):
            bloco = palavras_corte[i:i+grupo_tamanho]
            if not bloco:
                continue
            t_ini = bloco[0]['start'] - inicio_corte
            t_fim = bloco[-1]['end'] - inicio_corte
            if t_ini < 0: t_ini = 0
            
            texto_bloco = " ".join([p['word'] for p in bloco]).upper()
            
            f.write(f"{i//grupo_tamanho + 1}\n")
            f.write(f"{formatar_tempo_srt(t_ini)} --> {formatar_tempo_srt(t_fim)}\n")
            f.write(f"{texto_bloco}\n\n")

def processar_video_efeitos(video_path, inicio, fim, srt_path, output_path):
    duracao = fim - inicio
    # Filtro FFmpeg avançado: 
    # 1. Corta o trecho (-ss e -t)
    # 2. Converte para formato vertical 9:16 (crop inteligente centralizado) com redimensionamento para 1080x1920
    # 3. Queima as legendas dinâmicas estilizadas no centro do ecrã com destaque
    filtro_video = "crop=ih*9/16:ih,scale=1080:1920,subtitles=" + srt_path + ":force_style='FontSize=24,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,BackColour=&H80000000&,BorderStyle=3,Outline=2,Shadow=1,Alignment=2'"
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(inicio),
        "-i", video_path,
        "-t", str(duracao),
        "-vf", filtro_video,
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        output_path
    ]
    subprocess.run(cmd, check=True)

if st.button("🚀 Processar e Gerar Cortes Virais"):
    if not api_key_input:
        st.error("Por favor, insira sua Chave da OpenAI.")
        st.stop()
    if not url_video:
        st.error("Por favor, insira o link do vídeo do YouTube.")
        st.stop()
    
    try:
        client = OpenAI(api_key=api_key_input)
        
        # 1. Download
        arquivo_video = baixar_video_por_link(url_video)
        
        # 2. Extrai Áudio
        arquivo_audio = extrair_audio(arquivo_video)
        
        # 3. Transcreve Áudio com marcas por palavra
        transcricao = transcrever_audio(client, arquivo_audio)
        
        # Prepara texto corrido para o GPT analisar
        texto_transcrito = " ".join([p['word'] for p in transcricao.words])
        
        # 4. Identifica cortes
        cortes = identificar_cortes(client, texto_transcrito, instrucao_usuario)
        
        st.success(f"🎉 Foram identificados {len(cortes)} cortes virais!")
        
        # 5. Processamento final (Vertical 9:16 + Legendas Dinâmicas)
        for i, corte in enumerate(cortes):
            st.markdown("---")
            st.subheader(f"Corte {i+1}: {corte['titulo']}")
            
            srt_path = f"legenda_{i+1}.srt"
            output_corte = f"corte_viral_{i+1}.mp4"
            
            criar_legendas_srt(transcricao.words, corte['inicio'], corte['fim'], srt_path)
            
            with st.spinner(f"Renderizando efeitos e formato vertical no Corte {i+1}..."):
                processar_video_efeitos(arquivo_video, corte['inicio'], corte['fim'], srt_path, output_corte)
                
            st.video(output_corte)
            
            st.text_area(f"📝 Legenda / Bio sugerida (Corte {i+1}):", corte['legenda'], height=100)
            st.text_input(f"🏷️ Hashtags sugeridas (Corte {i+1}):", corte['hashtags'])
            
            with open(output_corte, "rb") as file:
                st.download_button(
                    label=f"⬇️ Baixar Vídeo Viral {i+1}",
                    data=file,
                    file_name=f"corte_viral_{i+1}.mp4",
                    mime="video/mp4"
                )
                
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
