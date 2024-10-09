import requests
import webbrowser
import hashlib
import os
from flask import Flask, request, jsonify, send_file
import json

app = Flask(__name__)

# OAuth 2.0 설정 정보
client_id = 'your_id'
client_secret = 'your_pw'
redirect_uri = 'http://localhost:5000/callback'
auth_url_base = 'https://accounts.i-sens.com/auth/authorize'
token_url = 'https://accounts.i-sens.com/oauth2/token'
api_url = 'https://api.i-sens.com/v1/public/cgms'

# 고유한 state와 nonce 값 생성
state = hashlib.sha256(os.urandom(1024)).hexdigest()  # 고유한 state 값 생성
nonce = hashlib.sha256(os.urandom(1024)).hexdigest()  # 고유한 nonce 값 생성

# 1. OAuth 인증 요청 URL을 열어서 인가 코드를 얻는 함수
def open_browser_for_oauth():
    # OAuth 2.0 authorization URL 구성
    auth_url = f"{auth_url_base}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}&nonce={nonce}"
    # 브라우저에서 OAuth 로그인 페이지 열기
    webbrowser.open(auth_url)

# 2. Flask 엔드포인트: 리디렉션된 URL에서 인가 코드를 받아 토큰 요청
@app.route('/callback')
def callback():
    # URL에서 'code'와 'state' 파라미터 값을 추출
    code = request.args.get('code')
    state_received = request.args.get('state')

    if not code or state_received != state:
        return "Error: Authorization code not found or state mismatch", 400

    # 인가 코드를 사용해 액세스 토큰 요청
    access_token = get_access_token(code)
    
    if access_token:
        # 액세스 토큰을 사용해 API 호출
        data = call_api(access_token)
        
        if data and 'error' not in data:
            # JSON 데이터를 파일로 저장
            json_filename = "api_data.json"
            with open(json_filename, 'w') as json_file:
                json.dump(data, json_file)
            
            # JSON 파일을 다운로드할 수 있도록 제공
            return send_file(json_filename, as_attachment=True)
        else:
            # API 요청이 실패한 경우 오류 메시지를 반환
            return f"Error: API response error - {data}", 400
    else:
        return "Error: Unable to get access token", 400

# 3. 인가 코드를 사용해 액세스 토큰을 요청하는 함수
def get_access_token(code):
    # 요청에 필요한 데이터 (x-www-form-urlencoded 형식)
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri
    }

    # 요청 헤더 설정
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # POST 요청을 통해 토큰 요청
    response = requests.post(token_url, headers=headers, data=payload)

    # 결과 처리
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 200:
        token_data = response.json()
        return token_data.get('access_token')
    else:
        print(f"Error: Unable to retrieve access token. Status: {response.status_code}, Message: {response.text}")
        return None

# 4. 액세스 토큰을 사용해 API를 호출하는 함수
def call_api(access_token):
    # API 호출 기간 설정
    start_date = '2023-06-01T00:00:00+09:00'
    end_date = '2024-09-30T23:59:59+09:00'

    # API 요청 시 사용할 파라미터
    params = {
        'start': start_date,
        'end': end_date
    }

    # 요청 헤더 설정 (Bearer 인증)
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # 디버깅: API 요청 URL과 파라미터 출력
    print(f"Request URL: {api_url}")
    print(f"Request Params: {params}")
    print(f"Request Headers: {headers}")

    # GET 요청 전송
    response = requests.get(api_url, headers=headers, params=params)

    # 디버깅: API 응답 상태 코드 및 내용 출력
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Text: {response.text}")

    # 결과 처리
    if response.status_code == 200 and response.text:
        try:
            data = response.json()
            if not data:
                print("Response is an empty list or data.")
            return data
        except ValueError:
            print("Failed to decode JSON response.")
            return {"error": "Invalid JSON format in response"}
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return {"error": f"Error: {response.status_code}, {response.text}"}

# 메인 실행 부분
if __name__ == '__main__':
    # OAuth 인증 요청을 브라우저에서 띄움
    open_browser_for_oauth()
    # Flask 웹 서버 실행 (localhost:5000에서 대기)
    app.run(port=5000)
