import time
import pandas as pd
import requests
import re
import urllib.parse
from bs4 import BeautifulSoup

def normalize_names(name_text):
    """
    이름 데이터를 일관된 형식으로 정규화하는 함수
    모든 이름을 "A B C" 형식으로 변환 (공백으로 구분)
    """
    if not name_text:
        return None
    
    # HTML 태그 제거
    clean_text = re.sub(r'<[^>]+>', ' ', str(name_text))
    
    # 줄바꿈, 여러 공백을 단일 공백으로 변환
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # 이름 분리 및 재결합
    names = []
    
    # 쉼표로 구분된 경우 ("A, B, C")
    if ',' in clean_text:
        # 쉼표로 분리 후 각 이름 공백 제거
        parts = [name.strip() for name in clean_text.split(',')]
        # 각 이름이 여러 단어로 구성된 경우도 처리
        for part in parts:
            names.append(part)
    else:
        # 줄바꿈이 있는 경우
        if '\n' in clean_text:
            lines = clean_text.split('\n')
            for line in lines:
                if line.strip():
                    names.append(line.strip())
        else:
            # 이름이 공백 없이 붙어있는 경우 (예: 박지훈려운최민영)
            # 이 경우 원래 형태를 유지하고 공백으로 분리하지 않음
            names.append(clean_text)
    
    # 공백으로 구분된 형식으로 변환
    return ' '.join(names)

