import streamlit as st
from groq import Groq
import tempfile
import os
from pydub import AudioSegment

st.title("🎙️ 語音轉文字 (Speech to Text)")

st.info("幫助寫作業 の 工具 By Eason")

client = Groq(api_key="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")

# Max file size in MB (Groq limit is 25MB)
MAX_FILE_SIZE_MB = 20

uploaded_file = st.file_uploader("上傳音檔", type=["m4a", "mp3", "wav", "webm", "ogg", "flac"])

if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.success(f"✅ 已上傳：{uploaded_file.name} ({file_size_mb:.2f} MB)")
    
    if st.button("開始轉換"):
        with st.spinner("轉換中，請稍候..."):
            tmp_file_path = None
            chunk_paths = []
            try:
                # Save to temporary file
                suffix = f".{uploaded_file.name.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Check if file needs to be split
                if file_size_mb > MAX_FILE_SIZE_MB:
                    st.info(f"音檔較大 ({file_size_mb:.2f} MB)，將分段處理...")
                    
                    # Load audio file
                    audio = AudioSegment.from_file(tmp_file_path)
                    total_duration = len(audio)
                    
                    # Split into 3 chunks
                    chunk_duration = total_duration // 3
                    chunks = []
                    
                    for i in range(3):
                        start = i * chunk_duration
                        end = total_duration if i == 2 else (i + 1) * chunk_duration
                        chunk = audio[start:end]
                        
                        # Save chunk to temporary file
                        chunk_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                        chunk.export(chunk_path, format="mp3")
                        chunk_paths.append(chunk_path)
                        chunks.append(chunk_path)
                    
                    # Transcribe each chunk
                    all_text = []
                    all_segments = []
                    
                    for idx, chunk_path in enumerate(chunks):
                        st.write(f"處理第 {idx + 1}/3 段...")
                        with open(chunk_path, "rb") as audio_file:
                            transcription = client.audio.transcriptions.create(
                                file=audio_file,
                                model="whisper-large-v3",
                                temperature=0,
                                response_format="verbose_json",
                            )
                        
                        if hasattr(transcription, 'text'):
                            all_text.append(transcription.text)
                        
                        if hasattr(transcription, 'segments'):
                            all_segments.extend(transcription.segments)
                    
                    st.success("轉換完成！")
                    
                    # Display merged text
                    st.subheader("完整文字")
                    merged_text = " ".join(all_text)
                    st.write(merged_text)
                    
                    # Display all segments
                    if all_segments:
                        st.subheader("分段內容")
                        for segment in all_segments:
                            st.write(segment['text'])
                
                else:
                    # Process normally for small files
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
                # Clean up temporary files
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                
                for chunk_path in chunk_paths:
                    if os.path.exists(chunk_path):
                        os.unlink(chunk_path)