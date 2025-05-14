import os
import pandas as pd
from datetime import datetime
from crawling_data import scrape_daily_content
from genre_collector import collect_missing_genres

# 모든 필요한 필드를 정의 (broadcast_channel 제거)
REQUIRED_FIELDS = [
    'genre_detail', 'director', 'runtime', 'streaming', 'production', 
    'rating', 'broadcast_period', 'episodes', 'cast',
    'country', 'language'
]

def main():
    """
    데이터 크롤링 파이프라인의 주요 실행 함수
    1. 오늘 콘텐츠 랭킹 데이터 체크 및 수집
    2. 콘텐츠 정보 통합 저장 (중복 제거)
    3. 상세 장르 정보 수집 (필요한 경우)
    4. 데이터 병합 및 저장
    """
    today_str = datetime.now().strftime('%y%m%d')
    data_dir = './data'
    
    # 데이터 저장 디렉토리 확인 및 생성
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 파일 경로 설정
    male_filename = f'{data_dir}/daily_MALE_{today_str}.csv'
    female_filename = f'{data_dir}/daily_FEMALE_{today_str}.csv'
    contents_filename = f'{data_dir}/contents.csv'
    
    # 1. 오늘 콘텐츠 랭킹 데이터가 있는지 확인
    if os.path.exists(male_filename) and os.path.exists(female_filename):
        print(f"이미 오늘({today_str})의 남/여 콘텐츠 랭킹 데이터가 있습니다.")
        male_df = pd.read_csv(male_filename)
        female_df = pd.read_csv(female_filename)
    else:
        print(f"오늘({today_str})의 콘텐츠 랭킹 데이터를 수집합니다.")
        # crawling_data.py의 함수를 통해 데이터 수집
        male_df, female_df = scrape_daily_content()
    
    # 2. 콘텐츠 정보 통합 저장 준비
    # 남성/여성 데이터에서 고유한 제목 추출
    if male_df is not None and female_df is not None:
        all_titles = pd.concat([male_df[['title', 'year', 'genre']], 
                                female_df[['title', 'year', 'genre']]])
        all_titles = all_titles.drop_duplicates(subset=['title', 'year']).reset_index(drop=True)
    else:
        print("남/여 데이터를 가져올 수 없습니다. 프로그램을 종료합니다.")
        return None, None
    
    # 3. 기존 콘텐츠 파일이 있는지 확인하고 통합
    if os.path.exists(contents_filename):
        print(f"기존 콘텐츠 정보 파일 {contents_filename}을 로드합니다.")
        contents_df = pd.read_csv(contents_filename)
        
        # 새로운 title-year 조합만 추출
        all_titles['key'] = all_titles['title'] + '|' + all_titles['year'].astype(str)
        contents_df['key'] = contents_df['title'] + '|' + contents_df['year'].astype(str)
        
        # 기존 데이터에 없는 새 데이터만 필터링
        new_titles = all_titles[~all_titles['key'].isin(contents_df['key'])].copy()
        
        if not new_titles.empty:
            # 필요한 모든 컬럼 추가
            new_titles = new_titles.drop(columns=['key'])
            for field in REQUIRED_FIELDS:
                new_titles[field] = None
            
            # 기존 데이터와 새 데이터 통합
            contents_df = contents_df.drop(columns=['key'])
            
            # 새 데이터의 열 순서가 기존 데이터와 일치하도록 확인
            missing_columns = [col for col in contents_df.columns if col not in new_titles.columns]
            for col in missing_columns:
                new_titles[col] = None
            
            new_titles = new_titles[contents_df.columns]
            contents_df = pd.concat([contents_df, new_titles])
            
            contents_df.to_csv(contents_filename, index=False)
            print(f"{len(new_titles)}개의 새로운 콘텐츠를 {contents_filename}에 추가했습니다.")
        else:
            print("추가할 새로운 콘텐츠가 없습니다.")
        
    else:
        # 파일이 없는 경우 새로 생성
        print(f"콘텐츠 정보 파일 {contents_filename}을 생성합니다.")
        
        # 필요한 모든 컬럼 추가
        for field in REQUIRED_FIELDS:
            all_titles[field] = None
            
        # 파일 저장 및 부적절한 키 컬럼 제거
        if 'key' in all_titles.columns:
            all_titles = all_titles.drop(columns=['key'])
        all_titles.to_csv(contents_filename, index=False)
        contents_df = all_titles.copy()
        print(f"{len(all_titles)}개의 콘텐츠 정보를 저장했습니다.")
    
    # 4. 상세 장르 정보 수집 (genre_detail이 없는 행에 한해서만)
    missing_genres_df = contents_df[contents_df['genre_detail'].isna()].copy()
    
    if not missing_genres_df.empty:
        print(f"{len(missing_genres_df)}개 콘텐츠의 상세 장르 정보를 수집합니다.")
        # 상세 장르 정보 수집
        updated_genres_df = collect_missing_genres(missing_genres_df)
        
        # 기존 데이터와 업데이트된 데이터 병합
        for idx, row in updated_genres_df.iterrows():
            mask = (contents_df['title'] == row['title']) & (contents_df['year'] == row['year'])
            
            # 모든 추가 필드 업데이트
            for field in REQUIRED_FIELDS:
                if pd.notna(row[field]):
                    contents_df.loc[mask, field] = row[field]
        
        # 업데이트된 데이터 저장
        contents_df.to_csv(contents_filename, index=False)
        print(f"상세 장르 정보가 업데이트된 콘텐츠 파일을 저장했습니다.")
    else:
        print("상세 장르 정보를 수집할 필요가 없습니다.")
    
    # 5. 데이터 병합
    # 남성/여성 데이터와 장르 정보 병합 (모든 추가 필드 포함)
    join_columns = ['title', 'year'] + REQUIRED_FIELDS
    male_with_genres = pd.merge(male_df, contents_df[join_columns], 
                                on=['title', 'year'], how='left')
    female_with_genres = pd.merge(female_df, contents_df[join_columns], 
                                    on=['title', 'year'], how='left')
    
    # 훈련 데이터 저장
    male_train_filename = f'{data_dir}/male_train_{today_str}.csv'
    female_train_filename = f'{data_dir}/female_train_{today_str}.csv'
    
    male_with_genres.to_csv(male_train_filename, index=False)
    female_with_genres.to_csv(female_train_filename, index=False)
    
    print(f"남성 훈련 데이터를 {male_train_filename}에 저장했습니다.")
    print(f"여성 훈련 데이터를 {female_train_filename}에 저장했습니다.")
    
    return male_with_genres, female_with_genres

if __name__ == "__main__":
    main()
