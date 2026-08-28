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

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "b304c554e7dbe31a293ecad2df11e9ae")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "b272fca3bda97463f8bb64f89d3cf4bf06fbfeea")

@app.get("/")
def home():
    return {"status": "online", "message": "Visual Finder API calisiyor"}

@app.post("/search-product")
async def search_product(image: UploadFile = File(...)):
    try:
        contents = await image.read()

        # 1. ImgBB'ye doğrudan dosya (multipart) olarak yükle
        imgbb_res = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}",
            files={"image": (image.filename or "upload.jpg", contents)}
        )
        imgbb_json = imgbb_res.json()
        print("ImgBB Cevabi:", imgbb_json)

        image_url = None
        if imgbb_json.get("success"):
            image_url = imgbb_json["data"]["url"]
        else:
            # ImgBB kotası biterse alternatif ücretsiz yükleyici (FreeImage.host)
            alt_res = requests.post(
                "https://freeimage.host/api/1/upload",
                data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload"},
                files={"source": (image.filename or "upload.jpg", contents)}
            )
            alt_json = alt_res.json()
            if alt_json.get("status_code") == 200:
                image_url = alt_json["image"]["url"]

        if not image_url:
            error_detail = imgbb_json.get("error", {}).get("message", "Görsel sunucuya yüklenemedi.")
            raise HTTPException(status_code=400, detail=f"Görsel yüklenemedi: {error_detail}")

        print("Basariyla Yuklenen Gorsel URL:", image_url)

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
        print("Lens Yaniti:", lens_data)

        for key in ["organic", "visualMatches", "shopping"]:
            for item in lens_data.get(key, []):
                products.append({
                    "title": item.get("title") or "Bulunan Ürün",
                    "link": item.get("link") or "",
                    "source": item.get("source") or "Alışveriş",
                    "price": item.get("price"),
                    "thumbnail": item.get("thumbnail") or item.get("imageUrl") or image_url
                })

        # 3. Sonuç boşsa genel alışveriş arama desteği
        if not products:
            shopping_res = requests.post(
                "https://google.serper.dev/shopping",
                headers=headers,
                json={"q": "trend kıyafet ayakkabı moda", "gl": "tr", "hl": "tr"}
            )
            shopping_data = shopping_res.json()
            for item in shopping_data.get("shopping", [])[:10]:
                products.append({
                    "title": item.get("title") or "Önerilen Ürün",
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
        print("HTTP Hatasi:", str(he.detail))
        raise he
    except Exception as e:
        print("Genel Hata:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
