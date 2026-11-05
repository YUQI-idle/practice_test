import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from question_bank import QUESTION_BANK

app = Flask(__name__)
app.config["DATABASE"] = os.environ.get(
    "MATH_APP_DB", str(Path(__file__).with_name("learning.db"))
)
database_path = Path(app.config["DATABASE"])
secret_path = Path(
    os.environ.get("MATH_APP_SECRET_FILE", str(database_path.with_name(".flask_secret")))
)
secret_path.parent.mkdir(parents=True, exist_ok=True)
try:
    secret_fd = os.open(
        secret_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
except FileExistsError:
    pass
else:
    with os.fdopen(secret_fd, "w", encoding="utf-8") as secret_file:
        secret_file.write(secrets.token_hex(32))
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secret_path.read_text(
    encoding="utf-8"
).strip()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
)

COURSE = [
    {
        "slug": "algebra-functions",
        "module": "수학 기초",
        "title": "대수와 함수",
        "summary": "식의 계산, 방정식, 함수와 그래프를 복습합니다.",
        "content": [
            "함수는 각 입력값 x에 출력값 y를 하나씩 대응시키는 규칙입니다. 예를 들어 f(x) = 2x + 1이면 x에 3을 넣었을 때 f(3) = 7입니다.",
            "공학수학에서는 식을 정리하고 함수를 읽는 일이 계속 반복됩니다. 함수의 입력과 출력을 구분하고, 간단한 일차·이차방정식을 풀 수 있도록 연습합니다.",
        ],
        "question": "f(x) = 2x + 1일 때 f(3)은 얼마인가요?",
        "choices": ["5", "6", "7", "8"],
        "answer": 2,
        "explanation": "x 대신 3을 대입하면 f(3) = 2 × 3 + 1 = 7입니다.",
    },
    {
        "slug": "exponents-logarithms",
        "module": "수학 기초",
        "title": "지수와 로그",
        "summary": "지수법칙과 로그의 의미를 익힙니다.",
        "content": [
            "지수는 같은 수를 반복해서 곱하는 것을 간단히 나타냅니다. aᵐ × aⁿ = aᵐ⁺ⁿ이고, (aᵐ)ⁿ = aᵐⁿ입니다.",
            "로그 logₐ(b)는 a를 몇 제곱해야 b가 되는지 묻는 표현입니다. 따라서 log₂(8) = 3입니다. 지수·로그는 성장, 감쇠, 신호 크기와 미분방정식에 자주 등장합니다.",
        ],
        "question": "log₂(8)의 값은 무엇인가요?",
        "choices": ["2", "3", "4", "8"],
        "answer": 1,
        "explanation": "2³ = 8이므로 log₂(8) = 3입니다.",
    },
    {
        "slug": "trigonometry",
        "module": "수학 기초",
        "title": "삼각함수",
        "summary": "라디안, 사인·코사인과 주기적인 변화를 배웁니다.",
        "content": [
            "삼각함수는 각도와 원 위의 좌표를 연결합니다. 단위원에서 각 θ에 해당하는 점의 좌표는 (cos θ, sin θ)입니다.",
            "미적분과 공학수학에서는 각도를 라디안으로 쓰는 것이 기본입니다. 한 바퀴는 2π 라디안이며 sin(x), cos(x)는 파동과 진동을 설명하는 대표적인 주기 함수입니다.",
        ],
        "question": "sin(π/2)의 값은 무엇인가요?",
        "choices": ["-1", "0", "1/2", "1"],
        "answer": 3,
        "explanation": "단위원에서 π/2는 위쪽 점 (0, 1)에 해당하므로 sin(π/2) = 1입니다.",
    },
    {
        "slug": "limits",
        "module": "미적분",
        "title": "극한과 연속",
        "summary": "함수의 값이 한 점에 가까워질 때의 변화를 이해합니다.",
        "content": [
            "lim(x→a) f(x)는 x가 a에 가까워질 때 f(x)가 가까워지는 값을 뜻합니다. 극한은 x=a에서의 실제 함수값과 다를 수도 있습니다.",
            "함수가 a에서 연속이려면 f(a)가 정의되어 있고, lim(x→a) f(x) = f(a)여야 합니다. 미분은 극한을 이용해 정의됩니다.",
        ],
        "question": "x가 2에 가까워질 때 x + 3의 극한은 얼마인가요?",
        "choices": ["2", "3", "5", "존재하지 않음"],
        "answer": 2,
        "explanation": "다항식은 연속이므로 x=2를 대입하여 2+3=5를 얻습니다.",
    },
    {
        "slug": "derivatives",
        "module": "미적분",
        "title": "미분의 정의와 기본 공식",
        "summary": "순간 변화율과 도함수를 계산합니다.",
        "content": [
            "미분계수는 한 점에서의 순간 변화율이며 그래프에서는 접선의 기울기입니다. f′(x) = lim(h→0) [f(x+h)-f(x)]/h로 정의합니다.",
            "거듭제곱 함수의 미분은 d(xⁿ)/dx = n xⁿ⁻¹입니다. 예를 들어 x³의 도함수는 3x²입니다. 상수의 미분은 0입니다.",
        ],
        "question": "f(x) = x³일 때 f′(x)는 무엇인가요?",
        "choices": ["x²", "2x", "3x²", "3x³"],
        "answer": 2,
        "explanation": "거듭제곱 미분법에 따라 지수 3을 앞으로 내리고 지수를 1 줄여 3x²입니다.",
    },
    {
        "slug": "derivative-applications",
        "module": "미적분",
        "title": "미분의 응용",
        "summary": "접선, 증가·감소, 최댓값과 최솟값을 살펴봅니다.",
        "content": [
            "도함수 f′(x)의 부호가 양수인 구간에서 f는 증가하고, 음수인 구간에서 감소합니다. f′(x)=0인 점은 극값 후보가 됩니다.",
            "미분은 속도(위치의 시간 미분), 최적화, 근삿값 계산에 쓰입니다. 후보점과 구간의 양 끝에서 함수값을 비교하면 닫힌 구간의 최댓값·최솟값을 찾을 수 있습니다.",
        ],
        "question": "위치 s(t)를 시간 t로 미분하면 무엇을 구하나요?",
        "choices": ["가속도", "속도", "거리", "시간"],
        "answer": 1,
        "explanation": "속도는 위치의 시간에 대한 변화율이므로 v(t)=s′(t)입니다.",
    },
    {
        "slug": "integrals",
        "module": "미적분",
        "title": "적분의 기본",
        "summary": "부정적분과 정적분, 미적분학의 기본정리를 익힙니다.",
        "content": [
            "부정적분은 미분하면 주어진 함수가 되는 함수들의 모음입니다. ∫xⁿ dx = xⁿ⁺¹/(n+1) + C (n≠-1)이며 C는 적분상수입니다.",
            "정적분은 누적량과 부호를 가진 넓이를 나타냅니다. 미적분학의 기본정리에 따라 ∫[a,b] f(x)dx = F(b)-F(a)이며 F′=f입니다.",
        ],
        "question": "∫ 2x dx의 부정적분은 무엇인가요?",
        "choices": ["x + C", "x² + C", "2x² + C", "2 + C"],
        "answer": 1,
        "explanation": "x²을 미분하면 2x이므로 부정적분은 x²+C입니다.",
    },
    {
        "slug": "integral-applications",
        "module": "미적분",
        "title": "적분의 응용",
        "summary": "넓이, 누적 변화량과 평균값을 계산합니다.",
        "content": [
            "속도 v(t)를 시간 구간에서 적분하면 위치의 변화량을 얻습니다. 속도가 항상 양수라면 이동 거리와 같지만, 방향이 바뀌면 거리는 |v(t)|를 적분해야 합니다.",
            "두 곡선 사이의 넓이는 위쪽 함수에서 아래쪽 함수를 뺀 뒤 적분합니다. 적분 구간과 곡선의 위아래 관계를 먼저 확인하세요.",
        ],
        "question": "속도 v(t)를 구간 [a,b]에서 적분한 값은 무엇을 나타내나요?",
        "choices": ["가속도의 변화량", "위치의 변화량", "평균 속도", "시간의 변화량"],
        "answer": 1,
        "explanation": "위치의 변화량은 속도를 시간에 대해 적분한 값입니다.",
    },
    {
        "slug": "sequences-series",
        "module": "미적분",
        "title": "수열과 급수",
        "summary": "무한급수와 테일러 급수의 기초를 배웁니다.",
        "content": [
            "급수는 수열의 항들을 더한 것입니다. 무한급수의 수렴 여부는 부분합의 극한으로 판단합니다.",
            "기하급수 1+r+r²+…는 |r|<1일 때 1/(1-r)로 수렴합니다. 테일러 급수는 함수 근처의 값을 다항식으로 근사해 미분방정식과 수치 계산에 활용합니다.",
        ],
        "question": "1 + 1/2 + 1/4 + 1/8 + …의 합은 무엇인가요?",
        "choices": ["1", "2", "수렴하지 않음", "무한대"],
        "answer": 1,
        "explanation": "첫 항 1, 공비 1/2인 기하급수의 합은 1/(1-1/2)=2입니다.",
    },
    {
        "slug": "linear-algebra",
        "module": "공학수학",
        "title": "벡터와 선형대수",
        "summary": "벡터, 행렬과 연립일차방정식을 다룹니다.",
        "content": [
            "벡터는 크기와 방향을 가진 양이며, 여러 성분을 가진 순서쌍으로 표현할 수 있습니다. 내적은 두 벡터의 방향 관계와 투영을 계산하는 데 쓰입니다.",
            "행렬은 선형 변환과 연립방정식을 표현합니다. Ax=b를 풀 때 행렬의 역행렬이 존재하면 x=A⁻¹b로 쓸 수 있습니다. 실제 계산은 가우스 소거법이 널리 쓰입니다.",
        ],
        "question": "벡터 (1, 2)와 (3, 4)의 내적은 무엇인가요?",
        "choices": ["7", "10", "11", "14"],
        "answer": 2,
        "explanation": "(1,2)·(3,4)=1×3+2×4=11입니다.",
    },
    {
        "slug": "multivariable-calculus",
        "module": "공학수학",
        "title": "다변수 미적분",
        "summary": "편미분과 다중적분으로 여러 변수의 변화를 살펴봅니다.",
        "content": [
            "여러 변수의 함수에서 편미분은 다른 변수들을 고정하고 한 변수에 대해서만 미분하는 것입니다. 예를 들어 f(x,y)=x²y이면 ∂f/∂x=2xy입니다.",
            "기울기 벡터 ∇f는 함수가 가장 빠르게 증가하는 방향을 가리킵니다. 이 개념은 최적화, 열전달, 전자기학 등에서 중요합니다.",
        ],
        "question": "f(x,y)=x²+y일 때 x에 대한 편미분은 무엇인가요?",
        "choices": ["2x", "2x+y", "x²", "1"],
        "answer": 0,
        "explanation": "y를 상수로 보고 x²을 미분하면 2x입니다.",
    },
    {
        "slug": "vector-calculus",
        "module": "공학수학",
        "title": "벡터 미적분",
        "summary": "발산, 회전과 선적분의 의미를 익힙니다.",
        "content": [
            "벡터장은 공간의 각 점에 벡터를 대응합니다. 발산(divergence)은 한 점에서 벡터장이 바깥으로 퍼져 나오는 정도를 나타냅니다.",
            "회전(curl)은 벡터장이 주변에서 회전하는 경향을 나타냅니다. 가우스 발산정리와 스토크스 정리는 영역 적분과 경계 적분을 연결합니다.",
        ],
        "question": "벡터장의 발산은 무엇을 나타내나요?",
        "choices": ["바깥으로 퍼지거나 모이는 정도", "곡선의 길이", "함수의 최댓값", "벡터의 단위"],
        "answer": 0,
        "explanation": "발산은 작은 영역에서 벡터장이 얼마나 순유출되는지 나타내는 스칼라입니다.",
    },
    {
        "slug": "differential-equations",
        "module": "공학수학",
        "title": "미분방정식",
        "summary": "미지 함수와 그 도함수 사이의 관계를 풉니다.",
        "content": [
            "미분방정식은 미지 함수와 하나 이상의 도함수 사이의 관계를 나타냅니다. dy/dx=ky의 해는 y=Ce^(kx)이며 초기 조건으로 상수 C를 정합니다.",
            "미분방정식은 운동, 회로, 개체 수 변화, 열과 같은 시스템을 모델링합니다. 해를 구한 뒤 초기 조건과 원래 식에 대입해 확인하는 습관이 중요합니다.",
        ],
        "question": "dy/dx=2y의 일반해는 무엇인가요?",
        "choices": ["y=C+2x", "y=Ce^(2x)", "y=2Ce^x", "y=Cx²"],
        "answer": 1,
        "explanation": "dy/y=2dx를 적분하면 ln|y|=2x+C이고, 따라서 y=Ce^(2x)입니다.",
    },
    {
        "slug": "laplace-transform",
        "module": "공학수학",
        "title": "라플라스 변환",
        "summary": "미분방정식을 대수방정식으로 바꾸는 변환을 배웁니다.",
        "content": [
            "라플라스 변환은 시간 함수 f(t)를 복소 변수 s의 함수 F(s)로 바꿉니다. 미분을 s에 대한 대수식으로 바꿔 초기값 문제를 풀기 쉽게 만듭니다.",
            "단위 계단 함수와 지연 성질은 스위치가 있는 시스템이나 입력이 늦게 시작되는 시스템을 나타냅니다. 계산 후 역변환해 시간 영역의 해를 얻습니다.",
        ],
        "question": "상수 함수 1 (t≥0)의 라플라스 변환은 무엇인가요?",
        "choices": ["1", "s", "1/s", "s²"],
        "answer": 2,
        "explanation": "∫₀∞ e^(-st)dt = 1/s (s>0)이므로 변환은 1/s입니다.",
    },
    {
        "slug": "fourier-series",
        "module": "공학수학",
        "title": "푸리에 급수와 변환",
        "summary": "신호를 사인파와 주파수 성분으로 분석합니다.",
        "content": [
            "푸리에 급수는 적절한 주기 함수를 사인과 코사인의 합으로 표현합니다. 복잡한 주기 신호도 여러 주파수 성분의 합으로 볼 수 있습니다.",
            "푸리에 변환은 비주기 신호까지 주파수 영역에서 분석하도록 확장합니다. 신호 처리, 진동 분석, 열방정식에서 폭넓게 사용됩니다.",
        ],
        "question": "푸리에 분석에서 주로 사용하는 기본 파형 조합은 무엇인가요?",
        "choices": ["직선과 포물선", "사인과 코사인", "로그와 지수", "행렬과 벡터"],
        "answer": 1,
        "explanation": "푸리에 급수와 변환은 사인·코사인(또는 복소 지수) 성분으로 신호를 표현합니다.",
    },
    {
        "slug": "complex-numbers",
        "module": "공학수학",
        "title": "복소수와 복소함수",
        "summary": "복소수의 극형식과 오일러 공식을 익힙니다.",
        "content": [
            "복소수 z=a+bi에서 i²=-1입니다. 극형식으로는 z=r(cos θ+i sin θ)라고 쓸 수 있습니다.",
            "오일러 공식 e^(iθ)=cos θ+i sin θ는 삼각함수와 지수함수를 연결합니다. 교류 회로와 파동을 계산할 때 진폭과 위상을 간결하게 표현하게 해줍니다.",
        ],
        "question": "i²의 값은 무엇인가요?",
        "choices": ["1", "-1", "i", "-i"],
        "answer": 1,
        "explanation": "허수 단위 i는 i²=-1을 만족하도록 정의됩니다.",
    },
]

