#!/usr/bin/env python3
"""
Test script for Authentication APIs
Run this script to test all authentication endpoints
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/api/v1/login"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_FULLNAME = "Test User"

def print_response(response: requests.Response, title: str):
    """Print formatted response"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response Text: {response.text}")

def test_register():
    """Test registration API"""
    print("\n🔵 Testing Registration API...")
    
    data = {
        "email": TEST_EMAIL,
        "fullname": TEST_FULLNAME,
        "password": TEST_PASSWORD,
        "confirm_password": TEST_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/register", json=data)
    print_response(response, "POST /api/v1/login/register")
    
    if response.status_code == 200:
        print("✅ Registration successful!")
        return True
    else:
        print("❌ Registration failed!")
        return False

def test_confirm_code(code: str):
    """Test confirm code API"""
    print("\n🔵 Testing Confirm Code API...")
    
    data = {
        "email": TEST_EMAIL,
        "code": code
    }
    
    response = requests.post(f"{BASE_URL}/confirm-code", json=data)
    print_response(response, "POST /api/v1/login/confirm-code")
    
    if response.status_code == 200:
        print("✅ Code confirmation successful!")
        return True
    else:
        print("❌ Code confirmation failed!")
        return False

def test_resend_code():
    """Test resend code API"""
    print("\n🔵 Testing Resend Code API...")
    
    data = {
        "email": TEST_EMAIL
    }
    
    response = requests.post(f"{BASE_URL}/resend-code", json=data)
    print_response(response, "POST /api/v1/login/resend-code")
    
    if response.status_code == 200:
        print("✅ Resend code successful!")
        return True
    else:
        print("❌ Resend code failed!")
        return False

def test_credential_login():
    """Test credential login API"""
    print("\n🔵 Testing Credential Login API...")
    
    data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "login_provider": False
    }
    
    response = requests.post(f"{BASE_URL}/access-token", json=data)
    print_response(response, "POST /api/v1/login/access-token (Credential)")
    
    if response.status_code == 200:
        print("✅ Credential login successful!")
        return response.json()
    else:
        print("❌ Credential login failed!")
        return None

def test_provider_login():
    """Test provider login API"""
    print("\n🔵 Testing Provider Login API...")
    
    data = {
        "email": "provider@example.com",
        "fullname": "Provider User",
        "password": None,
        "login_provider": True
    }
    
    response = requests.post(f"{BASE_URL}/access-token", json=data)
    print_response(response, "POST /api/v1/login/access-token (Provider)")
    
    if response.status_code == 200:
        print("✅ Provider login successful!")
        return response.json()
    else:
        print("❌ Provider login failed!")
        return None

def test_refresh_token(refresh_token: str):
    """Test refresh token API"""
    print("\n🔵 Testing Refresh Token API...")
    
    data = {
        "refresh_token": refresh_token
    }
    
    response = requests.post(f"{BASE_URL}/refresh-token", json=data)
    print_response(response, "POST /api/v1/login/refresh-token")
    
    if response.status_code == 200:
        print("✅ Refresh token successful!")
        return response.json()
    else:
        print("❌ Refresh token failed!")
        return None

def main():
    """Main test function"""
    print("🚀 Starting Authentication API Tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Email: {TEST_EMAIL}")
    
    # Test 1: Register
    if not test_register():
        print("\n❌ Registration failed, stopping tests")
        return
    
    # Wait for user to enter verification code
    print("\n📧 Please check your email for verification code")
    code = input("Enter the 6-digit verification code: ").strip()
    
    # Test 2: Confirm Code
    if not test_confirm_code(code):
        print("\n❌ Code confirmation failed, stopping tests")
        return
    
    # Test 3: Credential Login
    login_result = test_credential_login()
    if not login_result:
        print("\n❌ Credential login failed, stopping tests")
        return
    
    # Test 4: Refresh Token
    refresh_token = login_result.get("refresh_token")
    if refresh_token:
        test_refresh_token(refresh_token)
    
    # Test 5: Provider Login
    test_provider_login()
    
    # Test 6: Resend Code (optional)
    print("\n🔵 Testing Resend Code (this might fail if no pending registration)...")
    test_resend_code()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Error during testing: {e}")
