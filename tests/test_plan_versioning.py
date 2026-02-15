import httpx
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_plan_versioning():
    plan_code = f"PLAN_{uuid.uuid4().hex[:6]}"
    
    plan_data = {
        "plan_code": plan_code,
        "plan_name": "Pro Business Plan",
        "price": 4999,
        "currency": "INR",
        "country": "IN",
        "billing_cycle": "monthly",
        "max_users": 10,
        "max_branches": 2,
        "storage_limit_gb": 50,
        "is_active": True
    }

    print(f"\n--- Testing Plan Creation (V1) for {plan_code} ---")
    with httpx.Client() as client:
        # 1. Create Plan
        response = client.post(f"{BASE_URL}/plans/", json=plan_data)
        print(f"Status: {response.status_code}")
        # print(json.dumps(response.json(), indent=2))
        
        assert response.status_code == 200
        data = response.json()["data"][0]
        plan_uuid = data["id"]
        assert len(data["versions"]) == 1
        assert data["current_version"]["version"] == 1
        assert float(data["current_version"]["price"]) == 4999.0
        print(f"Success: Created V1 for plan {plan_uuid}")

        # # 2. Update Plan (Price and Limits change)
        # print("\n--- Testing Plan Update (V2) ---")
        # plan_data["price"] = 5999
        # plan_data["max_users"] = 15
        
        # response = client.put(f"{BASE_URL}/plans/{plan_uuid}", json=plan_data)
        # print(f"Status: {response.status_code}")
        # # print(json.dumps(response.json(), indent=2))
        
        # assert response.status_code == 200
        # data = response.json()["data"][0]
        # assert len(data["versions"]) == 2
        # assert data["current_version"]["version"] == 2
        # assert float(data["current_version"]["price"]) == 5999.0
        # assert data["current_version"]["max_users"] == 15
        
        # # Verify V1 still exists in the list
        # v1_found = any(v["version"] == 1 and not v["is_current"] for v in data["versions"])
        # assert v1_found, "V1 should still exist and not be current"
        # print("Success: Created V2 and preserved V1 as history.")

if __name__ == "__main__":
    try:
        test_plan_versioning()
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback
        traceback.print_exc()
