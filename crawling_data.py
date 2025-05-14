import os
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from dateutil.parser import parse
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 나이, 성별 그룹 설정
AGE_GROUPS = {
    'TEENAGE': '10대',
    'TWENTIES': '20대',
    'THIRTIES': '30대',
    'FORTIES': '40대',
    'FIFTY': '50대'
}

GENDERS = {
    'FEMALE': '여성',
    'MALE': '남성'
}

today_str = datetime.now().strftime('%y%m%d')
base_filename = f'./data/daily_{today_str}.csv'

if os.path.exists(base_filename):
    print(f"daily_{today_str} 파일이 이미 존재합니다.")
    exit()

# 크롬 드라이버 설정
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
driver = webdriver.Chrome(options=chrome_options)

contents = []
visited_urls = set()
page_count = 0

# OTT 플랫폼 목록
PLATFORMS = {
    'netflix': 'netflix',
    'tving': 'tving',
    'coupang': 'coupangplay',
    'wavve': 'wavve',
    'disney': 'disneyplus',
    'watcha': 'watcha',
    'boxoffice': 'boxoffice'
}

def select_age_gender(driver, age_group, gender):
    """
    브라우저에서 나이와 성별 선택을 위한 함수
    """
    try:
        # 나이-성별 선택 버튼 클릭
        age_gender_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".age-gender-select__button"))
        )
        age_gender_button.click()
        time.sleep(1)  
        
        # 나이 그룹 선택
        age_radio = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f"label.radio-button[name='ageGroup'][value='{age_group}'] input"))
        )
        age_radio.click()
        
        # 성별 선택
        gender_radio = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f"label.radio-button[name='gender'][value='{gender}'] input"))
        )
        gender_radio.click()
        
        # 확인 버튼 클릭
        confirm_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".modal-footer button.button--primary"))
        )
        confirm_button.click()
        
        time.sleep(2) 
        return True
    except Exception as e:
        print(f"나이 {age_group}와 성별 {gender} 선택 중 오류 발생: {str(e)}")
        return False

def scrape_ranking_data(period='', age_group=None, gender=None):
    """
    주어진 기간과 나이, 성별에 따라 각 플랫폼의 랭킹 데이터를 스크래핑
    """
    all_contents = []
    base_url = "https://www.kinolights.com/ranking/{platform}"
    if period:
        base_url += f"?period={period}"
    
    for platform_name, platform_url in PLATFORMS.items():
        url = base_url.format(platform=platform_url)
        driver.get(url)
        time.sleep(3)
        
        # 나이, 성별 그룹이 있는 경우 가져오기
        if age_group and gender:
            success = select_age_gender(driver, age_group, gender)
            if not success:
                print(f"{platform_name}에서 나이/성별 설정 실패, 기본값으로 진행합니다.")
        
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            ranking_items = soup.find_all('div', class_='content-list-card content-list-card--md')
            print(f"{platform_name}에서 {len(ranking_items)}개 항목 발견 (나이: {AGE_GROUPS.get(age_group, '전체')}, 성별: {GENDERS.get(gender, '전체')})")
            
            for item in ranking_items:
                try:
                    rank = item.select_one('.ranking-item__number .rank__number').text.strip()
                    title = item.select_one('.info__title').text.strip()
                    subtitle = item.select_one('.info__subtitle').text.strip()
                    genre, year = subtitle.split(' · ')
                    score = item.select_one('.score__number').text.strip()
                    
                    all_contents.append({
                        'rank': int(rank),
                        'title': title,
                        'genre': genre,
                        'year': year,
                        'score': float(score),
                        'platform': platform_name,
                        'age_group': AGE_GROUPS.get(age_group, '전체'),
                        'gender': GENDERS.get(gender, '전체')
                    })
                except Exception as e:
                    print(f"항목 스크래핑 오류: {str(e)}")
                    continue
        except Exception as e:
            print(f"{platform_name}에서 랭킹 항목을 찾는 중 오류 발생: {str(e)}")
    
    return all_contents

