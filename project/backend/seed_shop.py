import os
import sys
from datetime import datetime

# Ensure repo root is on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from app import create_app
from backend.models import db, ShopItem
from backend.db_service import DBService

def seed_shop():
    app = create_app()
    with app.app_context():
        print("Seeding Shop Items...")
        
        items = [
            # {
            #     "name": "Organic Herbal Soap",
            #     "description": "Handcrafted with natural oils for a refreshing and healthy skin glow.",
            #     "points_cost": 500,
            #     "image_url": "https://images.unsplash.com/photo-1600857062241-98e5dba7f214?auto=format&fit=crop&q=80&w=800",
            #     "category": "Hygiene"
            # },
            # {
            #     "name": "Luxury Silk Shampoo",
            #     "description": "Professional-grade hair nourishment with essential proteins.",
            #     "points_cost": 700,
            #     "image_url": "https://images.unsplash.com/photo-1535585209827-a15fcdce4c24?auto=format&fit=crop&q=80&w=800",
            #     "category": "Personal Care"
            # },
            {
                "name": "Advanced Hand Sanitizer",
                "description": "Kills 99.9% of germs while keeping your skin moisturized.",
                "points_cost": 600,
                "image_url": "https://images.unsplash.com/photo-1587854692152-cbe660dbde0d?auto=format&fit=crop&q=80&w=800",
                "category": "Safety"
            },
            # {
            #     "name": "GlowBoost Facewash",
            #     "description": "Deep cleansing formula with Vitamin C to brighten your skin.",
            #     "points_cost": 800,
            #     "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&q=80&w=800",
            #     "category": "Skincare"
            # }
        ]

        for item_data in items:
            existing = ShopItem.query.filter_by(name=item_data['name']).first()
            if not existing:
                new_item = ShopItem(**item_data)
                db.session.add(new_item)
                db.session.commit()
                print(f"[OK] Seeded {item_data['name']}")
                
                # Sync to Mongo
                if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
                    mongo_data = new_item.to_dict()
                    mongo_data['sql_id'] = new_item.id
                    DBService._async_mongo_write('shop_items', 'insert', mongo_data)
            else:
                print(f"[INFO] Item {item_data['name']} already exists.")

if __name__ == "__main__":
    seed_shop()
