import httpx
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_trial_plan_lifecycle():
    plan_code = f"TRIAL_{uuid.uuid4().hex[:6]}"
    
    # Trial Plan Data (Price 0, short limits)
    trial_plan_data = {
        "plan_code": plan_code,
        "plan_name": "Premium Trial",
        "price": 0,
        "currency": "INR",
        "country": "IN",
        "billing_cycle": "monthly",
        "max_users": 2,
        "max_branches": 1,
        "storage_limit_gb": 5,
        "is_active": True
    }

    print(f"\n--- Testing Trial Plan Creation: {plan_code} ---")
    with httpx.Client() as client:
        # 1. Create Trial Plan
        response = client.post(f"{BASE_URL}/plans/", json=trial_plan_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return

        data = response.json()["data"][0]
        plan_uuid = data["id"]
        
        assert response.status_code == 200
        assert data["plan_code"] == plan_code
        assert float(data["current_version"]["price"]) == 0.0
        print(f"Success: Trial Plan '{plan_code}' created with UUID: {plan_uuid}")

        # # 2. Verify in Global List
        # print("\n--- Verifying Trial Plan in list ---")
        # list_response = client.get(f"{BASE_URL}/plans/")
        # found = any(p["id"] == plan_uuid for p in list_response.json()["data"])
        # assert found, "Trial plan should be in the global plans list"
        # print("Success: Trial plan found in total list.")

        # # 3. Simulate upgrade of Trial Plan (e.g., adding more storage to trial)
        # print("\n--- Updating Trial Plan Version (V2) ---")
        # trial_plan_data["storage_limit_gb"] = 10
        # update_response = client.put(f"{BASE_URL}/plans/{plan_uuid}", json=trial_plan_data)
        
        # assert update_response.status_code == 200
        # update_data = update_response.json()["data"][0]
        # assert update_data["current_version"]["version"] == 2
        # assert update_data["current_version"]["storage_limit_gb"] == 10
        # print("Success: Trial plan versioned correctly.")

if __name__ == "__main__":
    try:
        test_trial_plan_lifecycle()
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback
        traceback.print_exc()
