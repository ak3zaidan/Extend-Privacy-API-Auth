from flask import Flask, request, jsonify, make_response
from datetime import datetime, timezone, timedelta
from google.oauth2 import service_account
from camoufox import AsyncCamoufox
from google.cloud import firestore
from flask_cors import CORS
from typing import Optional
import traceback
import asyncio
import random
import json
import os

TEST_TYPE = "Privacy" # Or "Extend"
TEST_MODE = False

TOKEN_EXP_EXTEND = 9
TOKEN_EXP_PRIVACY = 120

app = Flask(__name__)

CORS(app, origins=[
    "https://theprofilebuilder.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
])

def parse_proxy(proxy_string):
    try:
        host, port, username, password = proxy_string.split(':')
        return host, port, username, password
    except:
        return "", "", "", ""

def random_proxy():
    proxies = []
    
    if not os.path.exists("proxies.txt"):
        print(f'Error: proxies.txt not found.')
        return None
    with open("proxies.txt", "r") as file:
        proxies = [line.strip() for line in file if line.strip()]

    if proxies:
        return random.choice(proxies)
    
    return None

def save_token(db, email, token, type: str):
    """
    Save a token to Firebase collection "tokens" with the given email as document ID.
    
    Args:
        db: Firebase database instance
        email (str): Email address to use as document ID
        token (str): Token string to save
    """
    try:
        current_time = datetime.now(timezone.utc)
        
        token_data = {
            "token": token,
            "age": current_time
        }
        
        token_doc_ref = db.collection(f'tokens{type.lower()}').document(email)
        token_doc_ref.set(token_data)
        
        print(f"Token saved successfully for {email}")
    except Exception as e:
        print(f"Error saving token to database: {e}")
        raise e

def check_db(db, email: str, type: str) -> Optional[str]:
    """
    Check Firebase collection "tokens" for a document with the given email ID.
    
    Args:
        db: Firebase database instance
        email (str): Email address to use as document ID
    
    Returns:
        str: Token string if found and within 5 minutes, None otherwise
    """
    try:
        # Check tokens collection for document with email as ID
        token_doc_ref = db.collection(f'tokens{type.lower()}').document(email)
        token_doc = token_doc_ref.get()
        
        if token_doc.exists:
            data = token_doc.to_dict()
            age = data.get("age")  # Firebase timestamp
            token = data.get("token")  # String
            
            if age and token:
                # Convert Firebase timestamp to datetime
                age_datetime = age.replace(tzinfo=timezone.utc) if age.tzinfo is None else age
                current_time = datetime.now(timezone.utc)
                
                # Check if age is within 5 minutes
                time_diff = current_time - age_datetime

                TOKEN_EXP = TOKEN_EXP_EXTEND if type.lower() == "extend" else TOKEN_EXP_PRIVACY

                if time_diff <= timedelta(minutes=TOKEN_EXP):
                    # Token is fresh, return it
                    return token
                else:
                    # Token is expired, delete the document
                    token_doc_ref.delete()
                    return None
            else:
                # Missing required fields, delete the document
                token_doc_ref.delete()
                return None
        else:
            # Token document not found, check and cleanup OTP document if exists
            otp_doc_ref = db.collection("otp").document(email)
            otp_doc = otp_doc_ref.get()
            
            if otp_doc.exists:
                otp_doc_ref.delete()
            
            return None
            
    except Exception as e:
        print(f"Error checking database: {e}")
        return None

async def get_otp_code_async(email: str, db, timeout: int = 120) -> Optional[str]:
    """
    Asynchronous version of OTP polling function.
    
    Args:
        email (str): The email address to look up the OTP for
        db: Database instance
        timeout (int): Maximum time to wait in seconds (default: 120)
    
    Returns:
        str: The OTP code if found, None if timeout reached or error occurred
    """
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            # Get document from Firestore
            doc_ref = db.collection("otp").document(email)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                otp = data.get("otp")
                doc_ref.delete()

                if otp:
                    print("\nGot otp code: " + otp)
                    return otp
            
            # Wait 1 second before next poll (using async sleep)
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error polling for OTP: {e}")
            await asyncio.sleep(2)
            continue
    
    # Timeout reached
    return None