BASE_STYLE = """
<style>
  :root { color-scheme: light; font-family: system-ui, sans-serif; color: #172033; background: #f3f6fb; }
  * { box-sizing: border-box; }
  body { max-width: 1000px; margin: 0 auto; padding: 32px 20px 64px; line-height: 1.65; }
  a { color: #075985; }
  header { margin-bottom: 24px; }
  header a { text-decoration: none; font-weight: 700; }
  h1, h2, h3 { line-height: 1.3; }
  .hero, .panel, .lesson-card { background: white; border: 1px solid #dce4ef; border-radius: 14px; padding: 22px; }
  .hero { border-top: 5px solid #0284c7; margin-bottom: 20px; }
  .muted, .meta { color: #526174; }
  .course-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
  .lesson-card { display: block; color: inherit; text-decoration: none; }
  .lesson-card:hover { border-color: #0284c7; transform: translateY(-1px); }
  .lesson-card p { margin-bottom: 0; }
  .badge { display: inline-block; padding: 2px 9px; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: .85rem; }
  .done { background: #dcfce7; color: #166534; }
  .locked { opacity: .7; }
  .lesson-content { white-space: pre-line; }
  .question-card { margin: 16px 0; padding: 18px; border: 1px solid #dce4ef; border-radius: 10px; }
  .choices { display: grid; gap: 10px; margin: 16px 0; }
  label.choice { display: flex; gap: 10px; padding: 10px 12px; border: 1px solid #dce4ef; border-radius: 8px; }
  .difficulty { margin-top: 24px; padding-bottom: 6px; border-bottom: 1px solid #dce4ef; }
  button { border: 0; border-radius: 8px; padding: 10px 18px; background: #0369a1; color: white; font: inherit; cursor: pointer; }
  button:hover { background: #075985; }
  .notice { margin: 14px 0; padding: 12px 16px; border-radius: 8px; background: #ecfeff; }
  .notice.error { background: #fff7ed; }
  .progress-track { height: 10px; border-radius: 999px; background: #e2e8f0; overflow: hidden; }
  .progress-bar { height: 100%; background: #0284c7; }
  @media (max-width: 520px) { body { padding: 20px 14px 40px; } .hero, .panel { padding: 17px; } }
</style>
"""

