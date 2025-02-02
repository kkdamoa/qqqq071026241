import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains  # 추가된 import
from selenium.webdriver.common.keys import Keys  # 추가된 import
import time
import json
import requests
from bs4 import BeautifulSoup

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Chrome 프로필 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    profile_path = os.path.join(script_dir, 'chrome_profile')
    if os.path.exists(profile_path):
        options.add_argument(f'--user-data-dir={profile_path}')
        print("Chrome profile loaded")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    # 저장된 쿠키 로드
    cookies_path = os.path.join(script_dir, 'band_cookies.json')
    if (os.path.exists(cookies_path)):
        driver.get('https://band.us')
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    continue
        print("Cookies loaded")
        driver.refresh()
    
    return driver

def get_url_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # meta 태그에서 description 추출
        description = soup.find('meta', {'name': 'description'})
        if (description):
            return description.get('content', '')
        
        # 본문 텍스트 추출
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text() for p in paragraphs])
        return content.strip()
        
    except Exception as e:
        print(f"URL 내용 가져오기 실패: {str(e)}")
        return url

def login(driver, config):
    try:
        print("\n=== 로그인 시도 중 ===")
        driver.get('https://auth.band.us/login')
        print("로그인 페이지 로드됨")
        time.sleep(3)
        
        # 이메일 로그인 버튼 클릭
        email_login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.uButtonRound.-h56.-icoType.-email'))
        )
        email_login_btn.click()
        print("이메일 로그인 버튼 클릭됨")
        
        # 이메일 입력
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'input_email'))
        )
        email_input.send_keys(config['email'])
        print(f"이메일 입력됨: {config['email'][:3]}***@***")
        
        email_confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.uBtn.-tcType.-confirm'))
        )
        email_confirm_btn.click()
        print("이메일 확인 버튼 클릭됨")
        
        # 비밀번호 입력
        pw_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'pw'))
        )
        pw_input.send_keys(config['password'])
        print("비밀번호 입력됨")
        
        pw_confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.uBtn.-tcType.-confirm'))
        )
        pw_confirm_btn.click()
        print("비밀번호 확인 버튼 클릭됨")
        
        # 2차 인증 처리
        try:
            verification_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, 'code'))
            )
            print("\n=== 2차 인증 필요 ===")
            verification_code = input("이메일로 받은 인증 코드를 입력해주세요: ")
            verification_input.send_keys(verification_code)
            print("인증 코드 입력됨")
            
            verify_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.uBtn.-tcType.-confirm'))
            )
            verify_btn.click()
            print("인증 코드 확인 버튼 클릭됨")
            time.sleep(5)
        except:
            print("2차 인증 없음 - 로그인 진행")
        
        # 로그인 성공 후 메인 페이지 로딩 대기
        WebDriverWait(driver, 30).until(
            EC.url_to_be("https://band.us/")
        )
        print("\n✅ 로그인 성공!")
        
    except Exception as e:
        print(f"\n❌ 로그인 실패: {str(e)}")
        raise e

