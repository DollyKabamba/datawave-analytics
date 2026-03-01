#!/usr/bin/env python3
"""
DataWave Analytics — Script de démarrage
"""
import os
import sys

def main():
    # Init DB
    from app import app, init_db
    print("🔧 Initialisation de la base de données...")
    init_db()
    print("✅ Base de données prête.")

    # Check data file
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'data.xlsx')
    if os.path.exists(data_path):
        print("✅ Fichier de données trouvé : data.xlsx")
    else:
        print("⚠️  ATTENTION : data.xlsx introuvable dans data/")

    print()
    print("=" * 50)
    print("🌊 DataWave Analytics — ENSEA 2025-2026")
    print("=" * 50)
    print()
    print("🌐  http://127.0.0.1:5000")
    print()
    print("  admin    / AS3admin2026")
    print("  manager  / Manager@2026")
    print("  analyst  / Analyst@2026")
    print("  viewer   / Viewer@2026")
    print()
    print("Ctrl+C pour arrêter")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