HOME_PAGE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>수학 스텝업</title>""" + BASE_STYLE + """</head><body>
<header><a href="{{ url_for('home') }}">수학 스텝업</a>
  <span class="meta"> · {{ session_username }}</span>
  <form method="post" action="{{ url_for('logout') }}" style="display:inline">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <button type="submit">로그아웃</button>
  </form>
</header>
{% for category, message in get_flashed_messages(with_categories=true) %}
  <p class="notice {% if category == 'error' %}error{% endif %}">{{ message }}</p>
{% endfor %}
<section class="hero">
  <span class="badge">나의 학습 계획</span>
  <h1>미적분부터 공학수학까지, 한 단계씩</h1>
  <p>{{ profile['goal'] }}를 목표로 기초부터 쌓아갑니다.</p>
  <p class="meta">현재 수준: {{ profile['level'] }} · 학습 시간: {{ profile['study_time'] }}</p>
  <div class="progress-track" aria-label="전체 진도">
    <div class="progress-bar" style="width: {{ progress_percent }}%"></div>
  </div>
  <p class="meta">{{ completed_count }} / {{ total_count }} 단계 완료 ({{ progress_percent }}%)</p>
</section>
{% for module, lessons in modules %}
<h2>{{ module }}</h2>
<div class="course-grid">
  {% for lesson in lessons %}
  <a class="lesson-card" href="{{ url_for('lesson_page', slug=lesson['slug']) }}">
    <span class="badge {% if lesson['completed'] %}done{% endif %}">
      {% if lesson['completed'] %}완료{% else %}{{ loop.index }}단계{% endif %}
    </span>
    <h3>{{ lesson['title'] }}</h3>
    <p class="muted">{{ lesson['summary'] }}</p>
  </a>
  {% endfor %}
