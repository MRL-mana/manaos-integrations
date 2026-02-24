import requests
import json

try:
    r = requests.get('http://127.0.0.1:5559/api/images')
    data = r.json()

    print(f"\n生成された画像の総数: {data['count']}枚\n")

    # 最新10枚を表示
    images = sorted(data['images'], key=lambda x: x['created_at'], reverse=True)[:10]

    print("=" * 80)
    print("最新10枚の画像:")
    print("=" * 80)

    for i, img in enumerate(images, 1):
        size_kb = img['size'] / 1024
        print(f"\n{i}. {img['filename']}")
        print(f"   ローカルURL: http://127.0.0.1:5559/images/{img['filename']}")
        print(f"   外部URL: http://163.44.120.49:5559/images/{img['filename']}")
        print(f"   サイズ: {size_kb:.1f} KB")
        print(f"   作成日時: {img['created_at']}")

    print("\n" + "=" * 80)
    print(f"\nすべての画像は以下のURLでアクセスできます:")
    print(f"   ローカル: http://127.0.0.1:5559/images/")
    print(f"   外部: http://163.44.120.49:5559/images/")

except Exception as e:
    print(f"エラー: {e}")