async def privacy_auth(db, email, password, retry_count=0):
    """
    Authenticate with Extend using Camoufox browser automation with proxy support.
    Includes OTP handling and retry logic for retryable errors.
    
    Args:
        db: Database instance
        email (str): Login email
        password (str): Login password
        retry_count (int): Current retry attempt (internal use)
    
    Returns:
        str: Authentication token if successful, None otherwise
    """
    max_retries = 1
    
    proxy_settings = get_proxy_settings()
    if not proxy_settings:
        print("No proxy available")
    
    try:
        config = {
            "humanize": False
        }
        
        async with AsyncCamoufox(
            proxy=proxy_settings,
            geoip=True,
            config=config,
            headless=True if TEST_MODE else "virtual",
            firefox_user_prefs={
                "media.peerconnection.enabled": False
            }
        ) as browser:
            try:
                # Launch browser and create new page
                page = await browser.new_page()
                
                # Navigate to the signin page
                await page.goto("https://app.privacy.com/login", wait_until="load")
               
                # Wait for email field and fill it
                email_field = page.locator('[name="email"]')
                await email_field.wait_for(timeout=20000)
                await email_field.hover()
                await email_field.click()
                await asyncio.sleep(0.2)
                await email_field.press_sequentially(email, delay=random.uniform(5, 10))
                
                # Wait for password field and fill it
                password_field = page.locator('[name="password"]')
                await password_field.wait_for(timeout=10000)
                await password_field.hover()
                await password_field.click()
                await asyncio.sleep(0.2)
                await password_field.press_sequentially(password, delay=random.uniform(5, 10))

                await asyncio.sleep(0.25)
                
                # Click the continue button
                login_btn = page.locator('button[type="submit"]')
                await login_btn.wait_for(timeout=10000)
                await login_btn.hover()
                await login_btn.click()

                # Check for login error element
                try:
                    error_element = page.locator('div[role="alert"]')
                    await error_element.wait_for(timeout=6000)
                    if await error_element.is_visible():
                        error_text = await error_element.inner_text(timeout=3000)
                        print(error_text)
                        return f'Login Failed: {error_text}'
                except:
                    # No error element found, continue
                    pass

                # Get OTP code
                otp = await get_otp_code_async(email, db)

                if not otp or len(otp) != 6:
                    # Check for login error element again
                    try:
                        error_element = page.locator('div[role="alert"]')
                        if await error_element.is_visible():
                            error_text = await error_element.inner_text(timeout=3000)
                            print(error_text)
                            return f'Login Failed: {error_text}'
                    except:
                        pass
                
                    print("No otp found or bad format")
                    return None

                # Enter OTP to the field
                otp_field = page.locator('[name="code0"]')
                await otp_field.wait_for(timeout=10000)
                await otp_field.hover()
                await otp_field.click()
                await asyncio.sleep(0.2)
                await otp_field.press_sequentially(otp, delay=random.uniform(10, 20))
                
                await asyncio.sleep(0.25)

                # Click verify/continue button
                verify_btn = page.locator('button:has-text("Continue")')
                await verify_btn.wait_for(timeout=10000)
                await verify_btn.hover()
                await verify_btn.click()

                # Check for OTP error element
                try:
                    error_element = page.locator('div[role="alert"]')
                    await error_element.wait_for(timeout=3000)
                    if await error_element.is_visible():
                        error_text = await error_element.inner_text(timeout=3000)
                        print(error_text)
                        return f'OTP Failed: {error_text}'
                except:
                    # No error element found, continue
                    pass
                
                auth_token = await extract_auth_token_privacy(page)
                return auth_token
            
            except Exception as page_error:
                print(f"Page interaction error: {repr(page_error)}")
                traceback.print_exc()
                
                # Check if this is a retryable error
                if is_retryable_error(page_error) and retry_count < max_retries:
                    print(f"Retryable error detected, retrying... (attempt {retry_count + 1})")
                    return await extend_auth(db, email, password, retry_count + 1)
                
                return None
                
    except Exception as e:
        print(f"Browser automation error: {e}")
        
        # Check if this is a retryable error
        if is_retryable_error(e) and retry_count < max_retries:
            print(f"Retryable error detected, retrying... (attempt {retry_count + 1})")
            return await extend_auth(db, email, password, retry_count + 1)
        
        return None

async def extract_auth_token_privacy(page) -> Optional[str]:
    """
    Extract JWT authentication token from browser cookies on app.privacy.com.
    Polls cookies every 2 seconds for up to 30 seconds.
    
    Args:
        page: Camoufox/Playwright page instance
    Returns:
        str: JWT token if found, None otherwise
    """
    try:
        max_attempts = 15  # 15 attempts * 2 seconds = 30 seconds
        attempt = 0

        while attempt < max_attempts:
            try:
                # Get cookies from the current page context
                cookies = await page.context.cookies()
                
                # Look for the "token" cookie on app.privacy.com
                for cookie in cookies:
                    if cookie.get("name") == "token" and "app.privacy.com" in cookie.get("domain", ""):
                        jwt_token = cookie.get("value", "")
                        if jwt_token:
                            print(f"Found JWT token: {jwt_token[:20]}...")
                            return jwt_token
                
                # Wait 2 seconds before next attempt
                await asyncio.sleep(2.0)
                attempt += 1
            
            except Exception as eval_error:
                print(f"Error checking cookies: {eval_error}")
                await asyncio.sleep(2.0)
                attempt += 1
                continue

        print("No JWT token found in cookies after polling")
        return None

    except Exception as e:
        print(f"Error extracting auth token: {e}")
        return None

