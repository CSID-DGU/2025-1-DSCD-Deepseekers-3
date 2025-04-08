import urllib.request
import datetime
import pandas as pd
import sys
from bs4 import BeautifulSoup
from lxml import html
import re
import urllib.parse
import os

def get_instiz_keyword_data(keyword: str, starttime: str, endtime: str) -> pd.DataFrame:
    """
    📌 인스티즈 '익명잡담' 게시판에서 특정 키워드로 검색된 글들을 수집하는 크롤러
    """

    title, time_list, contents, url_list, view, like, comment, cate, search_keyword = [], [], [], [], [], [], [], [], []
    base_url = "https://www.instiz.net"
    encoded_keyword = urllib.parse.quote(keyword, safe='')

    now_year = datetime.datetime.now().year
    today = pd.to_datetime(datetime.datetime.now().strftime('%Y.%m.%d'))

    os.makedirs("data", exist_ok=True)

    for page in range(1, 100):  # 충분히 많은 페이지까지 가능하도록 수정
        try:
            full_url = (
                f'{base_url}/name?page={page}&category=1'
                f'&k={encoded_keyword}&stype=9&starttime={starttime}&endtime={endtime}'
            )
            print(f"[DEBUG] 검색 URL: {full_url}")

            response = urllib.request.urlopen(full_url)
            soup = BeautifulSoup(response.read().decode('utf-8'), 'html.parser')
            rows = soup.select('tr#detour')

            # ❗게시글이 없으면 break
            if not rows:
                print(f"[INFO] Page {page}에서 더 이상 게시글이 없습니다. 종료합니다.")
                break

            for row in rows:
                title_cell = row.select_one('td.listsubject a')
                if not title_cell or not title_cell.has_attr('href'):
                    continue

                post_href = title_cell['href']
                post_url = base_url + post_href.replace('..', '')

                # 제목
                titlestr = title_cell.get_text(strip=True)
                title.append(titlestr)

                # URL
                url_list.append(post_url)

                # 날짜
                time_cell = row.select_one('td.listno.regdate')
                if time_cell:
                    timestr = time_cell.get_text(strip=True)
                    full_time = f"{now_year}.{timestr}"
                    try:
                        parsed_time = pd.to_datetime(full_time, format="%Y.%m.%d %H:%M")
                    except:
                        parsed_time = pd.to_datetime(full_time, format="%Y.%m.%d")
                    time_list.append(parsed_time)
                else:
                    time_list.append(today)

                # 조회수, 추천수
                listnos = row.select('td.listno')
                view.append(listnos[-2].get_text(strip=True) if len(listnos) >= 3 else '')
                like.append(listnos[-1].get_text(strip=True) if len(listnos) >= 3 else '')

                # 댓글 수
                comment_span = row.select_one('span.cmt2')
                comment.append(comment_span.get_text(strip=True) if comment_span else '0')

                # 카테고리, 키워드
                cate.append('instiz')
                search_keyword.append(keyword)

                # ✅ 본문 크롤링
                try:
                    post_resp = urllib.request.urlopen(post_url)
                    post_html = post_resp.read()
                    doc = html.fromstring(post_html)

                    content_div = doc.get_element_by_id('memo_content_1')

                    # script, style, img 제거
                    for tag in content_div.xpath('.//script | .//style | .//img'):
                        tag.getparent().remove(tag)

                    # 텍스트 추출 & 공백 정리
                    text = content_div.text_content()
                    clean_text = re.sub(r'\s+', ' ', text).strip()
                    contents.append(clean_text)

                except Exception as e:
                    print(f"본문 크롤링 실패 ({post_url}): {e}", file=sys.stderr)
                    contents.append('')

        except Exception as e:
            print(f"Error on page {page}: {e}", file=sys.stderr)
            continue

    instiz_df = pd.DataFrame({
        'title': title,
        'time': time_list,
        'contents': contents,
        'url': url_list,
        'view': view,
        'like': like,
        'comment': comment,
        'cate': cate,
        'keyword': search_keyword,
    })

    print(f"[✓] instiz: 총 {len(instiz_df)}개 게시글 추출 완료")

    save_path = "data/instiz_keyword_data.csv"
    try:
        instiz_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"[📁] 데이터가 {save_path}에 저장되었습니다.")
    except Exception as e:
        print(f"[⚠️] CSV 저장 실패: {e}", file=sys.stderr)

    return instiz_df

if __name__ == "__main__":
    get_instiz_keyword_data(keyword='밤티라미수', starttime='20241201', endtime='20241231')