</div>
{% endfor %}
<section class="panel" style="margin-top:24px">
  <h2>학습 프로필과 저장 정보</h2>
  <p>학습 프로필, 단계별 진도, 퀴즈 점수는 이 프로젝트의 SQLite 데이터베이스에 저장됩니다.</p>
  <p class="meta">DB 파일: {{ database_name }} · 저장된 퀴즈 시도: {{ attempt_count }}회</p>
</section>
</body></html>
"""

LESSON_PAGE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ lesson['title'] }} - 수학 스텝업</title>""" + BASE_STYLE + """</head><body>
<header><a href="{{ url_for('home') }}">← 전체 학습 단계</a>
  <span class="meta"> · {{ session_username }}</span>
  <form method="post" action="{{ url_for('logout') }}" style="display:inline">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <button type="submit">로그아웃</button>
  </form>
</header>
{% for category, message in get_flashed_messages(with_categories=true) %}
  <p class="notice {% if category == 'error' %}error{% endif %}">{{ message }}</p>
{% endfor %}
<main class="hero">
  <span class="badge">{{ lesson['module'] }}</span>
  <h1>{{ lesson['title'] }}</h1>
  <p class="muted">{{ lesson['summary'] }}</p>
  {% for paragraph in lesson['content'] %}
  <p class="lesson-content">{{ paragraph }}</p>
  {% endfor %}
</main>
<section class="panel">
  <h2>확인 문제 · {{ questions|length }}문제</h2>
  <p class="muted">난이도별로 세 문제씩 풀어보세요. 답을 선택하고 <strong>답 확인</strong>을 누르면 정답과 해설을 볼 수 있습니다.</p>
  {% for difficulty in difficulties %}
    <h3 class="difficulty">{{ difficulty }} <span class="meta">({{ question_groups[difficulty]|length }}문제)</span></h3>
    {% for question in question_groups[difficulty] %}
    <article class="question-card">
      <h4>{{ loop.index }}. {{ question['prompt'] }}</h4>
      <form method="post" action="{{ url_for('submit_quiz', slug=lesson['slug']) }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="hidden" name="question_id" value="{{ question['id'] }}">
        <div class="choices">
        {% for choice in question['choices'] %}
          <label class="choice">
            <input type="radio" name="answer" value="{{ loop.index0 }}" required
              {% if question['latest_attempt'] and question['latest_attempt']['selected_answer'] == loop.index0 %}checked{% endif %}>
            {{ choice }}
          </label>
        {% endfor %}
        </div>
        <button type="submit">답 확인</button>
      </form>
      {% if question['latest_attempt'] %}
      <p class="notice {% if not question['latest_attempt']['is_correct'] %}error{% endif %}">
        {% if question['latest_attempt']['is_correct'] %}정답입니다!{% else %}다시 생각해 보세요.{% endif %}
        정답: <strong>{{ question['choices'][question['answer']] }}</strong><br>
        {{ question['explanation'] }}
      </p>
      {% endif %}
    </article>
    {% endfor %}
  {% endfor %}
  {% if lesson['completed'] %}
  <p class="notice">이 단계의 모든 문제가 완료됐어요. 다시 풀어도 진도 기록은 유지됩니다.</p>
  {% endif %}
</section>
<section class="panel" style="margin-top:16px">
  <h2>이전 학습 기록</h2>
  {% if attempts %}
  <ul>{% for attempt in attempts %}
    <li>{{ attempt['created_at'] }} · {{ attempt['difficulty'] or '이전' }} {{ attempt['question_position'] or '' }}{% if attempt['question_position'] %}번{% endif %} · {{ '정답' if attempt['is_correct'] else '오답' }}</li>
  {% endfor %}</ul>
  {% else %}<p class="muted">아직 제출한 답안이 없습니다.</p>{% endif %}
</section>
</body></html>
"""

