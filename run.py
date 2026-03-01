#!/usr/bin/env python3
"""
DataWave Analytics — Script de démarrage
Compatible local ET production (Render, Railway, etc.)
"""
import os

def main():
    from app import app, init_db
    init_db()

    data_path = os.path.join(os.path.dirname(__file__), 'data', 'data.xlsx')
    if not os.path.exists(data_path):
        print("⚠️  ATTENTION : data.xlsx introuvable dans data/")

    # Render/Railway injectent PORT automatiquement
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'

    print(f"🌊 DataWave Analytics — port {port}")
    app.run(debug=debug, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