def collect_wikipedia_info(title, year):
    """
    위키백과에서 작품 정보를 수집하는 함수
    
    Args:
        title: 작품 제목
        year: 작품 연도
    
    Returns:
        딕셔너리 형태의 작품 정보
    """
    # 검색 결과를 저장할 정보 딕셔너리
    info = {
        'genre_detail': None,
        'director': None,
        'runtime': None,
        'streaming': None,
        'production': None,
        'rating': None,
        'broadcast_period': None,
        'episodes': None,
        'cast': None,
        'country': None,
        'language': None
    }
    
    # 여러 형태의 URL을 시도할 목록
    url_formats = [
        # 기본 제목
        f"{title}",
        # 제목_(연도년_영화) 형식
        f"{title}_({year}년_영화)",
        # 제목_(연도년_드라마) 형식
        f"{title}_({year}년_드라마)",
        # 제목_(연도) 형식
        f"{title}_({year})",
        # 제목 (연도) 형식
        f"{title} ({year})"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    # 각 URL 형식 시도
    for url_format in url_formats:
        try:
            # URL 인코딩
            encoded_title = urllib.parse.quote(url_format)
            wiki_url = f"https://ko.wikipedia.org/wiki/{encoded_title}"
            
            print(f"위키백과 URL 시도: {wiki_url}")
            
            # 위키백과 페이지 요청
            response = requests.get(wiki_url, headers=headers)
            
            # 성공적으로 페이지를 가져왔는지 확인
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 문서가 존재하지 않는 페이지인지 확인
                if "위키백과에 이 이름의 문서가 없습니다" in soup.text:
                    print(f"문서 없음: {wiki_url}")
                    continue
                
                # infobox 테이블 찾기
                infobox = soup.find('table', class_='infobox')
                
                if infobox:
                    print(f"정보 박스 발견: {wiki_url}")
                    # 모든 행 검색
                    rows = infobox.find_all('tr')
                    
                    for row in rows:
                        # 헤더 셀 찾기
                        th = row.find('th')
                        if not th:
                            continue
                        
                        header_text = th.get_text().strip()
                        td = row.find('td')
                        if not td:
                            continue
                        
                        value = td.get_text().strip()
                        
                        # 장르 정보 추출
                        if '장르' in header_text:
                            info['genre_detail'] = value
                            print(f"장르 찾음: {value}")
                        
                        # 연출/감독 정보 추출 및 이름 형식 통일
                        elif '연출' in header_text or '감독' in header_text:
                            info['director'] = normalize_names(value)
                            if info['director']:
                                print(f"감독 찾음: {info['director']}")
                        
                        # 방송 분량/상영 시간 추출
                        elif '방송 분량' in header_text or '상영 시간' in header_text or '러닝타임' in header_text:
                            info['runtime'] = value
                        
                        # 추가 채널/스트리밍 정보 추출
                        elif '추가 채널' in header_text or '스트리밍' in header_text:
                            info['streaming'] = value
                        
                        # 제작사 정보 추출
                        elif '제작사' in header_text:
                            info['production'] = value
                        
                        # 등급 정보 추출 (이미지로 표시될 수 있음)
                        elif '등급' in header_text:
                            # 텍스트로 된 등급 정보가 있는지 확인
                            if value:
                                info['rating'] = value
                            else:
                                # 이미지가 있는지 확인
                                rating_img = td.find('img')
                                if rating_img and rating_img.get('alt'):
                                    info['rating'] = rating_img.get('alt')
                        
                        # 방송 기간 정보 추출
                        elif '방송 기간' in header_text:
                            info['broadcast_period'] = value
                        
                        # 방송 횟수/에피소드 정보 추출
                        elif '방송 횟수' in header_text or '에피소드' in header_text:
                            info['episodes'] = value
                        
                        # 출연자 정보 추출 및 이름 형식 통일
                        elif '출연' in header_text or '주연' in header_text or '배우' in header_text:
                            info['cast'] = normalize_names(td.get_text())
                            if info['cast']:
                                print(f"출연자 찾음: {info['cast']}")
                            
                        # 국가 정보 추출
                        elif '국가' in header_text or '제작 국가' in header_text:
                            info['country'] = value
                            
                        # 언어 정보 추출
                        elif '언어' in header_text or '원어' in header_text:
                            info['language'] = value
                    
                    # 장르 정보가 있으면 추가 URL 시도 중단
                    if info['genre_detail']:
                        break
        except Exception as e:
            print(f"위키백과에서 '{url_format}' 정보 수집 중 오류 발생: {str(e)}")
    
    return info

def collect_missing_genres(titles_df):
    """
    제목 데이터프레임에서 상세 장르가 없는 항목을 찾아 수집하는 함수
    
    Args:
        titles_df: genre_detail이 없는 콘텐츠 정보가 포함된 데이터프레임
        
    Returns:
        상세 장르 정보가 업데이트된 데이터프레임
    """
    # 필요한 필드가 이미 데이터프레임에 있다고 가정 (main.py에서 생성됨)
    
    result_df = titles_df.copy()
    
    # 이미 genre_detail이 있는 행은 제외
    # 데이터프레임에 genre_detail이 있는지 확인하고 없는 행만 필터링
    missing_genres_df = result_df[result_df['genre_detail'].isna()]
    
    if missing_genres_df.empty:
        print("genre_detail이 없는 콘텐츠가 없습니다. 크롤링을 건너뜁니다.")
        return result_df
    
    print(f"{len(missing_genres_df)}개 콘텐츠의 genre_detail이 없어 크롤링을 시작합니다.")
    
    try:
        for idx, row in missing_genres_df.iterrows():
            title = row['title']
            year = row['year']
            
            print(f"[{idx+1}/{len(missing_genres_df)}] '{title}({year})' 정보 수집 중...")
            
            # 위키백과에서만 정보 수집 시도
            wiki_info = collect_wikipedia_info(title, year)
            
            # 위키백과에서 정보를 찾았다면 업데이트
            if wiki_info['genre_detail']:
                result_df.at[idx, 'genre_detail'] = wiki_info['genre_detail']
                print(f"위키백과에서 '{title}({year})' 장르 정보 찾음: {wiki_info['genre_detail']}")
            
            # 추가 정보도 저장 (이미 데이터프레임에 컬럼이 존재함)
            for key in wiki_info:
                if wiki_info[key] and key in result_df.columns:
                    result_df.at[idx, key] = wiki_info[key]
            
            # 과도한 요청 방지를 위한 대기
            time.sleep(1.5)
    except Exception as e:
        print(f"정보 수집 중 오류 발생: {str(e)}")
    
    return result_df

if __name__ == "__main__":
    import os
    
    # 기존 데이터에서 출연자와 감독 이름 형식 정규화
    if os.path.exists('./data/contents.csv'):
        contents_df = pd.read_csv('./data/contents.csv')
        
        # broadcast_channel 컬럼이 있으면 제거
        if 'broadcast_channel' in contents_df.columns:
            contents_df = contents_df.drop(columns=['broadcast_channel'])
            print("broadcast_channel 컬럼을 제거했습니다.")
        
        # 출연자 및 감독 이름이 있는 경우 형식 통일
        for field in ['cast', 'director']:
            if field in contents_df.columns:
                print(f"기존 {field} 정보 형식을 통일하는 중...")
                for idx, row in contents_df.iterrows():
                    if pd.notna(row[field]):
                        contents_df.at[idx, field] = normalize_names(row[field])
        
        # 업데이트된 데이터 저장
        contents_df.to_csv('./data/contents.csv', index=False)
        print("출연자 및 감독 정보 형식 통일 완료!")
        
        # 전체 콘텐츠 데이터를 위한 실행 코드
        missing_df = contents_df[contents_df['genre_detail'].isna()]
        
        if not missing_df.empty:
            print(f"{len(missing_df)}개의 콘텐츠에 대한 상세 장르와 추가 정보를 수집합니다...")
            print("이 작업은 시간이 오래 걸릴 수 있습니다.")
            
            # 한 번에 처리할 데이터 수
            batch_size = 20
            total_batches = (len(missing_df) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, len(missing_df))
                
                current_batch = missing_df.iloc[start_idx:end_idx].copy()
                print(f"\n=== 배치 {batch_num+1}/{total_batches} 처리 중 ({start_idx+1}~{end_idx} / {len(missing_df)}) ===")
                
                # 현재 배치의 상세 정보 수집
                updated_df = collect_missing_genres(current_batch)
                
                # 원본 데이터프레임 업데이트
                for idx, row in updated_df.iterrows():
                    mask = (contents_df['title'] == row['title']) & (contents_df['year'] == row['year'])
                    
                    # 모든 필드 업데이트 (broadcast_channel 제외)
                    for field in row.index:
                        if field != 'broadcast_channel' and field not in ['title', 'year', 'genre'] and pd.notna(row[field]):
                            contents_df.loc[mask, field] = row[field]
                
                # 각 배치마다 진행 상황을 저장
                contents_df.to_csv('./data/contents.csv', index=False)
                print(f"배치 {batch_num+1} 완료 - contents.csv 파일이 업데이트되었습니다.")
                
                # 다음 배치 처리 전 잠시 대기
                if batch_num < total_batches - 1:
                    print("다음 배치 처리 전 15초 대기...")
                    time.sleep(15)
            
            print("\n=== 모든 데이터 수집이 완료되었습니다! ===")
            # 전체 통계 요약 출력
            filled_count = contents_df['genre_detail'].notna().sum()
            total_count = len(contents_df)
            success_rate = filled_count / total_count * 100
            
            print(f"전체 콘텐츠 수: {total_count}")
            print(f"장르 정보 수집 성공: {filled_count} ({success_rate:.1f}%)")
            print(f"장르 정보 미수집: {total_count - filled_count} ({100-success_rate:.1f}%)")
            
            # 수집 완료된 데이터 샘플 출력
            print("\n=== 수집된 데이터 샘플 ===")
            sample_df = contents_df[contents_df['genre_detail'].notna()].head(10)
            print(sample_df[['title', 'year', 'genre_detail', 'director', 'country']].to_string(index=False))
            
        else:
            print("장르 정보가 없는 콘텐츠가 없습니다. 모든 콘텐츠에 이미 장르 정보가 있습니다.")
    else:
        print("콘텐츠 파일이 존재하지 않습니다. main.py를 먼저 실행해주세요.")