AUTH_PAGE = """
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ '가입' if mode == 'register' else '로그인' }} - 수학 스텝업</title>""" + BASE_STYLE + """</head><body>
<header><a href="{{ url_for('login') }}">수학 스텝업</a></header>
<main class="panel">
  <h1>{{ '계정 만들기' if mode == 'register' else '로그인' }}</h1>
  {% if not request.is_secure %}
  <p class="notice error">현재 HTTP 연결입니다. 실습용 비밀번호만 사용하고, 다른 서비스에서 쓰는 비밀번호는 입력하지 마세요. 실제 사용자 계정은 HTTPS 설정 후 이용해야 합니다.</p>
  {% endif %}
  {% for category, message in get_flashed_messages(with_categories=true) %}
    <p class="notice {% if category == 'error' %}error{% endif %}">{{ message }}</p>
  {% endfor %}
  {% if error %}<p class="notice error">{{ error }}</p>{% endif %}
  <form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <p><label>아이디 (영문, 숫자, 밑줄 / 3~32자)<br>
      <input name="username" minlength="3" maxlength="32" pattern="[A-Za-z0-9_]{3,32}" required autocomplete="username">
    </label></p>
    <p><label>비밀번호 (12자 이상)<br>
      <input type="password" name="password" minlength="12" maxlength="256" required
        autocomplete="{{ 'new-password' if mode == 'register' else 'current-password' }}">
    </label></p>
    {% if mode == 'login' %}<input type="hidden" name="next" value="{{ next_url }}">{% endif %}
    <button type="submit">{{ '가입하고 시작하기' if mode == 'register' else '로그인' }}</button>
  </form>
  {% if mode == 'register' %}
    <p>이미 계정이 있나요? <a href="{{ url_for('login') }}">로그인</a></p>
  {% else %}
    <p>계정이 없나요? <a href="{{ url_for('register') }}">회원가입</a></p>
  {% endif %}
</main>
</body></html>
"""


