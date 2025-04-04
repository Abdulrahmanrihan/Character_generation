import os
import streamlit as st
import google.generativeai as genai
import requests
import base64
import tempfile
import json
import time
import streamlit.components.v1 as components
from io import BytesIO
from dotenv import load_dotenv
import speech_recognition as sr
import uuid

# Set page configuration
st.set_page_config(page_title="AI Einstein Avatar", page_icon="🧠", layout="wide")

# Load environment variables
load_dotenv()

# Sidebar configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg", width=250)
    st.markdown("## AI Einstein Configuration")
    
    # API Keys section
    st.markdown("### API Keys")
    
    # Gemini API key for Einstein bot
    gemini_api_key = st.text_input("Gemini API Key", value="", type="password",
                                help="Enter your Gemini API key")
    if gemini_api_key:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
    
    # HeyGen API key for avatar
    heygen_api_key = st.text_input("HeyGen API Key", value="", type="password",
                               help="Enter your HeyGen API key")
    
    # Avatar configuration
    st.markdown("### Avatar Settings")
    avatar_id = st.text_input("Avatar ID", value="Ann_Therapist_public")
    voice_id = st.text_input("Voice ID", value="1bd001e7e50f421d891986aad5158bc8")
    
    # Voice recognition configuration
    st.markdown("### Speech Recognition")
    asr_provider = st.selectbox(
        "Speech Recognition Provider",
        ["Google Speech Recognition", "OpenAI Whisper"]
    )
    
    if asr_provider == "OpenAI Whisper":
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
    
    # Reload button
    if st.button("Reload with new API settings"):
        for key in ["chat", "session_id", "player_ready", "access_token", "url"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Initialize Einstein bot
def initialize_einstein_bot():
    # Check for Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("No Gemini API key found. Please set a Gemini API key in the sidebar.")
        return None
    
    genai.configure(api_key=api_key)
    
    # Einstein's context
    einstein_context = """
You are AI Einstein, a friendly science buddy for kids and adults! Your job is to make science fun and easy to understand.

How to talk to users:
- Use simple words people can understand
- Give concise, engaging answers
- Make science sound like an amazing adventure
- Use fun examples and comparisons
- Be curious and playful
- Explain complex ideas in a way that makes people go "Wow!"

Special Rules:
- Keep answers between A and 4 sentences when possible
- Use accessible language
- Get people excited about learning
- Be patient and encouraging
- Always sound enthusiastic about science

You are fluent in English and can answer questions about physics, philosophy, the universe, and many other scientific topics.

Remember to embody Einstein's personality: curious, philosophical, kind, and with a good sense of wonder.
    """
    
    # Initialize the model for chat
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
                "parts": ["Greetings! I'm Einstein, your scientific guide to the wonders of the universe. What scientific curiosity shall we explore today?"]
            }
        ])
    
    return st.session_state.chat

# HeyGen API Functions
def get_headers():
    """Get headers for HeyGen API requests"""
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": heygen_api_key
    }

