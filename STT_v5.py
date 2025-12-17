import streamlit as st
from groq import Groq
import tempfile
import os
from pydub import AudioSegment
import math
import time
import re

st.title("🎙️ 語音轉文字 (Speech to Text)")

st.info("幫助寫作業 の 工具 By Eason")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Max file size in MB (Groq limit is 25MB)
MAX_FILE_SIZE_MB = 10
# Max chunk duration in milliseconds (15 minutes)
CHUNK_DURATION_MS = 15 * 60 * 1000
# Max retries for rate limit
MAX_RETRIES = 5

def transcribe_with_retry(audio_file_path, status_placeholder=None):
    """Transcribe audio with automatic retry on rate limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    temperature=0,
                    response_format="verbose_json",
                )
            return transcription
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                # Extract wait time from error message
                wait_match = re.search(r'try again in (\d+)m?([\d.]+)?s?', error_msg, re.IGNORECASE)
                if wait_match:
                    minutes = int(wait_match.group(1)) if wait_match.group(1) and 'm' in error_msg else 0
                    seconds = float(wait_match.group(2)) if wait_match.group(2) else float(wait_match.group(1))
                    if 'm' in error_msg[wait_match.start():wait_match.end()]:
                        wait_time = minutes * 60 + seconds
                    else:
                        wait_time = seconds
                else:
                    wait_time = 60 * (attempt + 1)  # Default backoff
                
                wait_time = min(wait_time + 5, 300)  # Add buffer, max 5 min
                
                if status_placeholder:
                    status_placeholder.warning(f"⏳ 達到 API 速率限制，等待 {wait_time:.0f} 秒後重試（第 {attempt + 1}/{MAX_RETRIES} 次）...")
                
                time.sleep(wait_time)
            else:
                raise e
    
    raise Exception("已達最大重試次數，請稍後再試")

# ...existing code...

uploaded_file = st.file_uploader("上傳音檔", type=["m4a", "mp3", "wav", "webm", "ogg", "flac"])

if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.success(f"✅ 已上傳：{uploaded_file.name} ({file_size_mb:.2f} MB)")
    
    if st.button("開始轉換"):
        status_placeholder = st.empty()
        with st.spinner("轉換中，請稍候..."):
            tmp_file_path = None
            chunk_paths = []
            try:
                # Save to temporary file
                suffix = f".{uploaded_file.name.split('.')[-1]}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Load audio to check duration
                audio = AudioSegment.from_file(tmp_file_path)
                total_duration_ms = len(audio)
                total_duration_min = total_duration_ms / 1000 / 60
                
                # Check if file needs to be split (by size or duration)
                num_chunks = math.ceil(total_duration_ms / CHUNK_DURATION_MS)
                
                if file_size_mb > MAX_FILE_SIZE_MB or num_chunks > 1:
                    st.info(f"音檔長度：{total_duration_min:.1f} 分鐘，將分成 {num_chunks} 段處理（每段最多 15 分鐘）...")
                    
                    chunks = []
                    
                    for i in range(num_chunks):
                        start = i * CHUNK_DURATION_MS
                        end = min((i + 1) * CHUNK_DURATION_MS, total_duration_ms)
                        chunk = audio[start:end]
                        
                        # Save chunk to temporary file
                        chunk_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                        chunk.export(chunk_path, format="mp3")
                        chunk_paths.append(chunk_path)
                        chunks.append((chunk_path, start))  # Store start time for timestamp adjustment
                    
                    # Transcribe each chunk
                    all_text = []
                    all_segments = []
                    
                    for idx, (chunk_path, time_offset_ms) in enumerate(chunks):
                        st.write(f"處理第 {idx + 1}/{num_chunks} 段...")
                        transcription = transcribe_with_retry(chunk_path, status_placeholder)
                        
                        if hasattr(transcription, 'text'):
                            all_text.append(transcription.text)
                        
                        if hasattr(transcription, 'segments'):
                            # Adjust timestamps for each segment
                            time_offset_sec = time_offset_ms / 1000
                            for segment in transcription.segments:
                                adjusted_segment = dict(segment)
                                adjusted_segment['start'] = segment['start'] + time_offset_sec
                                adjusted_segment['end'] = segment['end'] + time_offset_sec
                                all_segments.append(adjusted_segment)
                    
                    st.success("轉換完成！")
                    
                    # Display merged text
                    st.subheader("完整文字")
                    merged_text = " ".join(all_text)
                    st.write(merged_text)
                    
                    # Display all segments with timestamps
                    if all_segments:
                        st.subheader("分段內容（含時間戳記）")
                        for segment in all_segments:
                            start_time = int(segment['start'])
                            mins, secs = divmod(start_time, 60)
                            st.write(f"[{mins:02d}:{secs:02d}] {segment['text']}")
                
                else:
                    # Process normally for small files
                    transcription = transcribe_with_retry(tmp_file_path, status_placeholder)
                    
                    st.success("轉換完成！")
                    
                    if hasattr(transcription, 'text'):
                        st.subheader("完整文字")
                        st.write(transcription.text)
                    
                    if hasattr(transcription, 'segments'):
                        st.subheader("分段內容（含時間戳記）")
                        for segment in transcription.segments:
                            start_time = int(segment['start'])
                            mins, secs = divmod(start_time, 60)
                            st.write(f"[{mins:02d}:{secs:02d}] {segment['text']}")
            
            except Exception as e:
                st.error(f"轉換失敗：{str(e)}")
            
            finally:
                # Clean up temporary files
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                
                for chunk_path in chunk_paths:
                    if isinstance(chunk_path, tuple):
                        chunk_path = chunk_path[0]
                    if os.path.exists(chunk_path):
                        os.unlink(chunk_path)
