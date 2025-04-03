import os
import streamlit as st
import google.generativeai as genai
import requests
import base64
import tempfile
from io import BytesIO
from dotenv import load_dotenv
import speech_recognition as sr
import uuid
import time 

def initialize_einstein_bot():
    # Load environment variables
    load_dotenv()
    
    # Configure Gemini API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("No Gemini API key found. Please set GEMINI_API_KEY in .env file.")
        st.stop()
    
    genai.configure(api_key=api_key)
    
    # Kid-Friendly Einstein's context
    einstein_context = """
You are AI Einstein, a friendly science buddy for kids! Your job is to make science super fun and easy to understand. 

How to Talk to Kids:
- Use simple words kids can understand
- Give short, exciting answers
- Make science sound like an amazing adventure
- Use fun examples and comparisons
- Be curious and playful
- Explain complex ideas in a way that makes kids go "Wow!"

Special Rules:
- Keep answers between 2-4 sentences
- Use kid-friendly language
- Get kids excited about learning
- Be patient and encouraging
- Always sound enthusiastic about science

You Are fluent in English and Korean. Answer with the language that the users start the conversation with.
    """
    
    # Initialize the model for chat (text-only)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Create or get chat session
    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat(history=[
            {
                "role": "user",
                "parts": [einstein_context]
            },
            {
                "role": "model",
                "parts": ["Hi there! I'm your science buddy Einstein. I'm ready to make learning about science the most awesome adventure ever!"]
            }
        ])
    
    return st.session_state.chat

