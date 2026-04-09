import requests, logging
from bs4 import BeautifulSoup

from models.user_stats import BojUserData

logger = logging.getLogger(__name__)

failure_data = BojUserData.failure()

def boj_user_data(username):
    boj_url = 'https://www.acmicpc.net/user/{}'.format(username)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    boj_response = requests.get(boj_url, headers=headers)
    if boj_response.status_code != 200:
        return failure_data
    ret_value = parse_html(boj_response.text)
    return ret_value

def parse_html(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        made_tag = soup.find('th', text='맞은 문제')
        solved_cnt = made_tag.find_next_sibling('td').get_text(strip=True) if made_tag else 0
        # "만든 문제" 항목의 <th> 태그를 찾고, 그 다음 <td> 태그에서 값을 추출
        made_tag = soup.find('th', text='만든 문제')
        created_cnt = made_tag.find_next_sibling('td').get_text(strip=True) if made_tag else 0
    
        # "문제를 검수" 항목도 동일한 방식으로 처리
        verified_tag = soup.find('th', text='문제를 검수')
        reviewed_cnt = verified_tag.find_next_sibling('td').get_text(strip=True) if verified_tag else 0
    
        tags = ['번역한 문제','오타를 찾음','잘못된 데이터를 찾음','잘못된 조건을 찾음','데이터를 추가','문제를 각색','빠진 조건을 찾음','잘못된 번역을 찾음','데이터를 만듦','어색한 표현을 찾음','스페셜 저지를 만듦','시간 제한을 수정','메모리 제한을 수정','문제를 재창조','스페셜 저지 오류를 찾음','내용을 추가','문제를 다시 작성','입력 형식 오류를 찾음']
        fixed_cnt = 0
        for tag in tags:
            contributed_tag = soup.find('th',text=tag)
            tmp = contributed_tag.find_next_sibling('td').get_text(strip=True) if contributed_tag else 0
            fixed_cnt += int(tmp)
    
        data = BojUserData(
            solvedCount=int(solved_cnt),
            createdCount=created_cnt,
            reviewedCount=reviewed_cnt,
            fixedCount=fixed_cnt
        )
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        data = failure_data
    return data