def combine_duplicate_contents(contents):
    # 제목과 년도를 기준으로 그룹화
    content_dict = {}
    
    for content in contents:
        # 제목, 년도, 나이 그룹, 성별을 키로 사용하여 중복 방지
        key = (content['title'], content['year'], content['age_group'], content['gender'])
        if key not in content_dict:
            content_dict[key] = content
        else:
            # 이미 존재하는 콘텐츠의 플랫폼 정보에 현재 플랫폼 추가
            existing = content_dict[key]
            platforms = set(existing['platform'].split(', '))
            platforms.add(content['platform'])
            existing['platform'] = ', '.join(sorted(platforms))
    
    return list(content_dict.values())

def scrape_daily_content():
    """
    남성과 여성을 위한 일간 콘텐츠 랭킹 데이터를 수집하는 함수
    
    Returns:
        male_df: 남성 선호 콘텐츠 데이터프레임
        female_df: 여성 선호 콘텐츠 데이터프레임
    """
    if not os.path.exists('./data'):
        os.makedirs('./data')
    
    today_str = datetime.now().strftime('%y%m%d')
    
    try:
        # 남성과 여성 데이터를 위한 파일 생성
        male_contents = []
        female_contents = []
        
        # 각 성별에 대해 모든 나이 그룹 순회
        for gender_key, gender_value in GENDERS.items():
            for age_key, age_value in AGE_GROUPS.items():
                print(f"{age_value} {gender_value}의 일간 랭킹 스크래핑 중...")
                
                # 해당 나이 및 성별 조합에 대한 콘텐츠 가져오기
                contents = scrape_ranking_data('', age_key, gender_key)
                
                # 적절한 성별 컬렉션에 추가
                if contents:
                    combined = combine_duplicate_contents(contents)
                    print(f"{age_value} {gender_value}에서 {len(combined)}개 항목 발견")
                    
                    if gender_key == 'MALE':
                        male_contents.extend(combined)
                    else:  # FEMALE
                        female_contents.extend(combined)
        
        # 남성 데이터 파일 저장
        male_filename = f'./data/daily_MALE_{today_str}.csv'
        male_df = None
        if male_contents:
            male_df = pd.DataFrame(male_contents)
            male_df.to_csv(male_filename, index=False)
            print(f"{len(male_contents)}개 항목을 {male_filename}에 저장했습니다.")
        
        # 여성 데이터 파일 저장
        female_filename = f'./data/daily_FEMALE_{today_str}.csv'
        female_df = None
        if female_contents:
            female_df = pd.DataFrame(female_contents)
            female_df.to_csv(female_filename, index=False)
            print(f"{len(female_contents)}개 항목을 {female_filename}에 저장했습니다.")
            
        return male_df, female_df

    except Exception as e:
        print(f"일간 콘텐츠 랭킹 수집 중 오류 발생: {str(e)}")
        return None, None

def main():
    if not os.path.exists('./data'):
        os.makedirs('./data')
    
    try:
        # 남성과 여성 데이터를 위한 파일 생성
        male_contents = []
        female_contents = []
        
        # 각 성별에 대해 모든 나이 그룹 순회
        for gender_key, gender_value in GENDERS.items():
            for age_key, age_value in AGE_GROUPS.items():
                print(f"{age_value} {gender_value}의 일간 랭킹 스크래핑 중...")
                
                # 해당 나이 및 성별 조합에 대한 콘텐츠 가져오기
                contents = scrape_ranking_data('', age_key, gender_key)
                
                # 적절한 성별 컬렉션에 추가
                if contents:
                    combined = combine_duplicate_contents(contents)
                    print(f"{age_value} {gender_value}에서 {len(combined)}개 항목 발견")
                    
                    if gender_key == 'MALE':
                        male_contents.extend(combined)
                    else:  # FEMALE
                        female_contents.extend(combined)
        
        # 남성 데이터 파일 저장
        male_filename = f'./data/daily_MALE_{today_str}.csv'
        if male_contents:
            male_df = pd.DataFrame(male_contents)
            male_df.to_csv(male_filename, index=False)
            print(f"{len(male_contents)}개 항목을 {male_filename}에 저장했습니다.")
        
        # 여성 데이터 파일 저장
        female_filename = f'./data/daily_FEMALE_{today_str}.csv'
        if female_contents:
            female_df = pd.DataFrame(female_contents)
            female_df.to_csv(female_filename, index=False)
            print(f"{len(female_contents)}개 항목을 {female_filename}에 저장했습니다.")

    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
