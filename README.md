# 수학 스텝업

Flask와 SQLite로 만든 단계별 수학 학습 프로그램입니다. 고등수학 기초에서 시작해 미적분과 공학수학까지 이어집니다.

## 현재 학습 계획

- 현재 수준: 고등수학 기초부터
- 목표: 공학수학 독학, AI/머신러닝 수학 기초
- 학습 시간: 1시간
- 저장 항목: 학습 프로필, 단계별 진도, 퀴즈 점수

## 실행 방법

프로젝트 폴더에서 다음을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. 가상환경이 아직 없다면 먼저 `py -m venv .venv`를 실행합니다.

## 학습 단계

1. 대수와 함수
2. 지수와 로그
3. 삼각함수
4. 극한과 연속
5. 미분의 정의와 기본 공식
6. 미분의 응용
7. 적분의 기본
8. 적분의 응용
9. 수열과 급수
10. 벡터와 선형대수
11. 다변수 미적분
12. 벡터 미적분
13. 미분방정식
14. 라플라스 변환
15. 푸리에 급수와 변환
16. 복소수와 복소함수

각 단계에서 개념을 읽고 문제를 풉니다. 문제는 **쉬움·중간·어려움별 3개씩, 총 9개**입니다. 답을 선택하고 `답 확인`을 누르면 정답 여부와 해설이 표시되며 시도 내역이 저장됩니다. 한 챕터의 9문제를 모두 한 번 이상 맞히면 해당 챕터의 진도가 완료됩니다.

## 데이터베이스

첫 실행 시 프로젝트 폴더에 `learning.db` SQLite 파일과 테이블이 자동으로 생성됩니다. DB에는 학습 프로필, 강의 내용, 난이도별 문제, 완료 여부와 문제별 퀴즈 답안 기록이 저장됩니다. 기존 DB가 있으면 문제 테이블을 추가하고 이전 학습 프로필과 기록은 유지합니다. DB 파일은 `.gitignore`에 포함되어 GitHub에 올라가지 않습니다.

다른 위치의 DB 파일을 사용하려면 `MATH_APP_DB` 환경 변수를 지정합니다.

```powershell
$env:MATH_APP_DB = "C:\경로\learning.db"
.\.venv\Scripts\python.exe app.py
```

## 가입과 개인별 진도

방문자는 회원가입 후 로그인해야 학습 페이지에 들어갈 수 있습니다. 아이디와 비밀번호는 각각 1~100자이며, 이메일·전화번호 인증이나 추가 확인 없이 바로 가입할 수 있습니다. 계정에 이메일 주소도 요구하지 않습니다. 아이디는 계정마다 중복될 수 없고, 비밀번호는 해시로 저장됩니다. 서로 다른 사용자가 우연히 같은 비밀번호를 고를 수는 있지만, 다른 계정에 접속하려면 그 계정의 아이디와 비밀번호가 모두 필요합니다. 학습 프로필, 진도, 답안 기록은 계정별 SQLite 테이블에 분리됩니다. 기존의 공용 기록은 작성자를 식별할 수 없어 계정에 옮기지 않습니다. 기존 계정과 새 계정 모두 개인 진도는 새로 시작하며, 기존 공용 기록은 앱에서 더 이상 표시하지 않습니다. 비밀번호 분실 시 재설정 기능은 아직 없습니다.

별도의 DB 서버는 필요하지 않습니다. 앱과 SQLite 파일이 VM에서 같이 실행되는 실습/소규모 구성입니다. SQLite 파일은 앱 재시작 뒤에도 같은 경로에 남아 있어야 합니다.

세션 서명 키는 최초 실행 시 DB 옆의 `.flask_secret` 파일에 생성되며 Git에서 제외됩니다. 이 파일은 비밀로 보관하고 지우거나 바꾸지 마세요. 잃어버리면 모든 사용자가 다시 로그인해야 합니다. VM에서는 앱을 실행하는 계정만 읽을 수 있도록 파일 권한을 보호하세요.

> **중요: 현재 Azure 실습 주소는 HTTP입니다.** HTTP에서는 로그인 비밀번호와 세션 쿠키가 전송 중 암호화되지 않습니다. 이 주소에서 실제/재사용 비밀번호를 사용하지 말고, 다른 사용자를 받기 전에 HTTPS를 설정하세요. 인터넷 공개 운영 환경에서는 HTTPS, 계정 잠금/비밀번호 재설정, 백업과 운영용 WSGI 서버도 필요합니다.

## 관리자와 학습 기록

가입 화면에는 아이디, 로그인 시각, 답안과 진도가 운영자에게 보일 수 있다고 안내합니다. 앱은 가입·로그인·로그아웃 시각과 문제 답안/정오답을 기록합니다. IP 주소, 기기 정보, 비밀번호는 관리자 로그에 저장하지 않습니다.

관리자 아이디는 `1`이며 일반 가입에 사용할 수 없습니다. 관리자 기능은 기본적으로 꺼져 있습니다. HTTPS가 적용된 SSH 전용 터널을 준비한 후 `ADMIN_ENABLED=1`과 VM의 `ADMIN_PASSWORD` 환경변수를 설정해야 활성화됩니다. 비밀번호는 실습용으로 1~100자까지 허용하므로 `1`을 쓸 수도 있지만, 관리자 비밀번호는 공개 HTTP 페이지에서 입력하지 마세요. 로그인 정보는 비밀번호 해시로 저장됩니다.

