import requests
from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Now you can access the variables using os.getenv
LN_API_ENDPOINT_POST = "https://api.linkedin.com/v2/ugcPosts"
LN_API_ENDPOINT_IMG = "https://api.linkedin.com/v2/assets?action=registerUpload"
LN_API_ENDPOINT_ANALYTICS = "https://api.linkedin.com/v2/organizationalEntityShareStatistics"
LK_OWNER = os.getenv('LK_OWNER')
LK_TOKEN = os.getenv('LK_TOKEN')



def post_image_and_text(
    title: str, file_path: str, text_content: str
):
    register_upload_url = LN_API_ENDPOINT_IMG
    share_url = LN_API_ENDPOINT_POST

    # Step 1: Register the image upload
    register_upload_data = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": LK_OWNER,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }

    headers = {
        "Authorization": f"Bearer {LK_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(register_upload_url, json=register_upload_data, headers=headers)
    upload_response_data = response.json()

    # Extract the upload URL and asset ID from the response
    upload_url = upload_response_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_id = upload_response_data["value"]["asset"]

    # Step 2: Upload the image file
    image_file_path = file_path  # Replace with your image file path

    with open(image_file_path, "rb") as image_file:
        image_data = image_file.read()

    headers = {
        "Authorization": f"Bearer {LK_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(upload_url, data=image_data, headers=headers)

    # Step 3: Create the image share
    share_data = {
        "author": LK_OWNER,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text_content
                },
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": "Center stage!"
                        },
                        "media": asset_id,
                        "title": {
                            "text": title
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    response = requests.post(share_url, json=share_data, headers=headers)

    # Check for a successful response (201 Created)
    if response.status_code in [200, 201]:
        post_urn = response.json().get('id')  # Extracting the URN of the post
        print("Image share created successfully. Post URN:", post_urn)
        return post_urn  # Returning the URN for further use
    else:
        print("Error creating image share. Status code:", response.status_code)
        print("Response content:", response.content.decode())

# %%

def fetch_post_engagement_data(post_urn: str):
    """
    Fetch engagement data for a specific LinkedIn post.

    Args:
    post_urn (str): The unique identifier (URN) of the LinkedIn post.

    Returns:
    dict: Engagement data for the post.
    """
    # Prepare the request headers
    headers = {
        "Authorization": f"Bearer {LK_TOKEN}",
        "Content-Type": "application/json"
    }

    # Prepare the query parameters
    params = {
        "q": "organizationalEntity",
        "organizationalEntity": post_urn,
    }

    # Make the API call to fetch post analytics
    response = requests.get(LN_API_ENDPOINT_ANALYTICS, headers=headers, params=params)

    # Check for a successful response
    if response.status_code == 200:
        engagement_data = response.json()
        print("Engagement data fetched successfully.")
        return engagement_data
    else:
        print("Error fetching engagement data. Status code:", response.status_code)
        print("Response content:", response.content.decode())
        return None

# Example usage
# post_urn = post_image_and_text(title, file_path, text_content)


# post_urn = "urn:li:ugcPost:1234567890123456789"  # Replace with your actual post URN
# engagement_data = fetch_post_engagement_data(post_urn)
# print(engagement_data)

# %%
