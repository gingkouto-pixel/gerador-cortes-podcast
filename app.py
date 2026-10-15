import streamlit as st
import os
import subprocess
import yt_dlp
from openai import OpenAI
import json

st.set_page_config(page_title="Gerador de Cortes Virais", layout="centered")

st.title("🎬 Gerador de Cortes para Podcasts (1m15s)")
st.write("Insira o link do podcast (YouTube) e receba os clipes prontos para o TikTok!")

# Configura a chave da OpenAI direto na tela
api_key_input = st.text_input("Cole sua Chave da OpenAI (API Key):", type="password")

url_video = st.text_input("Cole o link do YouTube do podcast (até 5 horas):")
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

if st.button("🚀 Processar e Gerar Cortes"):
    if not api_key_input:
        st.error("Por favor, insira sua Chave da OpenAI.")
        st.stop()
    if not url_video:
        st.error("Por favor, insira o link do vídeo do YouTube.")
        st.stop()
    
    try:
        arquivo_video = baixar_video_por_link(url_video)
        st.success("Download concluído com sucesso!")
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