async def extend_auth(db, email, password, retry_count=0):
    """
    Authenticate with Extend using Camoufox browser automation with proxy support.
    Includes OTP handling and retry logic for retryable errors.
    
    Args:
        db: Database instance
        email (str): Login email
        password (str): Login password
        retry_count (int): Current retry attempt (internal use)
    
    Returns:
        str: Authentication token if successful, None otherwise
    """
    max_retries = 1
    
    proxy_settings = get_proxy_settings()
    if not proxy_settings:
        print("No proxy available")
    
    try:
        config = {
            "humanize": False
        }
        
        async with AsyncCamoufox(
            proxy=proxy_settings,
            geoip=True,
            config=config,
            headless=True if TEST_MODE else "virtual",
            firefox_user_prefs={
                "media.peerconnection.enabled": False
            }
        ) as browser:
            try:
                # Launch browser and create new page
                page = await browser.new_page()
                
                # Navigate to the signin page
                await page.goto("https://app.paywithextend.com/signin", wait_until="load")
               
                # Wait for email field and fill it
                email_field = page.locator('#email')
                await email_field.wait_for(timeout=20000)
                await email_field.hover()
                await email_field.click()
                await email_field.press_sequentially(email, delay=random.uniform(5, 10))
                
                # Wait for password field and fill it
                password_field = page.locator('#loginPwd')
                await password_field.wait_for(timeout=10000)
                await password_field.hover()
                await password_field.click()
                await password_field.press_sequentially(password, delay=random.uniform(5, 10))

                await asyncio.sleep(0.25)
                
                # Click the continue button
                login_btn = page.locator('#loginBtn')
                await login_btn.wait_for(timeout=10000)
                await login_btn.hover()
                await login_btn.click()

                # Check for login error element
                try:
                    error_elements = page.locator('//span[@data-testid="signInError"]')
                    await error_elements.wait_for(timeout=6000)
                    if await error_elements.is_visible():
                        error_text = await error_elements.inner_text(timeout=3000)
                        print(error_text)
                        return f'Login Failed: {error_text}'
                except:
                    # No error element found, continue
                    pass

                # Get OTP code
                otp = await get_otp_code_async(email, db)

                if not otp or len(otp) != 6:
                    # Check for login error element again
                    try:
                        error_elements = page.locator('//span[@data-testid="signInError"]')
                        if await error_elements.is_visible():
                            error_text = await error_elements.inner_text(timeout=3000)
                            print(error_text)
                            return f'Login Failed: {error_text}'
                    except:
                        pass
                
                    print("No otp found or bad format")
                    return None

                # Enter OTP to the field using XPath
                otp_field = page.locator('//*[@id="content"]/div/div[1]/div/div[4]/div[1]/form/div[1]/input')
                await otp_field.wait_for(timeout=10000)
                await otp_field.hover()
                await otp_field.click()
                await otp_field.press_sequentially(otp, delay=random.uniform(10, 20))
                
                await asyncio.sleep(0.25)

                # Click verify button
                verify_btn = page.locator('#verifyCodeBtn')
                await verify_btn.wait_for(timeout=10000)
                await verify_btn.hover()
                await verify_btn.click()

                # Check for otp error element
                try:
                    error_elements = page.locator('//*[@id="content"]/div/div[1]/div/div[4]/div[1]/form/div[1]/div/span')
                    await error_elements.wait_for(timeout=3000)
                    if await error_elements.is_visible():
                        error_text = await error_elements.inner_text(timeout=3000)
                        print(error_text)
                        return f'OTP Failed: {error_text}'
                except:
                    # No error element found, continue
                    pass
                
                auth_token = await extract_auth_token_extend(page)
                return auth_token
            
            except Exception as page_error:
                print(f"Page interaction error: {repr(page_error)}")
                traceback.print_exc()
                
                # Check if this is a retryable error
                if is_retryable_error(page_error) and retry_count < max_retries:
                    print(f"Retryable error detected, retrying... (attempt {retry_count + 1})")
                    return await extend_auth(db, email, password, retry_count + 1)
                
                return None
                
    except Exception as e:
        print(f"Browser automation error: {e}")
        
        # Check if this is a retryable error
        if is_retryable_error(e) and retry_count < max_retries:
            print(f"Retryable error detected, retrying... (attempt {retry_count + 1})")
            return await extend_auth(db, email, password, retry_count + 1)
        
        return None