도메인이 없는 이번 실습에서는 Nginx가 **VM 내부의 `127.0.0.1:8443`에서만** 자체 서명 HTTPS를 제공하고, VM의 SSH 포트 포워딩을 통해 본인 PC의 `https://localhost:8443`으로 연결합니다. Nginx 설정은 [deploy/nginx-math-admin.conf](./deploy/nginx-math-admin.conf)에 있습니다. 공용 IP의 8000 포트는 계속 일반 학습 페이지(HTTP)용이며, 이 경로에서 관리자 아이디 `1` 로그인을 시도하면 차단됩니다. 공개 HTTP 페이지에선 학습자 로그인 정보가 암호화되지 않으므로 실습용 계정만 사용하세요.

### Azure VM에 관리자 터널 설정

1. SSH로 VM에 접속합니다. 현재 앱 서버가 실행 중이면 해당 터미널에서 `Ctrl+C`로 중지하고 최신 코드를 받습니다.

   ```bash
   cd ~/practice_test
   git pull origin main
   sudo apt update
   sudo apt install -y nginx openssl
   ```

2. VM 안에서만 쓸 localhost 인증서를 만듭니다.

   ```bash
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout /etc/ssl/private/math-admin.key \
     -out /etc/ssl/certs/math-admin.crt \
     -subj '/CN=localhost' \
     -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
   sudo chmod 600 /etc/ssl/private/math-admin.key
   ```

3. Nginx 설정을 설치하고 검사한 뒤 다시 불러옵니다.

   ```bash
   sudo cp deploy/nginx-math-admin.conf /etc/nginx/sites-available/math-admin
   sudo ln -s /etc/nginx/sites-available/math-admin /etc/nginx/sites-enabled/math-admin
   sudo nginx -t
   sudo systemctl reload nginx
   ```

   Nginx가 `127.0.0.1:8443`에만 바인딩하므로 Azure NSG에 8443 인바운드 포트를 열지 않습니다.

4. 같은 SSH 터미널에서 관리자 기능과 실습 비밀번호를 설정하고 앱을 실행합니다.

   ```bash
   export ADMIN_ENABLED=1
   export ADMIN_PASSWORD=1
   export SESSION_COOKIE_SECURE=1
   export TRUST_PROXY=1
   source .venv/bin/activate
   python app.py
   ```

   `ADMIN_PASSWORD=1`은 SSH 터널 안에서만 쓰는 일회성 실습 비밀번호입니다. 이미 일반 계정이 아이디 `1`을 사용 중이면 앱은 그 계정을 관리자 계정으로 탈취하지 않고 시작을 거부합니다.

5. **내 Windows PC의 로컬 PowerShell/VS Code 터미널**에서 별도 터미널을 열고 SSH 포트 포워딩을 시작합니다. 개인 키 경로와 VM 사용자 이름을 실제 값으로 바꾸세요. 이 터미널은 접속하는 동안 계속 켜둡니다.

   ```powershell
   ssh -i "C:\키파일\경로\이름.pem" -N -L 8443:127.0.0.1:8443 azureuser@20.196.64.236
   ```

6. 내 PC 브라우저에서 `https://localhost:8443/login`을 엽니다. 자체 서명 인증서 경고가 표시되면 localhost 인증서가 이 VM에서 만든 것인지 확인한 뒤에만 계속 진행하고, 아이디 `1`, 비밀번호 `1`로 로그인합니다. 로그인 후 **관리자** 메뉴에서 활동을 볼 수 있습니다.

터널이나 앱을 종료하려면 각각의 실행 터미널에서 `Ctrl+C`를 누릅니다. 이 구성이 관리 화면 접근을 SSH 터널로 제한하지만, 공개 학습 사이트 자체는 여전히 HTTP입니다.

## Azure VM에 변경 내용 반영하기

코드를 GitHub에 push한 뒤 VM의 SSH 터미널에서 기존 서버를 `Ctrl+C`로 중지하고 다음을 실행합니다.

```bash
cd ~/practice_test
git pull origin main
source .venv/bin/activate
python app.py
```

앱이 다시 시작될 때 새 문제 테이블, 144개 문제와 사용자별/활동 로그 테이블이 자동으로 추가됩니다. 기존 DB와 공용 기록은 유지되지만, 기록을 소유자별로 나눌 수 없어 새 계정으로 옮기지 않습니다. 이후 계정별 기록은 사용자별 테이블에 저장됩니다. 첫 실행 시 `.flask_secret`도 생성되므로 DB와 함께 보존하세요. 서버를 실행한 터미널을 열어 둔 상태에서 브라우저를 새로고침하세요.

현재 프로젝트는 학습 진도와 퀴즈를 확인하기 위한 실습용 앱입니다. 공개 운영 시에는 위 HTTPS 설정과 운영용 웹 서버 구성이 필요합니다.
