from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os

app = FastAPI(title="Healthcare Claims API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable is not set")
client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
db = client["healthcare_ops_db"]


@app.get("/health")
def health():
    return {"status": "healthy", "service": "healthcare-claims-api"}


@app.get("/api/member/{member_id}/eligibility")
def get_member_eligibility(member_id: str):
    """Check member eligibility — used by hospitals at point of care"""
    doc = db["member_eligibility"].find_one({"member_id": member_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Member {member_id} not found")
    return doc


@app.get("/api/claim/{claim_id}/status")
def get_claim_status(claim_id: str):
    """Check claim status — used by providers to track payment"""
    doc = db["processed_claims"].find_one({"claim_id": claim_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return doc


@app.get("/api/provider/{npi}/payments")
def get_provider_payments(npi: str):
    """Get provider payment summary — used for monthly reconciliation"""
    doc = db["provider_payments"].find_one({"provider_npi": npi}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Provider {npi} not found")
    return doc


@app.get("/api/claims/state/{state}")
def get_claims_by_state(state: str):
    """Get all claims for a state — used for audit reporting"""
    docs = list(db["processed_claims"].find(
        {"source_state": state.upper()},
        {"_id": 0, "claim_id": 1, "member_id": 1, "cpt_code": 1,
         "billed_amount": 1, "final_status": 1, "fraud_flag": 1}
    ).limit(100))
    return {"state": state.upper(), "total": len(docs), "claims": docs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
