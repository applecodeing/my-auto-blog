import os
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai

# 1. Gemini API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 GitHub Secrets에 설정되지 않았습니다.")

genai.configure(api_key=GEMINI_API_KEY)

# 2. 구글 트렌드 RSS 키워드 추출
def get_trending_keyword():
    try:
        rss_url = "https://trends.google.co.kr/trends/trendingsearches/daily/rss?geo=KR"
        feed = feedparser.parse(rss_url)
        if feed.entries:
            return feed.entries[0].title
    except Exception as e:
        print(f"키워드 추출 중 오류 발생: {e}")
    return "스마트폰 유용한 설정 팁"

# 3. Gemini 글 작성
def generate_seo_article(keyword):
    # 현재 정상 작동하는 gemini-1.5-flash 모델로 변경
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    너는 구글 애드센스 수익을 극대화하는 전문 블로그 에디터야.
    오늘의 키워드는 '{keyword}'이다. 이 키워드와 연관된 IT/앱/스마트폰/생활 꿀팁 주제로 블로그 글을 작성해줘.

    [작성 규칙]
    1. 제목: 검색 클릭률(CTR)을 높이는 매력적인 제목 (50자 이내)
    2. 본문 구조: <h2>, <h3> HTML 태그를 사용하고 <table> 표나 <ul> 불릿 포인트를 활용할 것.
    3. 분량: 공백 포함 1,500자 이상 작성할 것.
    4. 출력 형식: 첫 줄에는 [제목]만 쓰고, 둘째 줄부터는 HTML 본문 코드로만 작성할 것.
    """
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    lines = text.split('\n')
    title = lines[0].replace('[제목]', '').replace('#', '').strip()
    body = '\n'.join(lines[1:]).strip()
    
    return title, body

# 4. 이메일 발송
def send_to_blogger(title, body_html):
    blogger_email = os.environ.get("BLOGGER_SECRET_EMAIL")
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_APP_PASS")
    
    msg = MIMEMultipart("alternative")
    msg['Subject'] = title
    msg['From'] = sender_email
    msg['To'] = blogger_email
    
    html_part = MIMEText(body_html, 'html')
    msg.attach(html_part)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, blogger_email, msg.as_string())
    print("성공적으로 게시되었습니다.")

if __name__ == "__main__":
    keyword = get_trending_keyword()
    print(f"추출된 키워드: {keyword}")
    title, body = generate_seo_article(keyword)
    send_to_blogger(title, body)
