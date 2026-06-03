from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from bakong_khqr import KHQR

app = Flask(__name__)
CORS(app)

# Initialize KHQR
khqr = KHQR("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTUzOGM3MzZjYzFjNDUyMSJ9LCJpYXQiOjE3NjA0MjcxMjEsImV4cCI6MTc2ODIwMzEyMX0.J5rUj5wTuQgcJMuVzaaMT0-uByY78uVCMF7N53Ro_tk")

# In-memory storage for transactions
TRANSACTIONS = {}

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        data = request.get_json()
        
        if not data or 'amount' not in data or 'currency' not in data:
            return jsonify({'error': 'Missing required fields: amount and currency'}), 400
        
        amount = data['amount']
        currency = data['currency']
        description = data.get('description', 'Payment')
        
        # Generate unique bill number
        bill_number = uuid.uuid4().hex[:12]
        
        # Create QR code
        qr_string = khqr.create_qr(
            bank_account="sea_sengly@aclb",
            merchant_name="Sea Sengly",
            merchant_city="Phnom Penh",
            amount=amount,
            currency=currency,
            store_label="Shop Anh",
            phone_number="016957000",
            bill_number=bill_number,
            terminal_label="WebQR",
            static=False,
        )
        
        # Generate MD5 for transaction tracking
        md5 = khqr.generate_md5(qr=qr_string)
        qr_image = khqr.qr_image(qr=qr_string, format="base64_uri")
        
        # Store transaction
        TRANSACTIONS[md5] = {
            'amount': amount,
            'currency': currency,
            'description': description,
            'status': 'UNPAID',
            'bill_number': bill_number
        }
        
        return jsonify({
            'success': True,
            'qr_image': qr_image,
            'md5': md5,
            'bill_number': bill_number,
            'amount': amount,
            'currency': currency
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-payment', methods=['GET'])
def check_payment():
    try:
        md5 = request.args.get('md5')
        
        if not md5 or md5 not in TRANSACTIONS:
            return jsonify({'error': 'Invalid transaction ID'}), 400
        
        transaction = TRANSACTIONS[md5]
        status = khqr.check_payment(md5)
        
        # Update transaction status
        if status == 'PAID':
            transaction['status'] = 'PAID'
        
        return jsonify({
            'status': status,
            'transaction': {
                'amount': transaction['amount'],
                'currency': transaction['currency'],
                'description': transaction['description'],
                'bill_number': transaction['bill_number']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'Shop Anh Backend'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)

    # python app.py