
import qrcode
import json

product = {
    "id": "BF-1001",
    "name": "Men's Casual Shirt",
    "category": "Men's Wear",
    "brand": "Baba Fashion",
    "mrp": 1299,
    "purchase_price": 550,
    "last_selling_price": 999,
    "stock": 12
}

# Compact JSON data
data = json.dumps(product, separators=(",", ":"))

qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=15,
    border=6
)

qr.add_data(data)
qr.make(fit=True)

img = qr.make_image(
    fill_color="black",
    back_color="white"
).convert("RGB")

img.save("BF-1001.png")

print("QR generated successfully!")
print(data)
