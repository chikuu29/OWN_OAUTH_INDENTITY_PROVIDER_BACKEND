import httpx
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_register_and_get_apps():
    app_code = f"APP_{uuid.uuid4().hex[:6]}"
    
    app_data = {
        "code": app_code,
        "name": "Test Application",
        "description": "A test application for automated verification",
        "icon": "https://example.com/icon.png",
        "is_active": True,
        "pricing": [
            {
                "price": 49.99,
                "currency": "USD",
                "country": "US",
                "is_active": True
            },
            {
                "price": 3999.00,
                "currency": "INR",
                "country": "IN",
                "is_active": True
            }
        ],
        "features": [
            {
                "code": "FEAT_AUTH",
                "name": "Authentication",
                "description": "User authentication and management",
                "is_base_feature": True,
                "addon_price": 0.0,
                "currency": "USD",
                "status": "active"
            },
            {
                "code": "FEAT_STORAGE",
                "name": "Storage",
                "description": "Cloud storage module",
                "is_base_feature": False,
                "addon_price": 10.0,
                "currency": "USD",
                "status": "active"
            }
        ]
    }

    print(f"\n--- Testing App Registration for {app_code} ---")
    with httpx.Client() as client:
        # 1. Register App
        response = client.post(f"{BASE_URL}/saas/register", json=app_data)
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        assert response.status_code == 200
        data = response.json()["data"][0]
        assert "base_price" in data
        assert "primary_currency" in data
        assert "primary_country" in data
        print(f"Verified root pricing: {data['base_price']} {data['primary_currency']} ({data['primary_country']})")

        # 2. Get Apps
        print("\n--- Testing List Apps ---")
        response = client.get(f"{BASE_URL}/saas/get_apps")
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 200
        apps_data = response.json().get("data", [])
        
        # Verify our new app is in the list
        found = False
        for app in apps_data:
            if app["code"] == app_code:
                found = True
                print(f"Success: Found registered app '{app_code}' in the list.")
                break
        
        assert found, f"Error: App '{app_code}' was not found in the get_apps response."

if __name__ == "__main__":
    try:
        test_register_and_get_apps()
    except Exception as e:
        print(f"\nTests failed: {e}")