def elevenlabs_tts(text, voice_id="pNInz6obpgDQGcFmaJgB", api_key=None):
    """Convert text to speech using ElevenLabs API"""
    if not api_key:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            st.error("No ElevenLabs API key found. Please set ELEVENLABS_API_KEY in .env file.")
            return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            st.error(f"ElevenLabs TTS Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"ElevenLabs TTS Exception: {str(e)}")
        return None

def nemesys_labs_tts(text, voice_id="einstein", api_key=None):
    """Convert text to speech using Nemesys Labs API"""
    if not api_key:
        api_key = os.getenv("NEMESYS_API_KEY")
        if not api_key:
            st.error("No Nemesys Labs API key found. Please set NEMESYS_API_KEY in .env file.")
            return None
    
    url = "https://api.nemesys.io/v1/tts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "text": text,
        "voice_id": voice_id,
        "speed": 1.0,
        "pitch": 1.0
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            audio_data = response.json().get("audio")
            if audio_data:
                audio_bytes = base64.b64decode(audio_data)
                return BytesIO(audio_bytes)
        st.error(f"Nemesys Labs TTS Error: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        st.error(f"Nemesys Labs TTS Exception: {str(e)}")
        return None

def google_cloud_tts(text, voice_name="en-US-Wavenet-F", api_key=None):
    """Convert text to speech using Google Cloud TTS API"""
    if not api_key:
        api_key = os.getenv("GOOGLE_TTS_API_KEY")
        if not api_key:
            st.error("No Google Cloud TTS API key found. Please set GOOGLE_TTS_API_KEY in .env file.")
            return None
    
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "input": {"text": text},
        "voice": {
            "languageCode": "en-US",
            "name": voice_name
        },
        "audioConfig": {"audioEncoding": "MP3"}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            audio_data = response.json().get("audioContent")
            if audio_data:
                audio_bytes = base64.b64decode(audio_data)
                return BytesIO(audio_bytes)
        st.error(f"Google Cloud TTS Error: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        st.error(f"Google Cloud TTS Exception: {str(e)}")
        return None

def google_speech_recognition(audio_bytes):
    """Recognize speech using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    # Create a unique filename in the user's home directory
    user_temp_dir = os.path.join(os.path.expanduser("~"), "einstein_temp")
    os.makedirs(user_temp_dir, exist_ok=True)
    temp_file_path = os.path.join(user_temp_dir, f"speech_{str(uuid.uuid4())}.wav")
    
    try:
        # Write audio data with explicit permissions
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(audio_bytes)
        
        # On Windows, ensure file is not read-only
        if os.name == 'nt':
            import stat
            os.chmod(temp_file_path, stat.S_IWRITE | stat.S_IREAD)
            
        with sr.AudioFile(temp_file_path) as source:
            audio_data = recognizer.record(source)
            
            try:
                text = recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                return "Could not understand audio"
            except sr.RequestError:
                return "Error connecting to Google Speech Recognition service"
    finally:
        # Clean up - remove the temp file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass  # If we can't remove it now, it's not critical
            
def whisper_asr(audio_bytes, api_key=None):
    """Recognize speech using OpenAI's Whisper API"""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("No OpenAI API key found. Please set OPENAI_API_KEY in .env file.")
            return "No API key available for speech recognition"
    
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Create a directory in the user's home folder for temporary files
    user_temp_dir = os.path.join(os.path.expanduser("~"), "einstein_temp")
    os.makedirs(user_temp_dir, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True, dir=user_temp_dir) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio.flush()
        
        try:
            with open(temp_audio.name, "rb") as audio_file:
                files = {
                    "file": audio_file,
                    "model": (None, "whisper-1")
                }
                response = requests.post(url, headers=headers, files=files)
                
                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    st.error(f"Whisper ASR Error: {response.status_code} - {response.text}")
                    return "Error with speech recognition service"
        except Exception as e:
            st.error(f"Whisper ASR Exception: {str(e)}")
            return "Error processing audio"

def get_einstein_response(chat, user_message):
    """Get Einstein's response to a user message"""
    try:
        # Get text response from Gemini
        response = chat.send_message(user_message)
        text_response = response.text
        
        return text_response
    except Exception as e:
        st.error(f"Error: {e}")
        return "Forgive me, but I cannot answer at this moment. Perhaps we should contemplate another question?"





def main():
    # Page configuration
    st.set_page_config(
        page_title="AI Einstein - Science Expert",
        page_icon="🧠",
        layout="centered"
    )
    
    # Header
    st.title("🧠 AI Einstein")
    st.markdown("Ask me about science, physics, philosophy, and the mysteries of the universe!")
    
    # Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Greetings! As I always said, 'The important thing is not to stop questioning.' What scientific curiosity shall we explore today?"}
        ]
    
    # Initialize Einstein bot
    chat = initialize_einstein_bot()
    
    # TTS/ASR Configuration
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg", width=250)
        st.markdown("## About AI Einstein")
        st.markdown("""
        This AI embodies the spirit of Albert Einstein to make scientific learning engaging and accessible.
        
        Perfect for:
        - Students learning physics and scientific concepts
        - Science enthusiasts curious about theoretical and applied science
        - Teachers looking for creative educational tools
        - Exploring complex scientific ideas
        
        Ask about relativity, quantum mechanics, scientific philosophy, or any scientific topic!
        """)
        
        st.markdown("## Voice Configuration")
        tts_provider = st.selectbox(
            "Text-to-Speech Provider",
            ["ElevenLabs", "Nemesys Labs", "Google Cloud TTS"]
        )
        
        asr_provider = st.selectbox(
            "Speech Recognition Provider",
            ["Google Speech Recognition", "OpenAI Whisper"]
        )
        
        # API keys input
        st.markdown("## API Keys Configuration")
        gemini_api_key = st.text_input("Gemini API Key", type="password", 
                                    help="Enter your Gemini API key if not using .env file")
        
        # Existing API key inputs for TTS and ASR providers
        if tts_provider == "ElevenLabs":
            elevenlabs_api_key = st.text_input("ElevenLabs API Key", type="password")
            if elevenlabs_api_key:
                os.environ["ELEVENLABS_API_KEY"] = elevenlabs_api_key
        elif tts_provider == "Nemesys Labs":
            nemesys_api_key = st.text_input("Nemesys Labs API Key", type="password")
            if nemesys_api_key:
                os.environ["NEMESYS_API_KEY"] = nemesys_api_key
        elif tts_provider == "Google Cloud TTS":
            google_tts_api_key = st.text_input("Google Cloud TTS API Key", type="password")
            if google_tts_api_key:
                os.environ["GOOGLE_TTS_API_KEY"] = google_tts_api_key
        
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
            if st.button("Reload with new API keys"):
                st.session_state.pop("chat", None)
                st.experimental_rerun()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Play audio for assistant messages
            if message["role"] == "assistant" and "audio" in message:
                st.audio(message["audio"], format="audio/mp3")
    
    # Voice input option
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎤 Record Voice Input"):
            with st.spinner("Listening..."):
                try:
                    # Record audio using microphone
                    recognizer = sr.Recognizer()
                    with sr.Microphone() as source:
                        st.info("Speak now...")
                        audio_data = recognizer.listen(source, timeout=5)
                        audio_bytes = audio_data.get_wav_data()
                    
                    # Process the recorded audio with selected ASR provider
                    if asr_provider == "Google Speech Recognition":
                        user_input = google_speech_recognition(audio_bytes)
                    else:  # OpenAI Whisper
                        user_input = whisper_asr(audio_bytes)
                    
                    if user_input and user_input != "Could not understand audio" and user_input != "Error with speech recognition service":
                        st.session_state.messages.append({"role": "user", "content": user_input})
                        with st.chat_message("user"):
                            st.markdown(user_input)
                        
                        # Get Einstein's response
                        with st.chat_message("assistant"):
                            with st.spinner("Contemplating..."):
                                response_text = get_einstein_response(chat, user_input)
                                st.markdown(response_text)
                                
                                # Generate speech from text
                                with st.spinner("Generating voice response..."):
                                    audio_stream = None
                                    if tts_provider == "ElevenLabs":
                                        audio_stream = elevenlabs_tts(response_text)
                                    elif tts_provider == "Nemesys Labs":
                                        audio_stream = nemesys_labs_tts(response_text)
                                    else:  # Google Cloud TTS
                                        audio_stream = google_cloud_tts(response_text)
                                    
                                    if audio_stream:
                                        st.audio(audio_stream, format="audio/mp3")
                                    
                                    # Store response in session state
                                    message_data = {
                                        "role": "assistant", 
                                        "content": response_text
                                    }
                                    
                                    if audio_stream:
                                        message_data["audio"] = audio_stream
                                    
                                    st.session_state.messages.append(message_data)
                except Exception as e:
                    st.error(f"Error during voice recording: {str(e)}")
    
    # Text input alternative
    user_input = st.chat_input("Ask AI Einstein about science, philosophy, or anything you're curious about...")
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Get Einstein's response
        with st.chat_message("assistant"):
            with st.spinner("Contemplating..."):
                response_text = get_einstein_response(chat, user_input)
                st.markdown(response_text)
                
                # Generate speech from text
                with st.spinner("Generating voice response..."):
                    audio_stream = None
                    if tts_provider == "ElevenLabs":
                        audio_stream = elevenlabs_tts(response_text)
                    elif tts_provider == "Nemesys Labs":
                        audio_stream = nemesys_labs_tts(response_text)
                    else:  # Google Cloud TTS
                        audio_stream = google_cloud_tts(response_text)
                
                    # Store response in session state
                    message_data = {
                        "role": "assistant", 
                        "content": response_text
                    }
                    
                    if audio_stream:
                        st.audio(audio_stream, format="audio/mp3")
                    
                    if audio_stream:
                        message_data["audio"] = audio_stream
                    
                    st.session_state.messages.append(message_data)

if __name__ == "__main__":
    main()