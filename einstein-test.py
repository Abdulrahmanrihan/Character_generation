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

def elevenlabs_tts(text, voice_id="pNInz6obpgDQGcFmaJgB"):
    """Convert text to speech using ElevenLabs API"""
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

def process_voice_input():
    with st.spinner("Listening..."):
        try:
            # Record audio using microphone
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                st.info("Speak now...")
                audio_data = recognizer.listen(source, timeout=5)
                audio_bytes = audio_data.get_wav_data()
            
            # Process the recorded audio with Google Speech Recognition
            user_input = google_speech_recognition(audio_bytes)
            
            if user_input and user_input != "Could not understand audio" and user_input != "Error connecting to Google Speech Recognition service":
                return user_input
            else:
                return None
        except Exception as e:
            st.error(f"Error during voice recording: {str(e)}")
            return None

def process_user_input(user_input, chat):
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
                
                # Generate speech from text using ElevenLabs
                with st.spinner("Generating voice response..."):
                    audio_stream = elevenlabs_tts(response_text)
                
                    # Store response in session state
                    message_data = {
                        "role": "assistant", 
                        "content": response_text
                    }
                    
                    if audio_stream:
                        st.audio(audio_stream, format="audio/mp3")
                        message_data["audio"] = audio_stream
                    
                    st.session_state.messages.append(message_data)

def main():
    # Page configuration
    st.set_page_config(
        page_title="AI Einstein - Science Expert",
        page_icon="🧠",
        layout="centered"
    )
    
    # Custom CSS to create a sticky footer and ensure proper order
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Set up the page structure */
    .main .block-container {
        display: flex;
        flex-direction: column;
        padding-bottom: 80px; /* Make room for the fixed input area */
        height: 100vh;
    }
    
    /* Style the sticky input container */
    .stTextInput, .stButton {
        position: fixed;
        bottom: 0;
        right: 0;
        left: 0;
        padding: 1rem;
        background-color: white;
        z-index: 999;
        border-top: 1px solid #eee;
    }
    
    /* Style the input area to position buttons side by side */
    .fixed-input-container {
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: white;
        padding: 10px;
    }
    
    /* Add bottom margin to messages to prevent them from being hidden */
    .stChatMessage {
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
    
    # Sidebar with information
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
    
    # Main chat area - This needs to appear BEFORE the input area in the DOM
    chat_area = st.container()
    with chat_area:
        # Display all previous messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # Play audio for assistant messages
                if message["role"] == "assistant" and "audio" in message:
                    st.audio(message["audio"], format="audio/mp3")
    
    # Add empty space to push content up
    st.markdown("<div style='height: 100px'></div>", unsafe_allow_html=True)
                
    # Fixed input area at the bottom
    # This creates a container that will be styled via CSS to stick to the bottom
    input_area = st.container()
    with input_area:
        # Create a div with a specific class we can target with CSS
        st.markdown("<div class='fixed-input-container'></div>", unsafe_allow_html=True)
        
        # Create columns for input field and voice button in a horizontal layout
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.chat_input("Ask AI Einstein about science, philosophy, or anything you're curious about...")
        
        with col2:
            voice_button = st.button("🎤", key="voice_input_button")
    
    # Process voice input if button is clicked
    if voice_button:
        voice_text = process_voice_input()
        if voice_text:
            process_user_input(voice_text, chat)
    
    # Process text input
    if user_input:
        process_user_input(user_input, chat)

if __name__ == "__main__":
    main()