def get_db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database():
    connection = get_db()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    database_path = Path(app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS learner_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                level TEXT NOT NULL,
                goal TEXT NOT NULL,
                study_time TEXT NOT NULL,
                data_scope TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                module TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                content_json TEXT NOT NULL,
                question TEXT NOT NULL,
                choices_json TEXT NOT NULL,
                answer INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                position INTEGER NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS progress (
                lesson_id INTEGER PRIMARY KEY REFERENCES lessons(id),
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id),
                selected_answer INTEGER NOT NULL,
                is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS lesson_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id),
                difficulty TEXT NOT NULL CHECK (difficulty IN ('쉬움', '중간', '어려움')),
                position INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                choices_json TEXT NOT NULL,
                answer INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                UNIQUE (lesson_id, difficulty, position)
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                level TEXT NOT NULL,
                goal TEXT NOT NULL,
                study_time TEXT NOT NULL,
                data_scope TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                completed_at TEXT,
                PRIMARY KEY (user_id, lesson_id)
            );
            CREATE TABLE IF NOT EXISTS user_quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
                question_id INTEGER REFERENCES lesson_questions(id) ON DELETE SET NULL,
                selected_answer INTEGER NOT NULL,
                is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_quiz_attempts_question
                ON user_quiz_attempts (user_id, question_id, id);
            """
        )
        attempt_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(quiz_attempts)")
        }
        if "question_id" not in attempt_columns:
            db.execute(
                "ALTER TABLE quiz_attempts ADD COLUMN question_id INTEGER REFERENCES lesson_questions(id)"
            )
        db.execute(
            """
            INSERT OR IGNORE INTO learner_profile (id, level, goal, study_time, data_scope)
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                "고등수학 기초부터",
                "공학수학 독학, AI/머신러닝 수학 기초",
                "1시간",
                "학습 프로필, 단원 진도, 퀴즈 점수",
            ),
        )
        for position, lesson in enumerate(COURSE, start=1):
            db.execute(
                """
                INSERT OR IGNORE INTO lessons
                    (slug, module, title, summary, content_json, question,
                     choices_json, answer, explanation, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lesson["slug"],
                    lesson["module"],
                    lesson["title"],
                    lesson["summary"],
                    json.dumps(lesson["content"], ensure_ascii=False),
                    lesson["question"],
                    json.dumps(lesson["choices"], ensure_ascii=False),
                    lesson["answer"],
                    lesson["explanation"],
                    position,
                ),
            )
            lesson_id = db.execute(
                "SELECT id FROM lessons WHERE slug = ?", (lesson["slug"],)
            ).fetchone()["id"]
            for difficulty, questions in QUESTION_BANK[lesson["slug"]].items():
                for question_position, item in enumerate(questions, start=1):
                    db.execute(
                        """
                        INSERT OR IGNORE INTO lesson_questions
                            (lesson_id, difficulty, position, prompt, choices_json,
                             answer, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            lesson_id,
                            difficulty,
                            question_position,
                            item["prompt"],
                            json.dumps(item["choices"], ensure_ascii=False),
                            item["answer"],
                            item["explanation"],
                        ),
                    )
        db.execute(
            """
            INSERT OR IGNORE INTO progress (lesson_id)
            SELECT id FROM lessons
            """
        )