async def extract_auth_token_extend(page) -> Optional[str]:
    """
    Extract authentication token from the page using the same method as Swift code.
    Polls localStorage every 2 seconds looking for Cognito access token.
    Args:
        page: Camoufox page instance
    Returns:
        str: Authentication token if found, None otherwise
    """
    try:
        js_script = """
        (function() {
            function lookup(suffix) {
                var key = Object.keys(localStorage).find(function(key) {
                    return key.startsWith("CognitoIdentityServiceProvider") && key.endsWith(suffix);
                });
                if (!key) return null;
                return localStorage[key];
            }
            var accessToken = lookup("accessToken");
            return JSON.stringify({
                accessToken: accessToken
            });
        })()
        """
        
        # Poll for access token every 2 seconds for up to 60 seconds
        max_attempts = 15  # 15 attempts * 2 seconds = 30 seconds
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Execute the JavaScript to look for the access token
                result = await page.evaluate(js_script)
                
                if result:
                    try:
                        # Handle case where result might already be parsed
                        if isinstance(result, dict):
                            access_token = result.get("accessToken", "")
                        else:
                            token_data = json.loads(result)
                            access_token = token_data.get("accessToken", "")
                        
                        if access_token:
                            print(f"Found access token: {access_token[:20]}...")
                            return access_token
                    except (json.JSONDecodeError, TypeError) as parse_error:
                        print(f"Error parsing result: {parse_error}")
                        pass
                
                # Wait 2 seconds before next attempt (using async sleep)
                await asyncio.sleep(2.0)
                attempt += 1
                
            except Exception as eval_error:
                print(f"Error evaluating JavaScript: {eval_error}")
                await asyncio.sleep(2.0)
                attempt += 1
                continue
        
        print("No Cognito access token found after polling")
        return None
        
    except Exception as e:
        print(f"Error extracting auth token: {e}")
        return None

def get_proxy_settings():
    """
    Get proxy configuration in Camoufox format.
    Returns proxy settings dict or None if no proxy available.
    """
    proxy = random_proxy()  # Your existing random_proxy() function
    if not proxy:
        return None
    
    # Parse proxy using your existing function
    ip, port, username, proxyPass = parse_proxy(proxy)
    proxy_url = f"http://{ip}:{port}"
    
    proxy_settings = {
        "server": proxy_url,
        "username": username,
        "password": proxyPass
    }
    
    return proxy_settings

def is_retryable_error(error) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: Exception object
    
    Returns:
        bool: True if error is retryable, False otherwise
    """
    error_str = str(error).lower()
    retryable_errors = [
        'timeout',
        'network',
        'connection',
        'proxy',
        'dns',
        'ssl',
        'tls',
        'browser disconnected',
        'page crashed',
        'navigation timeout',
        'target closed'  # Added for Playwright/Camoufox specific errors
    ]
    
    return any(retryable_error in error_str for retryable_error in retryable_errors)

def run_async_auth(db, email, password, type: str):
    """
    Wrapper function to run async extend_auth in a new event loop
    """
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if type.lower() == "extend":
                return loop.run_until_complete(extend_auth(db, email, password))
            else:
                return loop.run_until_complete(privacy_auth(db, email, password))
        finally:
            loop.close()
    except Exception as e:
        print(f"Error running async auth: {e}")
        return None

@app.route('/authtask', methods=['GET', 'POST', 'OPTIONS'])
def authtask():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "https://theprofilebuilder.com")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        return response
    
    try:
        creds = service_account.Credentials.from_service_account_file("service.json")
        db = firestore.Client(credentials=creds)

        if request.method == 'GET':
            params = request.args
        else:
            params = request.json if request.is_json else request.form
        
        email = params.get('email')
        password = params.get('password')

        if not email or not password:
            return jsonify({"error": "email and password invalid"}), 500
        
        type = params.get('type')

        if not type:
            return jsonify({"error": "Merchant type not included"}), 500

        auth_token = check_db(db, email, type)

        if auth_token:
            return jsonify({"access_token": auth_token}), 200
        
        try:
            # Use the wrapper function to run async code
            auth_token = run_async_auth(db, email, password, type)
            
            if auth_token:
                if "Login Failed" in auth_token:
                    return jsonify({"error": auth_token}), 401
                if "OTP Failed" in auth_token:
                    return jsonify({"error": auth_token}), 402

                save_token(db, email, auth_token, type)

                db.close()

                return jsonify({"access_token": auth_token}), 200
            else:
                return jsonify({"error": "Failed to auth"}), 500
            
        except asyncio.TimeoutError:
            return jsonify({"error": "Authentication timeout after 3 minutes"}), 408

    except Exception as e:
        print("Exception caught in auth: " + str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if TEST_MODE:
        creds = service_account.Credentials.from_service_account_file("service.json")
        db = firestore.Client(credentials=creds)
        
        # Use the wrapper function for test mode too
        auth_token = run_async_auth(db, "ak3zaidan@gmail.com", "2@@3Demha", TEST_TYPE)
        print(f"Test auth result: {auth_token}")
    else:
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
