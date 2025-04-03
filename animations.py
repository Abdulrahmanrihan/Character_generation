import streamlit as st
import requests
import json
import time
import streamlit.components.v1 as components

# Set page configuration
st.set_page_config(page_title="HeyGen Avatar Chat", page_icon="🤖", layout="wide")

# API configuration
API_KEY = st.sidebar.text_input("API Key", value="YjQ0ODcyMTYxZTFjNGEyYzljMzRmMzg5ZTIxNmIzMjctMTc0MzE1NDMwMg==", type="password")
BASE_URL = "https://api.heygen.com/v1"
AVATAR_ID = st.sidebar.text_input("Avatar ID", value="Elenora_IT_Sitting_public")
VOICE_ID = st.sidebar.text_input("Voice ID", value="1bd001e7e50f421d891986aad5158bc8")

# Headers for API requests
def get_headers():
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }

# Function to create a new streaming session
def create_session():
    url = f"{BASE_URL}/streaming.new"
    
    payload = {
        "quality": "medium",
        "avatar_id": AVATAR_ID,
        "voice": {
            "voice_id": VOICE_ID,
            "rate": 1
        },
        "video_encoding": "VP8",
        "disable_idle_timeout": False,
        "version": "v2"
    }
    
    with st.spinner("Creating session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            session_data = response.json()
            
            if 'data' in session_data and 'session_id' in session_data['data']:
                st.sidebar.success(f"Session created: {session_data['data']['session_id']}")
                return session_data['data']
            else:
                st.sidebar.error(f"Failed to create session: {session_data}")
                return None
                
        except Exception as e:
            st.sidebar.error(f"Error creating session: {e}")
            return None

# Function to start a streaming session
def start_session(session_id):
    url = f"{BASE_URL}/streaming.start"
    
    payload = {
        "session_id": session_id
    }
    
    with st.spinner("Starting session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            start_data = response.json()
            
            if start_data.get('code') == 100 or start_data.get('message') == 'success':
                st.sidebar.success("Session started successfully!")
                return True
            else:
                st.sidebar.error(f"Failed to start session: {start_data}")
                return False
        except Exception as e:
            st.sidebar.error(f"Error starting session: {e}")
            return False

# Function to send a message to the avatar
def send_message(session_id, text):
    url = f"{BASE_URL}/streaming.task"
    
    payload = {
        "session_id": session_id,
        "text": text,
        "task_type": "chat",
        "task_mode": "sync"
    }
    
    with st.spinner("Sending message..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            task_data = response.json()
            
            if task_data.get('code') == 100 and 'data' in task_data and 'task_id' in task_data['data']:
                return task_data['data']
            else:
                st.sidebar.error(f"Failed to send message: {task_data}")
                return None
        except Exception as e:
            st.sidebar.error(f"Error sending message: {e}")
            return None

# Function to stop a session
def stop_session(session_id):
    url = f"{BASE_URL}/streaming.stop"
    
    payload = {
        "session_id": session_id
    }
    
    with st.spinner("Stopping session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            stop_data = response.json()
            
            if stop_data.get('code') == 100 or stop_data.get('message') == 'success':
                st.sidebar.success("Session stopped successfully!")
                return True
            else:
                st.sidebar.error(f"Failed to stop session: {stop_data}")
                return False
        except Exception as e:
            st.sidebar.error(f"Error stopping session: {e}")
            return False

# WebRTC player component
def create_webrtc_player(url, token):
    # Create a custom HTML component with LiveKit WebRTC player
    # Fixed: ensuring proper loading of livekit library and waiting for it to load
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

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'player_ready' not in st.session_state:
    st.session_state.player_ready = False
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'url' not in st.session_state:
    st.session_state.url = None

# Main app
st.title("HeyGen Avatar Chat")

# Sidebar controls
st.sidebar.title("Controls")

# Start/Stop session buttons
col1, col2 = st.sidebar.columns(2)

# Start button handler
if col1.button("Start Session"):
    # Create and start a new session
    session_data = create_session()
    if session_data:
        st.session_state.session_id = session_data['session_id']
        st.session_state.access_token = session_data['access_token']
        st.session_state.url = session_data['url']
        
        if start_session(st.session_state.session_id):
            st.session_state.player_ready = True
            st.rerun()

# Stop button handler 
if col2.button("Stop Session"):
    if st.session_state.session_id:
        if stop_session(st.session_state.session_id):
            st.session_state.session_id = None
            st.session_state.player_ready = False
            st.rerun()

# Display session info
if st.session_state.session_id:
    st.sidebar.success(f"Active Session: {st.session_state.session_id[:8]}...")

# Main app area - Avatar display
if st.session_state.player_ready:
    # Display the WebRTC player
    st.subheader("Avatar View")
    create_webrtc_player(st.session_state.url, st.session_state.access_token)
    
    # Chat interface
    st.subheader("Chat with Avatar")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**Avatar:** {message['content']}")
    
    # Message input
    with st.form(key="message_form", clear_on_submit=True):
        message = st.text_input("Type your message:", key="message_input")
        submit_button = st.form_submit_button(label="Send")
        
        if submit_button and message:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': message
            })
            
            # Send message to avatar
            task_data = send_message(st.session_state.session_id, message)
            
            if task_data and 'duration_ms' in task_data:
                # Add avatar response to history (in a real app, this would be the transcription)
                st.session_state.chat_history.append({
                    'role': 'avatar',
                    'content': f"[Speaking for {task_data['duration_ms']/1000:.1f} seconds]"
                })
                
                # Refresh the display
                st.rerun()
        
else:
    # No active session
    st.info("Click 'Start Session' to begin chatting with the avatar.")