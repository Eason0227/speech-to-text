import streamlit as st
from groq import Groq
import tempfile
import os

st.title("🎙️ 語音轉文字 (Speech to Text)")

# User input for API key
api_key = st.text_input("請輸入 Groq API Key", type="password", help="請輸入您的 Groq API 金鑰")

if api_key:
    client = Groq(api_key=api_key)

    uploaded_file = st.file_uploader("上傳音檔", type=["m4a", "mp3", "wav", "webm", "ogg", "flac"])

    if uploaded_file is not None:
        st.success(f"✅ 已上傳：{uploaded_file.name}")
        
        if st.button("開始轉換"):
            with st.spinner("轉換中，請稍候..."):
                tmp_file_path = None
                try:
                    # Save to temporary file
                    suffix = f".{uploaded_file.name.split('.')[-1]}"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # Open and send the file
                    with open(tmp_file_path, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            file=audio_file,
                            model="whisper-large-v3",
                            temperature=0,
                            response_format="verbose_json",
                        )
                    
                    st.success("轉換完成！")
                    
                    # Display full text
                    if hasattr(transcription, 'text'):
                        st.subheader("完整文字")
                        st.write(transcription.text)
                    
                    # Display segments
                    if hasattr(transcription, 'segments'):
                        st.subheader("分段內容")
                        for segment in transcription.segments:
                            st.write(segment['text'])
                
                except Exception as e:
                    st.error(f"轉換失敗：{str(e)}")
                
                finally:
                    # Clean up temporary file
                    if tmp_file_path and os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)
else:
    st.warning("⚠️ 請先輸入 API Key")