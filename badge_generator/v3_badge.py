import svgwrite

def create_boj_stats_badge(
    solved_tier="PLATINUM V",
    problems_created=15,
    problems_reviewed=30,
    problems_contributed=5,
    difficulty_contributed=120,
    output_filename="boj_stats_badge.svg"
):
    dwg = svgwrite.Drawing(output_filename, profile='tiny', size=('400px', '250px'))

    # 배경색 및 형태 (로고 색상 반영)
    # 백준 로고의 짙은 회색과 파란색 계열을 참고하여 배경 그라데이션 적용
    gradient = dwg.linearGradient((0, '0%'), (0, '100%'), id='backgroundGradient')
    gradient.add_stop_color(0, '#A7A9AC') # 밝은 회색 (로고의 옅은 회색)
    gradient.add_stop_color(1, '#333333') # 짙은 회색 (로고의 짙은 회색)
    dwg.defs.add(gradient)

    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), rx=15, ry=15, fill="url(#backgroundGradient)"))

    # 뱃지 내부 요소 배경 (흰색 박스)
    # 제목 배경
    dwg.add(dwg.rect(insert=(20, 20), size=(360, 40), rx=8, ry=8, fill='white'))
    dwg.add(dwg.text("ID's BOJ STATS", insert=(30, 45), fill='black', font_size='20px', font_weight='bold', font_family='Arial, sans-serif'))

    y_offset = 80
    line_height = 35

    stats_data = [
        f"SOLVED TIER: {solved_tier}",
        f"PROBLEMS CREATED: {problems_created}",
        f"PROBLEMS REVIEWED: {problems_reviewed}",
        f"PROBLEMS CONTRIBUTED: {problems_contributed}",
        f"DIFFICULTY CONTRIBUTED: {difficulty_contributed}"
    ]

    for i, stat in enumerate(stats_data):
        dwg.add(dwg.rect(insert=(20, y_offset + i * line_height), size=(360, 30), rx=5, ry=5, fill='white'))
        dwg.add(dwg.text(stat, insert=(30, y_offset + i * line_height + 22), fill='black', font_size='16px', font_family='Arial, sans-serif'))

    # 솔브드 티어 이미지 (임시로 텍스트로 대체)
    # 실제 이미지를 넣으려면 base64 인코딩 또는 외부 링크 사용
    dwg.add(dwg.text("S", insert=(345, 80 + 22), fill='gray', font_size='16px', font_family='Arial, sans-serif'))

    dwg.save()

# 뱃지 생성 예시
create_boj_stats_badge()