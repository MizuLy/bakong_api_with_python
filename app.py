from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from flask_cors import CORS
import uuid
from bakong_khqr import KHQR

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize KHQR with developer token from environment
khqr = KHQR(os.getenv("BAKONG_TOKEN"))
print("TOKEN LOADED:", bool(os.getenv("BAKONG_TOKEN")))

# In-memory storage for active transactions
TRANSACTIONS = {}


@app.route("/api/generate-qr", methods=["POST"])
def generate_qr():
    try:
        data = request.get_json()

        if not data or "amount" not in data or "currency" not in data:
            return jsonify({"error": "Missing required fields: amount and currency"}), 400

        amount = data["amount"]
        currency = data["currency"].upper()
        description = data.get("description", "Payment")

        if currency not in ("USD", "KHR"):
            return jsonify({"error": "Currency must be USD or KHR"}), 400

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            return jsonify({"error": "Amount must be a valid number"}), 400

        if amount_val <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400

        if currency == "KHR" and not amount_val.is_integer():
            return jsonify({"error": "KHR amount must be a whole number"}), 400

        bill_number = uuid.uuid4().hex[:12]
        store_label = "Shop Anh"
        terminal_label = "WebQR"
        phone_number = "85516957000"

        # Generate standard EMVCo/KHQR compliant string directly from the SDK
        qr_string = khqr.create_qr(
            account_id="sea_sengly@aclb",  # Use your active Bakong ID
            merchant_name="Sea Sengly",
            merchant_city="Phnom Penh",
            amount=amount_val,
            currency=currency,
            store_label=store_label,
            phone_number=phone_number,
            bill_number=bill_number,
            terminal_label=terminal_label,
            static=False,
        )

        # Generate MD5 hash and Base64 QR image
        md5 = khqr.generate_md5(qr=qr_string)
        qr_image = khqr.qr_image(qr=qr_string, format="base64_uri")

        TRANSACTIONS[md5] = {
            "amount": amount_val,
            "currency": currency,
            "description": description,
            "status": "UNPAID",
            "bill_number": bill_number,
        }

        return jsonify({
            "success": True,
            "qr_image": qr_image,
            "md5": md5,
            "bill_number": bill_number,
            "amount": amount_val,
            "currency": currency,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/check-payment", methods=["GET"])
def check_payment():
    try:
        md5 = request.args.get("md5")

        if not md5 or md5 not in TRANSACTIONS:
            return jsonify({"error": "Invalid transaction ID"}), 400

        transaction = TRANSACTIONS[md5]
        status = khqr.check_payment(md5)

        if status == "PAID":
            transaction["status"] = "PAID"

        return jsonify({
            "status": status,
            "transaction": {
                "amount": transaction["amount"],
                "currency": transaction["currency"],
                "description": transaction["description"],
                "bill_number": transaction["bill_number"],
            },
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "Shop Anh Backend"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
