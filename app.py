import streamlit as st
import os
import subprocess
import yt_dlp
from openai import OpenAI
import json
import math

st.set_page_config(page_title="Gerador de Cortes Virais Pro", layout="centered")

st.title("🎬 Divisor Completo de Podcast (1m15s por Parte)")
st.write("Divide o vídeo INTEIRO de ponta a ponta em blocos sequenciais de 1m15s com formato vertical (9:16), legendas dinâmicas e hashtags!")

api_key_input = st.text_input("Cole sua Chave da OpenAI (API Key):", type="password")
url_video = st.text_input("Cole o link do YouTube do podcast:")

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
        info = ydl.extract_info(url, download=True)
        duracao_total = info.get('duration', 0)
    return "video_baixado.mp4", duracao_total

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

def gerar_info_corte(client, texto_trecho, numero_parte):
    prompt = f"""
    Crie uma legenda persuasiva e hashtags virais para a PARTE {numero_parte} deste podcast.
    
    Trecho falado:
    "{texto_trecho}"
    
    Retorne ESTRITAMENTE um JSON no formato:
    {{
        "titulo": "🔥 PARTE {numero_parte}: [Título chamativo resumindo o trecho]",
        "legenda": "Confira a Parte {numero_parte} do podcast! Curta e siga para a próxima parte! 👇",
        "hashtags": "#podcast #parte{numero_parte} #cortes #viral"
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        conteudo = response.choices[0].message.content.strip()
        if conteudo.startswith("```json"):
            conteudo = conteudo.replace("```json", "").replace("```", "").strip()
        return json.loads(conteudo)
    except:
        return {
            "titulo": f"🔥 PARTE {numero_parte} DO PODCAST",
            "legenda": f"Assista à Parte {numero_parte}! Curta e siga para ver o restante!",
            "hashtags": "#podcast #cortes #viral"
        }

def formatar_tempo_srt(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    milisegs = int((segundos - int(segundos)) * 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegs:03d}"

def criar_legendas_srt(palavras, inicio_corte, fim_corte, srt_path):
    palavras_corte = [p for p in palavras if p['start'] >= inicio_corte and p['end'] <= fim_corte]
    with open(srt_path, "w", encoding="utf-8") as f:
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

def processar_video_efeitos(video_path, inicio, duracao, srt_path, output_path):
    filtro_video = "crop=ih*9/16:ih,scale=1080:1920,subtitles=" + srt_path + ":force_style='FontSize=24,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,BorderStyle=3,Alignment=2'"
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

if st.button("🚀 Dividir Vídeo Inteiro"):
    if not api_key_input or not url_video:
        st.error("Preencha a Chave da OpenAI e o Link do YouTube.")
        st.stop()
    
    try:
        client = OpenAI(api_key=api_key_input)
        
        # 1. Download
        arquivo_video, duracao_total = baixar_video_por_link(url_video)
        
        # 2. Extrai Áudio e Transcreve
        arquivo_audio = extrair_audio(arquivo_video)
        transcricao = transcrever_audio(client, arquivo_audio)
        
        # 3. Calcula quantidade de blocos de 75s (1m15s)
        tamanho_bloco = 75.0
        total_partes = math.ceil(duracao_total / tamanho_bloco)
        
        st.success(f"🎉 O vídeo possui {duracao_total:.0f}s e será dividido em {total_partes} partes de 1m15s sem perder nada!")
        
        # 4. Gera cada parte sequencialmente
        for parte in range(1, total_partes + 1):
            inicio = (parte - 1) * tamanho_bloco
            fim = min(parte * tamanho_bloco, duracao_total)
            duracao_atual = fim - inicio
            
            st.markdown("---")
            
            # Texto falado neste bloco para a IA resumir
            palavras_bloco = [p['word'] for p in transcricao.words if inicio <= p['start'] <= fim]
            texto_bloco = " ".join(palavras_bloco)
            
            # Gera info viral (Título da Parte X, Legenda, Hashtags)
            info = gerar_info_corte(client, texto_bloco, parte)
            st.subheader(info['titulo'])
            
            srt_path = f"legenda_{parte}.srt"
            output_corte = f"parte_{parte}.mp4"
            
            criar_legendas_srt(transcricao.words, inicio, fim, srt_path)
            
            with st.spinner(f"Processando e renderizando Parte {parte} de {total_partes}..."):
                processar_video_efeitos(arquivo_video, inicio, duracao_atual, srt_path, output_corte)
                
            st.video(output_corte)
            st.text_area(f"📝 Legenda / Bio (Parte {parte}):", info['legenda'], height=80)
            st.text_input(f"🏷️ Hashtags (Parte {parte}):", info['hashtags'])
            
            with open(output_corte, "rb") as file:
                st.download_button(
                    label=f"⬇️ Baixar Parte {parte}",
                    data=file,
                    file_name=f"parte_{parte}.mp4",
                    mime="video/mp4"
                )
                
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
