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

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "226b7b01ad0208418a0dc74de42f0e79")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "aece28f83843b17949ed03735eb65142805b9d45")

@app.get("/")
def home():
    return {"status": "online", "message": "Visual Finder API calisiyor"}

@app.post("/search-product")
async def search_product(image: UploadFile = File(...)):
    try:
        contents = await image.read()
        b64_image = base64.b64encode(contents).decode('utf-8')

        # 1. ImgBB'ye yükle
        imgbb_response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": IMGBB_API_KEY,
                "image": b64_image
            }
        )
        imgbb_data = imgbb_response.json()
        
        if not imgbb_data.get("success"):
            error_text = imgbb_data.get("error", {}).get("message", "ImgBB hatasi")
            print("ImgBB Hatasi:", error_text)
            raise HTTPException(status_code=400, detail=f"Görsel yüklenemedi: {error_text}")
        
        image_url = imgbb_data["data"]["url"]
        print("Gorsel URL:", image_url)

        # 2. Serper Google Lens Arama
        serper_url = "https://google.serper.dev/lens"
        payload = {
            "url": image_url,
            "gl": "tr",
            "hl": "tr"
        }
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        serper_res = requests.post(serper_url, headers=headers, json=payload)
        data = serper_res.json()
        print("Serper Ham Yaniti:", data)
        
        products = []

        # Organic sonuçları topla
        for item in data.get("organic", []):
            products.append({
                "title": item.get("title") or "Ürün",
                "link": item.get("link") or "",
                "source": item.get("source") or "Web",
                "price": item.get("price"),
                "thumbnail": item.get("thumbnail") or item.get("imageUrl")
            })

        # Visual matches (Görsel eşleşmeler) topla
        for item in data.get("visualMatches", []):
            products.append({
                "title": item.get("title") or "Benzer Ürün",
                "link": item.get("link") or "",
                "source": item.get("source") or "Alışveriş",
                "price": item.get("price"),
                "thumbnail": item.get("thumbnail") or item.get("imageUrl")
            })

        # Shopping sonuçları topla
        for item in data.get("shopping", []):
            products.append({
                "title": item.get("title") or "Mağaza Ürünü",
                "link": item.get("link") or "",
                "source": item.get("source") or "Mağaza",
                "price": item.get("price"),
                "thumbnail": item.get("thumbnail") or item.get("imageUrl")
            })

        return {
            "success": True,
            "total_results": len(products),
            "uploaded_url": image_url,
            "data": products
        }

    except Exception as e:
        print("Backend Hatasi:", str(e))
        raise HTTPException(status_code=500, detail=str(e))