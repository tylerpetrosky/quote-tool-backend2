
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

moo_data = pd.read_csv("data/mutual_of_omaha.csv")
moo_data["Carrier"] = "Mutual of Omaha"
corebridge_male = pd.read_csv("data/corebridge_male.csv")
corebridge_female = pd.read_csv("data/corebridge_female.csv")
corebridge_data = pd.concat([corebridge_male, corebridge_female], ignore_index=True)
corebridge_data["Gender"] = corebridge_data["Gender"].str.capitalize()
corebridge_data["Carrier"] = "Corebridge"
premiums_df = pd.concat([moo_data, corebridge_data], ignore_index=True)

def evaluate_underwriting(carrier, health):
    smoker = health.get("smoker", False)
    a1c = health.get("a1c")
    conditions = set([c.lower() for c in health.get("conditions", [])])
    surgeries = health.get("recent_surgeries", False)
    oxygen_use = health.get("oxygen_use", False)

    if carrier == "Mutual of Omaha":
        if any(c in conditions for c in ["cancer", "stroke", "heart attack"]):
            return "Declined"
        if a1c and a1c > 8.5:
            return "Declined"
        if any(c in conditions for c in ["kidney failure", "liver failure"]):
            return "Declined"
        if oxygen_use:
            return "Declined"
        return "Smoker" if smoker else "Non-Smoker"

    elif carrier == "Corebridge":
        if health["age"] < 50 or health["age"] > 80:
            return "Declined"
        if any(c in conditions for c in ["cancer", "stroke", "heart attack"]):
            return "Declined"
        if a1c and a1c > 8.0:
            return "Declined"
        if surgeries or oxygen_use:
            return "Declined"
        return "Smoker" if smoker else "Non-Smoker"

    elif carrier == "Ethos":
        if any(c in conditions for c in ["terminal illness", "hospice"]):
            return "Declined"
        return "Smoker" if smoker else "Non-Smoker"

    return "Declined"

@app.post("/api/get-quotes")
async def get_quotes(req: Request):
    data = await req.json()
    age = int(data["age"])
    face_amount = int(data["faceAmount"])
    gender = data["gender"]
    smoker = data["smoker"]
    a1c = float(data["a1c"]) if data["a1c"] else None
    recent_surgeries = data["recentSurgeries"]
    oxygen_use = data["oxygenUse"]
    conditions = data.get("conditions", [])

    results = []
    for carrier in premiums_df["Carrier"].unique():
        rate_class = evaluate_underwriting(carrier, {
            "age": age,
            "smoker": smoker,
            "a1c": a1c,
            "conditions": conditions,
            "recent_surgeries": recent_surgeries,
            "oxygen_use": oxygen_use
        })
        if rate_class in ["Smoker", "Non-Smoker"]:
            df = premiums_df[
                (premiums_df["Carrier"] == carrier) &
                (premiums_df["Age"] == age) &
                (premiums_df["Face Amount"] == face_amount) &
                (premiums_df["Gender"].str.lower() == gender.lower())
            ]
            if not df.empty:
                premium = df.iloc[0][rate_class]
                results.append({
                    "carrier": carrier,
                    "rate_class": rate_class,
                    "monthly_premium": float(premium)
                })
    return results
