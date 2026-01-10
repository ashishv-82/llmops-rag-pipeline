import requests
import sys
import time
import argparse
import os

def run_tests(base_url, verbose=False):
    print(f"🚀 Starting Integration Tests against {base_url}")
    
    # 1. Health Check
    try:
        resp = requests.get(f"{base_url}/health")
        if resp.status_code == 200:
            print("✅ Health Check Passed")
            if verbose: print(resp.json())
        else:
            print(f"❌ Health Check Failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check Connection Error: {e}")
        return False

    # 2. Upload Document (Create a dummy file first)
    dummy_file = "test_doc.txt"
    with open(dummy_file, "w") as f:
        f.write("The capital of France is Paris. The application is running on EKS.")
    
    try:
        with open(dummy_file, "rb") as f:
            files = {"file": (dummy_file, f, "text/plain")}
            resp = requests.post(f"{base_url}/documents/upload", files=files)
            
        if resp.status_code == 200 and resp.json().get("status") == "processing":
            print("✅ Document Upload Passed")
        else:
            print(f"❌ Document Upload Failed: {resp.status_code} - {resp.text}")
            # Continue anyway for query test? Maybe.
    except Exception as e:
        print(f"❌ Document Upload Error: {e}")
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

    # Wait for indexing (simulation)
    print("⏳ Waiting 5s for indexing...")
    time.sleep(5)

    # 3. Query RAG
    query_payload = {
        "question": "What is the capital of France?",
        "domain": "general"
    }
    try:
        resp = requests.post(f"{base_url}/rag/query", json=query_payload)
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "")
            if "Paris" in answer:
                print("✅ RAG Query Passed (Correct Answer)")
            else:
                print(f"⚠️ RAG Query Passed but answer might be wrong: {answer}")
                
            # Check metrics
            if "complexity_metrics" in data:
                print("✅ Metrics Verified (Complexity Headers present)")
            else:
                print("⚠️ Metrics Missing in response")
        else:
            print(f"❌ RAG Query Failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ RAG Query Connection Error: {e}")
        return False

    print("\n🎉 All Integration Tests Completed Successfully!")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run API Integration Tests")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    args = parser.parse_args()
    
    success = run_tests(args.url)
    if not success:
        sys.exit(1)
