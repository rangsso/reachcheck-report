
PAIN_KEYWORDS = ["별로", "아쉽", "불친절", "느리", "오래", "웨이팅", "대기", "비싸", "짜요", "짜서", "싱거", "좁아", "좁은", "시끄", "불편", "실망", "더러", "지저분", "냄새"]

text = "여기 진짜 맛집 인정합니다"

print(f"Testing text: '{text}'")
match = None
for pk in PAIN_KEYWORDS:
    if pk in text:
        match = pk
        break

if match:
    print(f"MATCH FOUND: '{match}'")
else:
    print("NO MATCH")