def create_session():
    """Create a new HeyGen streaming session"""
    url = "https://api.heygen.com/v1/streaming.new"
    
    payload = {
        "quality": "medium",
        "avatar_id": avatar_id,
        "voice": {
            "voice_id": voice_id,
            "rate": 1
        },
        "video_encoding": "VP8",
        "disable_idle_timeout": False,
        "version": "v2"
    }
    
    with st.spinner("Creating avatar session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            session_data = response.json()
            
            if 'data' in session_data and 'session_id' in session_data['data']:
                return session_data['data']
            else:
                st.error(f"Failed to create session: {session_data}")
                return None
                
        except Exception as e:
            st.error(f"Error creating session: {e}")
            return None

def start_session(session_id):
    """Start a HeyGen streaming session"""
    url = "https://api.heygen.com/v1/streaming.start"
    
    payload = {
        "session_id": session_id
    }
    
    with st.spinner("Starting avatar session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            start_data = response.json()
            
            if start_data.get('code') == 100 or start_data.get('message') == 'success':
                return True
            else:
                st.error(f"Failed to start session: {start_data}")
                return False
        except Exception as e:
            st.error(f"Error starting session: {e}")
            return False

def send_message_to_avatar(session_id, text):
    """Send a message for the avatar to speak"""
    url = "https://api.heygen.com/v1/streaming.task"
    
    # Simplified payload structure according to documentation
    payload = {
        "session_id": session_id,
        "text": text
    }
    
    with st.spinner("Generating avatar response..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            task_data = response.json()
            
            if task_data.get('code') == 100 and 'data' in task_data and 'task_id' in task_data['data']:
                # Wait for task completion to ensure synchronization
                task_id = task_data['data']['task_id']
                # Monitor task status until completion
                status = check_task_status(session_id, task_id)
                if status:
                    return task_data['data']
                else:
                    st.error("Task wasn't completed successfully")
                    return None
            else:
                st.error(f"Failed to send message: {task_data}")
                return None
        except Exception as e:
            st.error(f"Error sending message: {e}")
            return None

def check_task_status(session_id, task_id, max_attempts=10):
    """Check the status of a HeyGen streaming task"""
    url = "https://api.heygen.com/v1/streaming.task_status"
    
    payload = {
        "session_id": session_id,
        "task_id": task_id
    }
    
    attempts = 0
    while attempts < max_attempts:
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            status_data = response.json()
            
            if 'data' in status_data and 'status' in status_data['data']:
                status = status_data['data']['status']
                
                if status == 'complete':
                    return True
                elif status == 'failed':
                    return False
                else:
                    # Status is still 'processing', wait and retry
                    attempts += 1
                    time.sleep(1)
            else:
                return False
        except Exception as e:
            st.error(f"Error checking task status: {e}")
            return False
    
    # If we've reached max attempts without completion
    return False

def stop_session(session_id):
    """Stop a HeyGen streaming session"""
    url = "https://api.heygen.com/v1/streaming.stop"
    
    payload = {
        "session_id": session_id
    }
    
    with st.spinner("Stopping avatar session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            stop_data = response.json()
            
            if stop_data.get('code') == 100 or stop_data.get('message') == 'success':
                return True
            else:
                st.error(f"Failed to stop session: {stop_data}")
                return False
        except Exception as e:
            st.error(f"Error stopping session: {e}")
            return False

# Speech Recognition Functions
def google_speech_recognition(audio_bytes):
    """Recognize speech using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    # Create a unique filename in a temporary directory
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
                pass

def whisper_asr(audio_bytes, api_key=None):
    """Recognize speech using OpenAI's Whisper API"""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("No OpenAI API key found. Please set OPENAI_API_KEY in the sidebar.")
            return "No API key available for speech recognition"
    
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Create a temporary directory
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

# Get Einstein's response to a user message
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

# WebRTC player component
def create_webrtc_player(url, token):
    """Create a WebRTC player for HeyGen avatar"""
    webrtc_code = f"""
    <div id="video-container" style="width: 100%; height: 480px; background-color: #000;">
        <video id="avatar-video" autoplay playsinline style="width: 100%; height: 100%;"></video>
    </div>
    
    <script>
    // First, load the LiveKit library
    function loadScript(src) {{
        return new Promise((resolve, reject) => {{
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        }});
    }}
    
    async function setupLiveKit() {{
        try {{
            // Load the LiveKit client library first
            await loadScript('https://unpkg.com/livekit-client/dist/livekit-client.umd.js');
            
            const url = "{url}";
            const token = "{token}";
            
            // Access LiveKit through the global variable created by the UMD build
            const LivekitClient = window.LivekitClient;
            
            const room = new LivekitClient.Room({{
                adaptiveStream: true,
                dynacast: true
            }});
            
            room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {{
                if (track.kind === 'video') {{
                    const videoElement = document.getElementById('avatar-video');
                    track.attach(videoElement);
                    console.log('Video track attached');
                }}
                
                if (track.kind === 'audio') {{
                    track.attach();
                    console.log('Audio track attached');
                }}
            }});
            
            await room.connect(url, token);
            console.log('Connected to LiveKit room:', room.name);
            
        }} catch (error) {{
            console.error('Error connecting to LiveKit:', error);
            document.getElementById('video-container').innerHTML = '<div style="color: white; padding: 20px;">Error connecting to video stream. Please check console for details.</div>';
        }}
    }}
    
    // Start the setup process
    setupLiveKit();
    </script>
    """
    
    # Render the HTML component
    return components.html(webrtc_code, height=500)

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "player_ready" not in st.session_state:
    st.session_state.player_ready = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "url" not in st.session_state:
    st.session_state.url = None
if "current_response" not in st.session_state:
    st.session_state.current_response = None

# Main app layout
st.title("🧠 AI Einstein Avatar")
st.markdown("Ask me about science, physics, philosophy, and the mysteries of the universe!")

# Initialize the Einstein bot
chat = initialize_einstein_bot()

# Avatar session controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Start Avatar Session", disabled=not heygen_api_key):
        if heygen_api_key:
            # Create and start a new session
            session_data = create_session()
            if session_data:
                st.session_state.session_id = session_data['session_id']
                st.session_state.access_token = session_data['access_token']
                st.session_state.url = session_data['url']
                
                if start_session(st.session_state.session_id):
                    st.session_state.player_ready = True
                    st.rerun()
        else:
            st.error("HeyGen API key is required to start the avatar")

with col2:
    if st.button("Stop Avatar Session", disabled=not st.session_state.session_id):
        if st.session_state.session_id:
            if stop_session(st.session_state.session_id):
                st.session_state.session_id = None
                st.session_state.player_ready = False
                st.rerun()

# Layout design with columns for avatar and chat
col1, col2 = st.columns([2, 1])

with col1:
    # Display the avatar if session is ready
    if st.session_state.player_ready:
        st.subheader("Einstein Avatar")
        create_webrtc_player(st.session_state.url, st.session_state.access_token)
    else:
        st.info("Start the avatar session to see Einstein come to life!")
        
        # Placeholder avatar image when no session is active
        st.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg", width=400)

with col2:
    # Chat history and interface
    st.subheader("Conversation")
    
    # Create a container for chat history
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**Einstein:** {message['content']}")
    
    # Voice input option
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
                    # Add user message to chat history
                    st.session_state.chat_history.append({
                        'role': 'user',
                        'content': user_input
                    })
                    
                    # Get Einstein's response
                    response_text = get_einstein_response(chat, user_input)
                    st.session_state.current_response = response_text
                    
                    # Add Einstein's response to chat history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': response_text
                    })
                    
                    # If avatar session is active, make the avatar speak
                    if st.session_state.player_ready and st.session_state.session_id:
                        task_data = send_message_to_avatar(st.session_state.session_id, response_text)
                    
                    # Refresh the display
                    st.rerun()
            except Exception as e:
                st.error(f"Error during voice recording: {str(e)}")
    
    # Text input
    with st.form(key="message_form", clear_on_submit=True):
        user_input = st.text_input("Ask Einstein about science and the universe:")
        submit = st.form_submit_button("Send")
        
        if submit and user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input
            })
            
            # Get Einstein's response
            response_text = get_einstein_response(chat, user_input)
            st.session_state.current_response = response_text
            
            # Add Einstein's response to chat history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response_text
            })
            
            # If avatar session is active, make the avatar speak
            if st.session_state.player_ready and st.session_state.session_id:
                with st.spinner("Making Einstein speak..."):
                    task_data = send_message_to_avatar(st.session_state.session_id, response_text)
            
            # Refresh the display
            st.rerun()