def initialize_user_data(db, user_id):
    profile = db.execute(
        "SELECT level, goal, study_time, data_scope FROM learner_profile WHERE id = 1"
    ).fetchone()
    if profile is None:
        profile = (
            "고등수학 기초부터",
            "공학수학 독학, AI/머신러닝 수학 기초",
            "1시간",
            "학습 프로필, 단원 진도, 퀴즈 점수",
        )
    db.execute(
        """
        INSERT INTO user_profiles (user_id, level, goal, study_time, data_scope)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, *profile),
    )
    db.execute(
        "INSERT INTO user_progress (user_id, lesson_id) SELECT ?, id FROM lessons",
        (user_id,),
    )


def load_lesson(row):
    lesson = dict(row)
    lesson["content"] = json.loads(lesson.pop("content_json"))
    lesson["completed"] = bool(lesson.pop("completed"))
    return lesson


init_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.full_path))
        return view(**kwargs)

    return wrapped_view


def csrf_protect(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if request.method == "POST":
            submitted_token = request.form.get("csrf_token", "")
            expected_token = session.get("_csrf_token", "")
            if not expected_token or not hmac.compare_digest(
                submitted_token.encode("utf-8"), expected_token.encode("utf-8")
            ):
                abort(
                    400,
                    description="요청 검증에 실패했습니다. 페이지를 새로고침해 주세요.",
                )
        return view(**kwargs)

    return wrapped_view


@app.context_processor
def inject_template_context():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return {
        "csrf_token": session["_csrf_token"],
        "session_username": session.get("username"),
    }


def safe_next_url(target):
    parsed = urlsplit(target)
    if (
        "\\" in target
        or parsed.scheme
        or parsed.netloc
        or not parsed.path.startswith("/")
        or parsed.path.startswith("//")
    ):
        return ""
    return target


@app.route("/register", methods=["GET", "POST"])
@csrf_protect
def register():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "GET":
        return render_template_string(AUTH_PAGE, mode="register", error=None, next_url="")

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    if not re.fullmatch(r"[a-z0-9_]{3,32}", username):
        return render_template_string(
            AUTH_PAGE,
            mode="register",
            error="아이디는 영문 소문자, 숫자, 밑줄로 3~32자여야 합니다.",
            next_url="",
        ), 400
    if not 12 <= len(password) <= 256:
        return render_template_string(
            AUTH_PAGE,
            mode="register",
            error="비밀번호는 12~256자로 입력해 주세요.",
            next_url="",
        ), 400

    with database() as db:
        existing_user = db.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing_user:
            return render_template_string(
                AUTH_PAGE,
                mode="register",
                error="이미 사용 중인 아이디입니다.",
                next_url="",
            ), 409
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        user_id = cursor.lastrowid
        initialize_user_data(db, user_id)

    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    flash("가입이 완료됐어요. 나만의 학습 진도를 시작해 보세요.")
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
@csrf_protect
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    next_url = safe_next_url(request.values.get("next", ""))
    if request.method == "GET":
        return render_template_string(
            AUTH_PAGE, mode="login", error=None, next_url=next_url
        )

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    with database() as db:
        user = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template_string(
            AUTH_PAGE,
            mode="login",
            error="아이디 또는 비밀번호를 확인해 주세요.",
            next_url=next_url,
        ), 401

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(next_url or url_for("home"))


@app.route("/logout", methods=["POST"])
@csrf_protect
@login_required
def logout():
    session.clear()
    flash("로그아웃했습니다.")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    with database() as db:
        user_id = session["user_id"]
        profile = db.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        rows = db.execute(
            """
            SELECT lessons.slug, lessons.module, lessons.title, lessons.summary,
                   user_progress.completed
            FROM lessons
            JOIN user_progress
              ON user_progress.lesson_id = lessons.id
             AND user_progress.user_id = ?
            ORDER BY lessons.position
            """,
            (user_id,),
        ).fetchall()
        attempt_count = db.execute(
            "SELECT COUNT(*) FROM user_quiz_attempts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

    grouped = {}
    for row in rows:
        grouped.setdefault(row["module"], []).append(dict(row))
    completed_count = sum(row["completed"] for row in rows)
    total_count = len(rows)
    modules = list(grouped.items())
    return render_template_string(
        HOME_PAGE,
        profile=profile,
        modules=modules,
        completed_count=completed_count,
        total_count=total_count,
        progress_percent=round(completed_count * 100 / total_count) if total_count else 0,
        attempt_count=attempt_count,
        database_name=Path(app.config["DATABASE"]).name,
        result=request.args.get("result"),
    )


@app.route("/lessons/<slug>")
@login_required
def lesson_page(slug):
    user_id = session["user_id"]
    with database() as db:
        row = db.execute(
            """
            SELECT lessons.*, user_progress.completed
            FROM lessons
            JOIN user_progress
              ON user_progress.lesson_id = lessons.id
             AND user_progress.user_id = ?
            WHERE lessons.slug = ?
            """,
            (user_id, slug),
        ).fetchone()
        if row is None:
            abort(404)
        lesson = load_lesson(row)
        attempts = db.execute(
            """
            SELECT user_quiz_attempts.is_correct, user_quiz_attempts.created_at,
                   lesson_questions.difficulty, lesson_questions.position
            FROM user_quiz_attempts
            LEFT JOIN lesson_questions ON lesson_questions.id = user_quiz_attempts.question_id
            WHERE user_quiz_attempts.user_id = ?
              AND user_quiz_attempts.lesson_id = (SELECT id FROM lessons WHERE slug = ?)
            ORDER BY user_quiz_attempts.id DESC LIMIT 10
            """,
            (user_id, slug),
        ).fetchall()
        question_rows = db.execute(
            """
            SELECT lesson_questions.*,
                   latest.selected_answer AS latest_selected_answer,
                   latest.is_correct AS latest_is_correct
            FROM lesson_questions
            LEFT JOIN (
                SELECT question_id, selected_answer, is_correct
                FROM user_quiz_attempts
                WHERE id IN (
                    SELECT MAX(id) FROM user_quiz_attempts
                    WHERE user_id = ? AND question_id IS NOT NULL GROUP BY question_id
                )
            ) AS latest ON latest.question_id = lesson_questions.id
            WHERE lesson_questions.lesson_id = (
                SELECT id FROM lessons WHERE slug = ?
            )
            ORDER BY
                CASE lesson_questions.difficulty
                    WHEN '쉬움' THEN 1 WHEN '중간' THEN 2 ELSE 3
                END,
                lesson_questions.position
            """,
            (user_id, slug),
        ).fetchall()

    difficulties = ("쉬움", "중간", "어려움")
    question_groups = {difficulty: [] for difficulty in difficulties}
    for row in question_rows:
        question = dict(row)
        question["choices"] = json.loads(question.pop("choices_json"))
        question["latest_attempt"] = None
        if question["latest_is_correct"] is not None:
            question["latest_attempt"] = {
                "selected_answer": question["latest_selected_answer"],
                "is_correct": bool(question["latest_is_correct"]),
            }
        question.pop("latest_selected_answer")
        question.pop("latest_is_correct")
        question_groups[question["difficulty"]].append(question)

    return render_template_string(
        LESSON_PAGE,
        lesson=lesson,
        attempts=attempts,
        difficulties=difficulties,
        question_groups=question_groups,
        questions=question_rows,
    )


@app.route("/lessons/<slug>/quiz", methods=["POST"])
@csrf_protect
@login_required
def submit_quiz(slug):
    answer_value = request.form.get("answer", "")
    question_value = request.form.get("question_id", "")
    with database() as db:
        question_row = db.execute(
            """
            SELECT lesson_questions.id, lesson_questions.lesson_id,
                   lesson_questions.answer, lesson_questions.choices_json
            FROM lesson_questions
            JOIN lessons ON lessons.id = lesson_questions.lesson_id
            WHERE lessons.slug = ? AND lesson_questions.id = ?
            """,
            (slug, question_value),
        ).fetchone()
        if question_row is None:
            abort(404)
        try:
            selected_answer = int(answer_value)
        except ValueError:
            abort(400, description="답안을 선택해 주세요.")
        if not 0 <= selected_answer < len(json.loads(question_row["choices_json"])):
            abort(400, description="유효하지 않은 답안입니다.")

        is_correct = selected_answer == question_row["answer"]
        db.execute(
            """
            INSERT INTO user_quiz_attempts
                (user_id, lesson_id, question_id, selected_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                question_row["lesson_id"],
                question_row["id"],
                selected_answer,
                int(is_correct),
            ),
        )
        incomplete_count = db.execute(
            """
            SELECT COUNT(*)
            FROM lesson_questions
            WHERE lesson_id = ?
              AND NOT EXISTS (
                  SELECT 1 FROM user_quiz_attempts
                  WHERE user_quiz_attempts.user_id = ?
                    AND user_quiz_attempts.question_id = lesson_questions.id
                    AND user_quiz_attempts.is_correct = 1
              )
            """,
            (question_row["lesson_id"], session["user_id"]),
        ).fetchone()[0]
        if incomplete_count == 0:
            db.execute(
                """
                UPDATE user_progress
                SET completed = 1, completed_at = CURRENT_TIMESTAMP
                WHERE lesson_id = ? AND user_id = ?
                """,
                (question_row["lesson_id"], session["user_id"]),
            )
    return redirect(url_for("lesson_page", slug=slug))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
