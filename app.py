import streamlit as st
import os
import subprocess
import yt_dlp
from openai import OpenAI
import json

st.set_page_config(page_title="Gerador de Cortes Virais", layout="centered")

st.title("🎬 Gerador de Cortes para Podcasts (1m15s)")
st.write("Insira o link do podcast (YouTube) e receba os clipes com títulos, legendas e hashtags virais para o TikTok/Reels!")

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
            timestamp_granularities=["segment"]
        )
    return transcript

def identificar_cortes(client, transcricao, instrucao):
    st.info("🧠 Analisando os melhores momentos, legendas e hashtags com GPT...")
    prompt = f"""
    Você é um especialista em crescimento e estratégia de conteúdo viral (TikTok, Instagram Reels, YouTube Shorts).
    Análise a transcrição do podcast abaixo e selecione os melhores momentos (entre 60 e 75 segundos cada).
    Instrução adicional do usuário: {instrucao}

    Transcrição com marcas de tempo:
    {transcricao}

    Para cada corte encontrado, crie também:
    1. 'titulo': Um título chamativo com gancho viral.
    2. 'legenda': Uma bio/legenda curta, persuasiva e com chamada para ação (CTA) para o post.
    3. 'hashtags': Uma lista com 5 a 10 hashtags virais e muito relevantes ao tema.

    Retorne ESTRITAMENTE um JSON válido no seguinte formato:
    [
        {{
            "inicio": 120.5,
            "fim": 195.0,
            "titulo": "🔥 ELE REVELOU O SEGREDO DOS MILIONÁRIOS!",
            "legenda": "Concordas com esta opinião sobre negócios? Comenta aqui embaixo a tua opinião e segue o perfil para mais cortes diários! 👇",
            "hashtags": "#podcast #cortes #negocios #sucesso #viral #empreendedorismo"
        }}
    ]
    Importante: 'inicio' e 'fim' devem ser em segundos (números). Não inclua nenhum outro texto fora do JSON.
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

def cortar_video(video_path, inicio, fim, output_path):
    duracao = fim - inicio
    cmd = f"ffmpeg -y -ss {inicio} -i {video_path} -t {duracao} -c:v libx264 -c:a aac {output_path}"
    subprocess.run(cmd, shell=True, check=True)

if st.button("🚀 Processar e Gerar Cortes"):
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
        
        # 3. Transcreve Áudio
        transcricao = transcrever_audio(client, arquivo_audio)
        
        # Prepara segmentos de texto com timestamps
        texto_com_tempo = ""
        for seg in transcricao.segments:
            texto_com_tempo += f"[{seg['start']:.1f}s -> {seg['end']:.1f}s] {seg['text']}\n"
            
        # 4. Identifica os Melhores Momentos + Legendas + Hashtags
        cortes = identificar_cortes(client, texto_com_tempo, instrucao_usuario)
        
        st.success(f"🎉 Foram identificados {len(cortes)} cortes virais!")
        
        # 5. Gera os Arquivos e Exibe as Informações Virais
        for i, corte in enumerate(cortes):
            st.markdown("---")
            st.subheader(f"Corte {i+1}: {corte['titulo']}")
            
            output_corte = f"corte_{i+1}.mp4"
            
            with st.spinner(f"Gerando vídeo do Corte {i+1}..."):
                cortar_video(arquivo_video, corte['inicio'], corte['fim'], output_corte)
                
            st.video(output_corte)
            
            # Exibe Legenda e Hashtags prontas para copiar
            st.text_area(f"📝 Legenda / Bio sugerida (Corte {i+1}):", corte['legenda'], height=100)
            st.text_input(f"🏷️ Hashtags sugeridas (Corte {i+1}):", corte['hashtags'])
            
            with open(output_corte, "rb") as file:
                st.download_button(
                    label=f"⬇️ Baixar Vídeo {i+1}",
                    data=file,
                    file_name=f"corte_{i+1}.mp4",
                    mime="video/mp4"
                )
                
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