def post_to_band(driver, config, band_info):
    try:
        print(f"\n=== '{band_info['name']}' 밴드에 포스팅 시도 중 ===")
        
        # 여러번 시도하는 재시도 메커니즘 추가
        max_retries = 3
        for retry in range(max_retries):
            try:
                # 밴드로 이동
                driver.get(band_info['url'])
                print(f"밴드 페이지 로드됨: {band_info['url']}")
                
                # 페이지 완전 로딩 대기 시간 증가
                time.sleep(15)  # 10초에서 15초로 증가
                
                # 명시적인 페이지 로드 상태 확인
                WebDriverWait(driver, 20).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )

                # 페이지 새로고침 시도
                if retry > 0:
                    driver.refresh()
                    time.sleep(10)
                
                # 글쓰기 버튼이 있는지 확인
                write_buttons = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'button._btnPostWrite'))
                )
                
                if not write_buttons:
                    raise Exception("글쓰기 버튼을 찾을 수 없습니다")
                
                # 스크롤을 최상단으로 이동
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                # JavaScript로 글쓰기 버튼 클릭
                driver.execute_script("arguments[0].click();", write_buttons[0])
                print("글쓰기 버튼 클릭됨")
                time.sleep(5)
                
                # 에디터 찾기 및 작성
                editor = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
                )
                
                # 에디터를 한번 클릭하고 내용을 지움
                driver.execute_script("arguments[0].click();", editor)
                driver.execute_script("arguments[0].innerHTML = '';", editor)
                time.sleep(2)
                
                # 제목 입력 (JavaScript 사용)
                if config.get('title'):
                    driver.execute_script(
                        "arguments[0].innerHTML += arguments[1] + '<br>';", 
                        editor, 
                        config['title']
                    )
                    time.sleep(2)
                
                # URL 입력 (JavaScript 사용)
                post_url = config['post_url']
                driver.execute_script(
                    "arguments[0].innerHTML += arguments[1];", 
                    editor, 
                    post_url
                )
                time.sleep(2)
                
                # Enter 키 이벤트 발생
                ActionChains(driver).key_down(Keys.ENTER).key_up(Keys.ENTER).perform()
                print("URL 미리보기 로딩 중... (15초)")
                time.sleep(15)
                
                # URL 텍스트 삭제
                driver.execute_script("""
                    var editor = arguments[0];
                    var url = arguments[1];
                    editor.innerHTML = editor.innerHTML.replace(url, '');
                    editor.innerHTML = editor.innerHTML.replace(/^\\n|\\n$/g, '');
                    editor.innerHTML = editor.innerHTML.trim();
                """, editor, post_url)
                time.sleep(2)
                
                # 게시 버튼 클릭
                submit_btns = driver.find_elements(By.CSS_SELECTOR, 'button.uButton.-sizeM._btnSubmitPost.-confirm')
                if submit_btns:
                    driver.execute_script("arguments[0].click();", submit_btns[0])
                    time.sleep(5)
                    
                    # 게시판 선택 팝업 처리
                    try:
                        # ...existing code for popup handling...
                        pass
                    except Exception as e:
                        print(f"게시판 선택 처리 중 오류 (무시됨): {str(e)}")
                    
                    print("포스팅 성공!")
                    time.sleep(random.uniform(20, 30))  # 대기 시간 증가
                    return True
                    
                raise Exception("게시 버튼을 찾을 수 없습니다")
                
            except Exception as e:
                print(f"시도 {retry + 1}/{max_retries} 실패: {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(30)  # 재시도 전 30초 대기
                    continue
                raise
                
    except Exception as e:
        print(f"\n❌ '{band_info['name']}' 밴드 포스팅 실패: {str(e)}")
        time.sleep(45)  # 실패 시 대기 시간 증가
        return False

def normal_posting_process(driver, config):
    """일반적인 포스팅 프로세스"""
    try:
        print("\n=== 포스팅 프로세스 시작 ===")
        # 로그인
        login(driver, config)
        
        # 밴드 목록 가져오기
        print("\n=== 밴드 목록 수집 중 ===")
        driver.get('https://band.us/feed')
        print("피드 페이지 로드됨")
        time.sleep(3)

        # "내 밴드 더보기" 버튼을 찾아서 클릭
        try:
            more_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button.myBandMoreView._btnMore'))
            )
            print("'내 밴드 더보기' 버튼 발견")
            driver.execute_script("arguments[0].click();", more_btn)
            print("'내 밴드 더보기' 버튼 클릭됨")
            time.sleep(2)  # 밴드 목록이 로드될 때까지 대기
        except Exception as e:
            print("'내 밴드 더보기' 버튼을 찾을 수 없거나 이미 모든 밴드가 표시되어 있습니다.")
        
        band_list = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-viewname="DMyGroupBandBannerView.MyGroupBandListView"]'))
        )
        
        # 모든 밴드 항목 찾기
        band_items = band_list.find_elements(By.CSS_SELECTOR, 'li[data-viewname="DMyGroupBandListItemView"]')
        band_elements = []
        
        for item in band_items:
            try:
                band_link = item.find_element(By.CSS_SELECTOR, 'a.itemMyBand')
                band_name = item.find_element(By.CSS_SELECTOR, 'span.body strong.ellipsis').text.strip()
                band_url = band_link.get_attribute('href')
                
                if (band_url and band_name):
                    band_elements.append({
                        'name': band_name,
                        'url': band_url
                    })
                    print(f"밴드 발견: {band_name} ({band_url})")
            except Exception as e:
                continue
        
        # URL 기준으로 내림차순 정렬 (높은 숫자가 먼저 오도록)
        band_elements.sort(key=lambda x: int(x['url'].split('/')[-1]), reverse=True)
        
        total = len(band_elements)
        if (total > 0):
            print(f"총 {total}개의 밴드를 찾았습니다.")
            print(f"첫 번째 밴드: {band_elements[0]['name']} ({band_elements[0]['url']})")
            print(f"마지막 밴드: {band_elements[-1]['name']} ({band_elements[-1]['url']})")
        else:
            print("밴드를 찾을 수 없습니다.")
            return 1

        # 각 밴드에 글 작성
        success_count = 0
        for i, band_info in enumerate(band_elements, 1):
            print(f"\n=== 밴드 {i}/{total} 진행 중 ===")
            if post_to_band(driver, config, band_info):
                success_count += 1
            time.sleep(10)  # 각 밴드 간 대기 시간
        
        print(f"\n=== 최종 결과 ===")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {total - success_count}개")
        print(f"총 밴드 수: {total}개")
        print("=== 포스팅 프로세스 완료 ===\n")
        return 0
        
    except Exception as e:
        print(f"\n❌ 포스팅 프로세스 실패: {str(e)}")
        return 1

def main():
    try:
        print("===== 밴드 자동 포스팅 시작 =====")
        print("\n1. 설정 및 인증 데이터 로드 중...")
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 밴드 URL 목록 로드
        if os.path.exists('band_urls.json'):
            with open('band_urls.json', 'r', encoding='utf-8') as f:
                config['bands'] = json.load(f)
                print(f"밴드 URL 로드 완료: {len(config['bands'])}개")

        print(f"이메일: {config['email'][:3]}***")
        print(f"URL: {config['post_url']}")
        print(f"제목: {config['title']}")
        
        print("\n2. Chrome 드라이버 설정 중...")
        
        # Chrome 프로필 경로 설정 (밴드 폴더 사용)
        profile_path = os.path.abspath(os.path.join('밴드', 'chrome_profile'))
        print(f"Chrome 프로필 경로: {profile_path}")
        
        if not os.path.exists(profile_path):
            print("⚠️ chrome_profile 폴더가 없습니다.")
            print("band_auto_poster.py를 실행하여 로그인 세션을 생성해주세요.")
            return 1
            
        options = Options()
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument('--profile-directory=Default')
        # headless 모드 제거
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--ignore-certificate-errors')  # SSL 인증서 검증 비활성화
        
        driver = webdriver.Chrome(options=options)
        print("Chrome 드라이버 시작됨 (기존 프로필 사용)")
        
        try:
            return normal_posting_process(driver, config)
            
        finally:
            print("\n브라우저 종료")
            driver.quit()
            
    except Exception as e:
        print(f"\n❌ 치명적 오류 발생: {str(e)}")
        return 1

if __name__ == "__main__":
    print("===== 밴드 자동 포스팅 시작 =====")
    sys.exit(main())
