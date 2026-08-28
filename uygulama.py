import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Visual Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kendi yeni ImgBB ve Serper anahtarlarınızı buraya yazın
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "143724ca78fb5e2d2af4cc6679c6188a")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "b272fca3bda97463f8bb64f89d3cf4bf06fbfeea")

@app.get("/")
def home():
    return {"status": "online", "message": "Visual Finder API calisiyor"}

@app.post("/search-product")
async def search_product(image: UploadFile = File(...)):
    try:
        contents = await image.read()

        # 1. ImgBB'ye Doğrudan Multipart Dosya Olarak Yükle
        files = {
            'image': (image.filename or 'upload.jpg', contents, image.content_type or 'image/jpeg')
        }
        params = {
            'key': IMGBB_API_KEY
        }

        imgbb_res = requests.post("https://api.imgbb.com/1/upload", params=params, files=files)
        imgbb_json = imgbb_res.json()

        if not imgbb_json.get("success"):
            error_detail = imgbb_json.get("error", {}).get("message", "ImgBB bilinmeyen hata")
            print(f"ImgBB Hatası: {error_detail}")
            raise HTTPException(status_code=400, detail=f"Görsel ImgBB'ye yüklenemedi: {error_detail}")

        image_url = imgbb_json["data"]["url"]
        print("Yüklenen Görsel URL:", image_url)

        # 2. Serper Lens Araması
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        products = []

        lens_res = requests.post(
            "https://google.serper.dev/lens",
            headers=headers,
            json={"url": image_url}
        )
        lens_data = lens_res.json()

        for key in ["organic", "visualMatches", "shopping"]:
            for item in lens_data.get(key, []):
                products.append({
                    "title": item.get("title") or "Bulunan Ürün",
                    "link": item.get("link") or "",
                    "source": item.get("source") or "Alışveriş",
                    "price": item.get("price"),
                    "thumbnail": item.get("thumbnail") or item.get("imageUrl") or image_url
                })

        # 3. Sonuç boşsa Alışveriş Arama motorunu devreye sok
        if not products:
            shopping_res = requests.post(
                "https://google.serper.dev/shopping",
                headers=headers,
                json={"q": "kadın erkek ayakkabı giyim moda kıyafet", "gl": "tr", "hl": "tr"}
            )
            shopping_data = shopping_res.json()
            for item in shopping_data.get("shopping", [])[:10]:
                products.append({
                    "title": item.get("title") or "Popüler Ürün",
                    "link": item.get("link") or "",
                    "source": item.get("source") or "Mağaza",
                    "price": item.get("price"),
                    "thumbnail": item.get("imageUrl") or image_url
                })

        return {
            "success": True,
            "total_results": len(products),
            "uploaded_url": image_url,
            "data": products
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print("Genel Sunucu Hatası:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
