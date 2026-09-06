import os
import json
import requests
import xml.etree.ElementTree as ET
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

APP_NAME = "AutoBloggerPro"

def get_trending_keyword():
    url = "[https://trends.google.co.kr/trends/trendingsearches/daily/rss?geo=KR](https://trends.google.co.kr/trends/trendingsearches/daily/rss?geo=KR)"
    res = requests.get(url)
    root = ET.fromstring(res.text)
    keywords = [item.find('title').text for item in root.findall('.//item')]
    
    blog_rss = "[https://smart-tip-2026.blogspot.com/feeds/posts/default?alt=rss](https://smart-tip-2026.blogspot.com/feeds/posts/default?alt=rss)"
    blog_res = requests.get(blog_rss)
    blog_content = blog_res.text if blog_res.status_code == 200 else ""

    for kw in keywords:
        if kw not in blog_content:
            return kw
    return keywords[0] if keywords else "최신 생활 정보"

def get_unsplash_images(keyword):
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    default_img_html = """
    <p style="text-align:center;">
      <img src="[https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=800](https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=800)" alt="기본 이미지" style="max-width:100%; height:auto; border-radius:8px;" />
    </p>
    """
    if not access_key:
        return default_img_html, default_img_html

    url = f"[https://api.unsplash.com/search/photos?query=](https://api.unsplash.com/search/photos?query=){keyword}&per_page=2&orientation=landscape&client_id={access_key}"
    res = requests.get(url)
    if res.status_code != 200:
        return default_img_html, default_img_html

    data = res.json()
    results = data.get("results", [])
    img_htmls = []
    
    for photo in results[:2]:
        img_url = photo["urls"]["regular"]
        download_location = photo["links"]["download_location"]
        try:
            requests.get(f"{download_location}&client_id={access_key}")
        except Exception:
            pass

        photographer_name = photo["user"]["name"]
        photographer_url = f"{photo['user']['links']['html']}?utm_source={APP_NAME}&utm_medium=referral"
        unsplash_url = f"[https://unsplash.com/?utm_source=](https://unsplash.com/?utm_source=){APP_NAME}&utm_medium=referral"
        
        html_block = f"""
        <div style="text-align:center; margin: 20px 0;">
          <img src="{img_url}" alt="{keyword}" style="max-width:100%; height:auto; border-radius:8px;" />
          <br/>
          <span style="font-size:0.8em; color:#666;">
            Photo by <a href="{photographer_url}" target="_blank" rel="noopener">{photographer_name}</a> on <a href="{unsplash_url}" target="_blank" rel="noopener">Unsplash</a>
          </span>
        </div>
        """
        img_htmls.append(html_block)

    while len(img_htmls) < 2:
        img_htmls.append(default_img_html)

    return img_htmls[0], img_htmls[1]

# ⭐ 에러 처리 및 JSON 정제 로직이 강화된 핵심 부분
def generate_viral_content(keyword, img_html1, img_html2):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("🚨 오류: GEMINI_API_KEY가 없습니다. GitHub Secrets를 확인하세요.")
        exit(1)

    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){gemini_key}"
    
    prompt = f"""
    당신은 월 1,000만 원 이상의 수익을 올리는 전문 블로그 에디터입니다.
    키워드: '{keyword}'

    [본문 구성 및 지침]
    1. 제목: 클릭률(CTR)을 높이는 흥미롭고 명확한 제목
    2. 본문 HTML 포맷 작성 규칙:
       - 상단에 준비된 대표 이미지 HTML 세트를 그대로 배치:
         {img_html1}
       - 서론: 독자의 문제 상황에 깊이 공감하고 질문을 던지며 시작 (체류시간 증가 유도)
       - 소제목 <h2> 2개, <h3> 2개 이상 구성
       - 중간 부분에 서브 이미지 HTML 세트를 그대로 배치:
         {img_html2}
       - 가독성을 위한 <b>강조 표시</b> 및 <ul>, <li> 리스트 사용
       - 문장은 1~2줄마다 줄바꿈 (<br/> 또는 <p> 분리)
       - '결론적으로', '요약하자면' 같은 인공지능 상투어 절대 금지. 사람이 작성한 듯 자연스러운 어조.

    [응답 형식]
    JSON 형태로 반환해 주세요:
    {{
      "title": "글 제목",
      "content": "HTML 본문 내용"
    }}
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    res = requests.post(url, json=payload)
    result = res.json()
    
    # 1. API 응답 에러 사전 차단
    if res.status_code != 200:
        print(f"🚨 Gemini API 통신 오류 (상태 코드: {res.status_code})")
        print(f"상세 에러: {json.dumps(result, indent=2, ensure_ascii=False)}")
        exit(1)

    try:
        text_res = result['candidates'][0]['content']['parts'][0]['text']
        # 2. AI가 마크다운을 붙여서 보낼 경우 텍스트 정제
        text_res = text_res.strip().removeprefix("```json").removesuffix("```").strip()
        text_res = text_res.removeprefix("```").strip()
        
        return json.loads(text_res)
    except KeyError:
        print(f"🚨 AI 응답 구조 이상: {json.dumps(result, indent=2, ensure_ascii=False)}")
        exit(1)
    except json.JSONDecodeError:
        print(f"🚨 JSON 파싱 에러 (AI 응답 텍스트): {text_res}")
        exit(1)

def post_to_blogger(title, content):
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("BLOGGER_REFRESH_TOKEN"),
        client_id=os.getenv("BLOGGER_CLIENT_ID"),
        client_secret=os.getenv("BLOGGER_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    service = build('blogger', 'v3', credentials=creds)
    blog_id = os.getenv("BLOGGER_BLOG_ID")
    body = {"kind": "blogger#post", "title": title, "content": content}
    
    posts = service.posts()
    response = posts.insert(blogId=blog_id, body=body).execute()
    print(f"성공적으로 포스팅되었습니다! URL: {response.get('url')}")

if __name__ == "__main__":
    keyword = get_trending_keyword()
    print(f"✅ 선정된 키워드: {keyword}")
    
    img_html1, img_html2 = get_unsplash_images(keyword)
    post_data = generate_viral_content(keyword, img_html1, img_html2)
    
    post_to_blogger(post_data['title'], post_data['content'])
