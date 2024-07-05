import requests
from dotenv import load_dotenv
import os
import re
import time

# Load the .env file
load_dotenv()

# Now you can access the variables using os.getenv
LN_API_ENDPOINT_POST = "https://api.linkedin.com/rest/posts"
LN_API_ENDPOINT_IMG = "https://api.linkedin.com/rest/images?action=initializeUpload"
LK_API_VERSION = "202405"
LK_OWNER = os.getenv('LK_OWNER')
LK_TOKEN = os.getenv('LK_TOKEN')


def post_image_and_text(file_path: str, text_content: str):

    # Headers setup, mainly for authentication and content type
    headers = {
        "Authorization": f"Bearer {LK_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LK_API_VERSION
    }

    # Step 1: Initialize the image upload using the new Images API
    initialize_upload_data = {
        "initializeUploadRequest": {
            "owner": LK_OWNER  # Use the LinkedIn owner URN from the environment variable
        }
    }

    # Send request to initialize upload and parse the response
    response = requests.post(LN_API_ENDPOINT_IMG, json=initialize_upload_data, headers=headers)
    upload_response_data = response.json()

    # Extract the upload URL and image URN from the response
    upload_url = upload_response_data["value"]["uploadUrl"]
    image_urn = upload_response_data["value"]["image"]

    # Step 2: Upload the image file (modify this part to match how you handle file uploads)
    with open(file_path, "rb") as image_file:
        image_data = image_file.read()

    # Upload the image using the obtained URL
    upload_headers = {"Authorization": f"Bearer {LK_TOKEN}"}  # Authorization for the image upload
    upload_response = requests.put(upload_url, data=image_data, headers=upload_headers)
    print(f"Upload Response Status Code: {upload_response.status_code}")


    # Optional: Fetch the uploaded image details for verification or further use
    get_image_url = f"https://api.linkedin.com/rest/images/{image_urn}"

    for _ in range(10):
        get_image_response = requests.get(get_image_url, headers=headers)
        response_json = get_image_response.json()
        print(response_json)  # Display the image details for confirmation

        if response_json.get('status') == 'PROCESSING':
            time.sleep(5)  # Wait for 5 seconds before the next attempt
        else:
            break  # If the status is 'PROCESSING', break the loop

    parsed = re.sub(r'[\(\)*\[\]\{\}<>@|~_]', r'\\\g<0>', text_content)

    # Step 3: Create the image share
    post_data = {
        "author": LK_OWNER,
        "commentary": parsed,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "content": {
            "media": {
                "title": "Center stage!",
                "id": image_urn
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    # Sending the request to create the post
    response = requests.post(LN_API_ENDPOINT_POST, json=post_data, headers=headers)

    # Check for a successful response (201 Created)
    if response.status_code == 201:
        post_id = response.headers.get('x-linkedin-id')  # Changed from 'x-restli-id' to 'x-linkedin-id'
        print(f"Post successfully created with ID: {post_id}")
        return post_id
    else:
        print(f"Failed to create post. Status code: {response.status_code}, Error: {response.json()}")


def post_comment_on_linkedin(post_urn: str, comment: str):
    headers = {
        'Authorization': f'Bearer {LK_TOKEN}',
        'LinkedIn-Version': LK_API_VERSION,  # Adjust this to the current version in the format YYYYMM
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }

    # URN of the share or ugcPost where you want to post the comment
    share_urn = requests.utils.quote(post_urn)

    # Comment data
    comment_data = {
        "actor": LK_OWNER,  # Your LinkedIn Person URN
        "object": share_urn,
        "message": {
            "text": comment
        }
    }

    # URL for posting the comment
    url = f'https://api.linkedin.com/v2/socialActions/{share_urn}/comments'

    # POST request to create a comment
    response = requests.post(url, headers=headers, json=comment_data)

    # Output the response from the API
    if response.status_code == 201:
        comment_id = response.headers.get('x-linkedin-id')
        print(f'Comment created successfully with ID: {comment_id}')
        print(response.json())
    else:
        print(f'Failed to create comment. Status code: {response.status_code}, Error: {response.json()}')

