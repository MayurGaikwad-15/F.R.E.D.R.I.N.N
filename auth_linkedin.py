import os
import sys
import webbrowser
import httpx
from urllib.parse import urlencode, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to path so we can import linkedin_ops if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8585/callback"
# Required scopes to get user info AND post on behalf of the user
SCOPES = "openid profile email w_member_social"

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback"):
            query_components = parse_qs(self.path.split('?')[1])
            if 'code' in query_components:
                self.server.auth_code = query_components['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Authentication Successful!</h1><p>You can close this window now.</p></body></html>")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Authentication Failed</h1><p>No code found in the callback URL.</p></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

def run_auth_flow():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in your .env file.")
        print("Please check your .env file and ensure they are filled out.")
        sys.exit(1)
        
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES
    }
    url = f"{auth_url}?{urlencode(params)}"
    
    # Start local server to listen for the callback
    server_address = ('', 8585)
    httpd = HTTPServer(server_address, OAuthHandler)
    httpd.auth_code = None
    
    print(f"Opening browser for LinkedIn Authentication...")
    print(f"If the browser doesn't open automatically, please click this link:\n{url}")
    webbrowser.open(url)
    
    # Wait for the callback request
    while httpd.auth_code is None:
        httpd.handle_request()
        
    code = httpd.auth_code
    print("Authorization code received. Fetching access token...")
    
    # Exchange code for token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = httpx.post(token_url, data=data, headers=headers)
    if response.status_code == 200:
        token_data = response.json()
        
        # Save token immediately
        token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "linkedin_token.json")
        with open(token_path, "w") as f:
            json.dump(token_data, f, indent=4)
            
        print("[OK] Authentication successful! linkedin_token.json has been generated.")
        print("Hold on, fetching your LinkedIn URN...")
        
        # Fetch URN using the new token
        # Using OpenID profile endpoint to fetch URN
        access_token = token_data.get("access_token")
        profile_url = "https://api.linkedin.com/v2/userinfo"
        prof_res = httpx.get(profile_url, headers={"Authorization": f"Bearer {access_token}"})
        
        if prof_res.status_code == 200:
            prof_data = prof_res.json()
            # The 'sub' field contains the member ID in the OpenID userinfo response
            user_urn = f"urn:li:person:{prof_data.get('sub')}" 
            
            # Save the urn directly in the token file for ease of access
            token_data['author_urn'] = user_urn
            with open(token_path, "w") as f:
                json.dump(token_data, f, indent=4)
                
            print(f"[OK] Fetched LinkedIn Profile URN: {user_urn}")
            print("Setup Complete! You can now use the F.R.E.D.R.I.N.N. bot to post to LinkedIn.")
        else:
            print(f"[WARNING] Could not fetch your LinkedIn Profile URN.")
            print(f"Error {prof_res.status_code}: {prof_res.text}")
            
    else:
        print("[ERROR] Failed to fetch access token!")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    run_auth_flow()
