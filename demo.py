'''
import requests

url = "https://api.heygen.com/v2/video/generate"

payload = {
    "caption": False,
    "title": "My AI Avatar Video",
    "callback_id": "my-custom-id-123",
    "dimension": {
        "width": 1280,
        "height": 720
    },
    "video_inputs": [
        {
            # Example scene with avatar and text-to-speech
            "character": {
                "type": "avatar",
                "avatar_id": "Santa_Fireplace_Front_public",
                "scale": 1.0,
                "avatar_style": "normal",
                "offset": {
                    "x": 0.0,
                    "y": 0.0
                }
            },
            "voice": {
                "type": "text",
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",
                "input_text": "Hello! This is a demo of the HeyGen API.",
                "speed": 1.0
            },
            "background": {
                "type": "color",
                "value": "#f6f6fc"
            }
        }
    ],
    "folder_id": "PAVLY",  # Optional
    "callback_url": "https://your-callback-url.com"  # Optional
}

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": "YjQ0ODcyMTYxZTFjNGEyYzljMzRmMzg5ZTIxNmIzMjctMTc0MzE1NDMwMg=="
}

response = requests.post(url, json=payload, headers=headers)
print(response.text)
'''


import requests

# Video ID from your previous response
video_id = "2b7b120c4e2f44c8b041d2f0597b2cd5"

# API endpoint for retrieving video status
url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"

headers = {
    "accept": "application/json",
    "x-api-key": "YjQ0ODcyMTYxZTFjNGEyYzljMzRmMzg5ZTIxNmIzMjctMTc0MzE1NDMwMg=="
}

# Make the GET request to retrieve video status
response = requests.get(url, headers=headers)

# Print the response
print(response.status_code)
print(response.json())

# If the video is completed, you might want to extract and save important URLs
if response.status_code == 200:
    data = response.json().get('data', {})
    status = data.get('status')
    
    print(f"Video Status: {status}")
    
    if status == "completed":
        video_url = data.get('video_url')
        gif_url = data.get('gif_url')
        thumbnail_url = data.get('thumbnail_url')
        duration = data.get('duration')
        
        print(f"Video URL: {video_url}")
        print(f"GIF URL: {gif_url}")
        print(f"Thumbnail: {thumbnail_url}")
        print(f"Duration: {duration} seconds")
        
        # Optional: Download the video file since the URL expires in 7 days
        if video_url:
            print("Downloading video file...")
            video_response = requests.get(video_url)
            with open(f"{video_id}.mp4", "wb") as f:
                f.write(video_response.content)
            print(f"Video saved as {video_id}.mp4")
    elif status == "failed":
        error = data.get('error')
        print(f"Error: {error}")