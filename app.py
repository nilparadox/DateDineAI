import streamlit as st
import uuid
import json
import os
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
from google_places import get_places_nearby
from dotenv import load_dotenv

# Load .env file (local dev)
load_dotenv()

# Prefer Streamlit Cloud secrets; fall back to .env for local
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

if not GOOGLE_API_KEY:
    st.error("Missing GOOGLE_API_KEY. Add it to .env (local) or Streamlit Secrets (cloud).")


def save_user(user_id, name, vibe, food, budget, time_limit, lat, lon):
    data = {
        "user_id": user_id,
        "name": name,
        "vibe": vibe,
        "food": food,
        "budget": budget,
        "time_limit": time_limit,
        "lat": lat,
        "lon": lon
    }

    # Try reading existing users, else start fresh
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        users = {}

    users[user_id] = data

    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)



st.set_page_config(page_title="DateDine AI", page_icon="🌸")

st.title("🌸 Welcome to DateDine AI")
st.subheader("Plan your perfect romantic date 💑")

st.markdown("---")

# --- User Info ---
with st.form("user_form"):
    st.write("### Your Preferences")

    name = st.text_input("Your Name")
    vibe = st.selectbox("Looking for a place that's...", 
                        ["Romantic", "Quiet Cafe", "Lively with music", "Dance & Drinks", "Adventurous"])
    food = st.multiselect("What kind of food do you prefer?", 
                          ["Indian", "Thai", "Italian", "Continental", "Chinese", "Bengali", "Anything"])
    budget = st.slider("Approx Budget for Two (₹)", 300, 5000, 1500, step=100)
    time_limit = st.slider("Max travel time (in minutes)", 5, 90, 30, step=5)

    submit = st.form_submit_button("Generate My Profile")

if submit:
    user_id = str(uuid.uuid4())[:6]
    st.session_state.user_id = user_id

    # Use defaults if location is not yet captured
    lat = st.session_state.get("user_lat", 19.0760)  # Mumbai default
    lon = st.session_state.get("user_lon", 72.8777)

    # Save user data to file
    save_user(user_id, name, vibe, food, budget, time_limit, lat, lon)

    # Display saved data from file
    st.success("✅ Profile saved! Here's what we stored:")
    try:
        with open("users.json", "r") as f:
            st.code(f.read(), language='json')
    except FileNotFoundError:
        st.error("⚠️ Could not find users.json — file not created.")

    # Show friend code
    st.success("🎉 Profile Created")
    st.write(f"**Your unique friend code is:** `{user_id}`")
    st.info("Share this code with your partner to connect.")




st.markdown("---")
st.write("### 💌 Connect with Your Partner")

partner_code = st.text_input("Enter your partner's code")

if st.button("Link Now"):
    if partner_code:
        # Try loading users
        try:
            with open("users.json", "r") as f:
                users = json.load(f)
        except:
            st.error("❌ Could not load user data.")
            users = {}

        if partner_code in users:
            you = users.get(st.session_state.user_id)
            partner = users.get(partner_code)

            if you and partner:
                # Midpoint location
                mid_lat = (you["lat"] + partner["lat"]) / 2
                mid_lon = (you["lon"] + partner["lon"]) / 2

                # Overlapping food
                shared_food = list(set(you["food"]) & set(partner["food"]))
                shared_food = shared_food if shared_food else ["Anything"]

                # Choose budget min of both
                max_budget = min(you["budget"], partner["budget"])

                                # Output real restaurant suggestions
                st.success("🌟 Date Plan Suggestions")
                st.write(f"**Midpoint Location:** ({mid_lat:.4f}, {mid_lon:.4f})")
                st.write(f"**Shared Food:** {', '.join(shared_food)}")
                st.write(f"**Max Budget:** ₹{max_budget}")

                st.markdown("---")
                st.write("### 🍽️ Searching for Restaurants Near You...")

                # Use your existing function
                query = f"{you['vibe']} {shared_food[0]} restaurant"
                places = get_places_nearby(mid_lat, mid_lon, radius=5000, query=query)

                if not places:
                    st.warning("No restaurants found. Try different preferences.")
                else:
                    for i, place in enumerate(places[:5]):
                        st.markdown(f"""
                        🥂 **{place['Name']}**
                        - 📍 {place['Address']}
                        - ⭐ Rating: {place['Rating']}
                        - 📖 Tags: {place['Description']}
                        """)

            else:
                st.error("⚠️ Could not load both profiles.")
        else:
            st.warning("Partner code not found in user database.")
    else:
        st.warning("Please enter a valid code to link.")

st.markdown("---")
import streamlit as st

# --- Auto Location Detector ---
st.markdown("---")
st.write("### 📍 Detect Your Location Automatically")

st.markdown(
    """
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const coords = pos.coords.latitude + "," + pos.coords.longitude;
            const input = window.parent.document.querySelector('input[data-testid="stTextInput"]');
            if (input) input.value = coords;
            const event = new Event("input", { bubbles: true });
            input.dispatchEvent(event);
        }
    );
    </script>
    """,
    unsafe_allow_html=True
)

location_str = st.text_input("📌 Your Location (auto-filled)", placeholder="Waiting for permission...")

# Parse and store in session
if location_str and "," in location_str:
    lat, lon = location_str.split(",")
    try:
        st.session_state.user_lat = float(lat.strip())
        st.session_state.user_lon = float(lon.strip())
        st.success(f"Location set: ({lat.strip()}, {lon.strip()})")
    except:
        st.warning("Unable to parse coordinates.")
else:
    st.info("Waiting for location access...")
# --- Fallback: manual address to coordinates via Google Geocoding ---
st.markdown("#### Or enter a location manually")
manual_addr = st.text_input("City or full address", placeholder="e.g., Bandra West, Mumbai")

if st.button("Use this location"):
    if not manual_addr.strip():
        st.warning("Please type a city or address.")
    else:
        try:
            import requests
            params = {"address": manual_addr, "key": GOOGLE_API_KEY}
            resp = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=params, timeout=15).json()
            if resp.get("status") == "OK" and resp.get("results"):
                loc = resp["results"][0]["geometry"]["location"]
                st.session_state.user_lat = float(loc["lat"])
                st.session_state.user_lon = float(loc["lng"])
                st.success(f"Location set from address: ({st.session_state.user_lat:.6f}, {st.session_state.user_lon:.6f})")
            else:
                st.error(f"Could not geocode that address. Status: {resp.get('status')}")
        except Exception as e:
            st.error(f"Geocoding failed: {e}")

# -------------------- AI Restaurant Matching Engine --------------------

# Load restaurant data
df = pd.read_csv("restaurants.csv")

# Load NLP model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Embed restaurant descriptions
descriptions = df['Description'].tolist()
description_embeddings = model.encode(descriptions, show_progress_bar=True)

# Build FAISS index
dimension = description_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(description_embeddings))

st.success("💡 AI Vibe Matcher loaded. Ready to recommend!")
st.markdown("---")
st.write("### 🔍 Test AI Matching (demo)")

user_vibe = st.text_input("Describe your ideal vibe", "romantic rooftop with Italian food")

if st.button("Find Matches"):
    user_embed = model.encode([user_vibe])
    D, I = index.search(user_embed, k=3)
    st.write("Top Matches:")
    for idx in I[0]:
        st.write(f"🍽️ {df.iloc[idx]['Name']} — {df.iloc[idx]['Description']}")
