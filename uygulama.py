import os
import base64
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

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "b304c554e7dbe31a293ecad2df11e9ae")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "b272fca3bda97463f8bb64f89d3cf4bf06fbfeea")

@app.get("/")
def home():
    return {"status": "online", "message": "Visual Finder API calisiyor"}

@app.post("/search-product")
async def search_product(image: UploadFile = File(...)):
    try:
        contents = await image.read()
        b64_image = base64.b64encode(contents).decode('utf-8')

        # 1. ImgBB'ye Yükle
        imgbb_res = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64_image}
        )
        imgbb_json = imgbb_res.json()

        if not imgbb_json.get("success"):
            raise HTTPException(status_code=400, detail="Görsel ImgBB'ye yüklenemedi.")

        # Doğrudan resim dosyasının ham bağlantısı
        image_url = imgbb_json["data"]["url"]
        print("Yüklenen Görsel URL:", image_url)

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        products = []

        # 2. Serper Lens Araması
        lens_res = requests.post(
            "https://google.serper.dev/lens",
            headers=headers,
            json={"url": image_url}
        )
        lens_data = lens_res.json()
        print("Lens Yanıtı:", lens_data)

        # Lens sonuçlarını ayıkla
        for key in ["organic", "visualMatches", "shopping"]:
            for item in lens_data.get(key, []):
                products.append({
                    "title": item.get("title") or "Bulunan Ürün",
                    "link": item.get("link") or "",
                    "source": item.get("source") or "Alışveriş",
                    "price": item.get("price"),
                    "thumbnail": item.get("thumbnail") or item.get("imageUrl") or image_url
                })

        # 3. Eğer Lens boş dönerse Yedek Arama (Google Alışveriş Arama)
        if not products:
            search_query = "kadın erkek ayakkabı giyim moda kıyafet"
            shopping_res = requests.post(
                "https://google.serper.dev/shopping",
                headers=headers,
                json={"q": search_query, "gl": "tr", "hl": "tr"}
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

    except Exception as e:
        print("Hata:", str(e))
        raise HTTPException(status_code=500, detail=str(e))