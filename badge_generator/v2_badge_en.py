import svgwrite, base64

from models.user_stats import UserStats

def create_svg(data: UserStats):
    
    stats = {
        "Solved Problems": str(data.solvedCount),
        "Authored Problems": data.createdCount,
        "Reviewed Problems": data.reviewedCount,
        "Fixed Problems": str(data.fixedCount),
        "Rating Contributions": str(data.voteCount)
    }
    # 뱃지 전체 크기 설정

    width = 467
    height = 195
    dwg = svgwrite.Drawing(size=(f"{width}px", f"{height}px"))
    
    # 배경
    bg_rect = dwg.rect(
        insert=(0, 0),
        size=(width, height),
        rx=10,  # 라운드 모서리
        ry=10,
        fill="#282a36"
    )

    dwg.add(bg_rect)
    
    # 타이틀 텍스트
    title = f"{data.handle}'s BOJ Stats"
    dwg.add(dwg.text(
        title,
        insert=(20, 30),
        fill="#E84DFF",
        font_size="18px",
        font_weight="bold",
        font_family=('Segoe UI', 'Ubuntu', "Helvetica Neue", "Sans-Serif"),
    ))
    
    # 통계 항목들을 위한 시작 위치와 줄 간격 설정
    start_y = 60
    line_height = 25
    
    # 각 통계 항목을 텍스트로 추가 (왼쪽: 라벨, 오른쪽: 값)
    for i, label in enumerate(stats):
        y = start_y + i * line_height
        # 라벨 텍스트
        dwg.add(dwg.text(
            f"{label}",
            insert=(20, y),
            fill="#fffff0",
            font_size="14px",
            font_family=('Segoe UI', 'Ubuntu', "Helvetica Neue", "Sans-Serif"),
            font_weight="bold"
        ))
        # 값 텍스트
        dwg.add(dwg.text(
            stats[label],
            insert=(width // 2 + 40, y),
            text_anchor="end",
            fill="#fffff0",
            font_size="14px",
            font_family=('Segoe UI', 'Ubuntu', "Helvetica Neue", "Sans-Serif"),
            font_weight="bold"
        ))
    
    tier = data.tier
    tier_file_name =  f'tier_image/{tier}.png'
    with open(tier_file_name, 'rb') as f:
        tier_encoded = base64.b64encode(f.read()).decode('utf-8')
# data URI 생성
    tier_uri = f'data:image/png;base64,{tier_encoded}'
# SVG에 이미지 삽입
    dwg.add(dwg.image(href=tier_uri, insert=((width // 2 + 40+width)//2 - 45, 185 // 2-50), size=(100, 100)))
    return dwg.tostring()
