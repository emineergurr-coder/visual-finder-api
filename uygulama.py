import base64
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Web / Tarayıcı CORS izinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMGBB_API_KEY = "226b7b01ad0208418a0dc74de42f0e79"
SERPER_API_KEY = "aece28f83843b17949ed03735eb65142805b9d45"

@app.post("/search-product")
async def search_product(image: UploadFile = File(...)):
    try:
        # 1. Fotoğrafı oku ve base64 formatına çevir
        contents = await image.read()
        b64_image = base64.b64encode(contents).decode('utf-8')

        # 2. ImgBB'ye yükle
        imgbb_response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": IMGBB_API_KEY,
                "image": b64_image
            }
        )
        
        imgbb_data = imgbb_response.json()
        print("ImgBB Yanıtı:", imgbb_data)

        if not imgbb_data.get("success"):
            error_msg = imgbb_data.get("error", {}).get("message", "ImgBB yükleme hatası")
            print("ImgBB Hatası:", error_msg)
            raise HTTPException(status_code=400, detail=f"Görsel yüklenemedi: {error_msg}")
        
        image_url = imgbb_data["data"]["url"]
        print("Yüklenen Görsel URL:", image_url)

        # 3. Serper Google Lens API ile ara
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
        print("Serper Yanıtı:", data)
        
        products = []
        for item in data.get("organic", []):
            products.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "source": item.get("source"),
                "price": item.get("price"),
                "thumbnail": item.get("thumbnail")
            })

        return {
            "success": True,
            "total_results": len(products),
            "uploaded_url": image_url,
            "data": products
        }

    except Exception as e:
        print("DETAYLI HATA:", str(e))
        raise HTTPException(status_code=500, detail=str(e))