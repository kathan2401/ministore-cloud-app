from flask import Flask, render_template, request, jsonify
from instagrapi import Client
import google.generativeai as genai
from database import Database
import os
import json
import random

app = Flask(__name__)
db = Database()

# Load config
CONFIG_FILE = "config.json"
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "instagram": {"username": "", "password": ""},
        "gemini_api_key": "",
        "niches": {
            "boutique": ["sarees", "ethnicwear"],
            "food": ["cloudkitchenindia", "homemadefood"],
            "craft": ["handmadeindia", "resinartindia"]
        }
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

cl = Client()
logged_in = False

def login_instagram():
    global logged_in
    if not logged_in and config["instagram"]["username"]:
        try:
            cl.login(config["instagram"]["username"], config["instagram"]["password"])
            logged_in = True
            print("Logged into Instagram successfully.")
        except Exception as e:
            print(f"Login failed: {e}")

if config["gemini_api_key"]:
    genai.configure(api_key=config["gemini_api_key"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    global config, ai_model
    if request.method == 'POST':
        data = request.json
        config["instagram"]["username"] = data.get("ig_username", config["instagram"]["username"])
        config["instagram"]["password"] = data.get("ig_password", config["instagram"]["password"])
        config["gemini_api_key"] = data.get("gemini_api_key", config["gemini_api_key"])
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
            
        if config["gemini_api_key"]:
            genai.configure(api_key=config["gemini_api_key"])
            ai_model = genai.GenerativeModel('gemini-1.5-flash')
            
        login_instagram()
        return jsonify({"status": "success"})
    
    return jsonify({
        "ig_username": config["instagram"]["username"],
        "has_password": bool(config["instagram"]["password"]),
        "has_gemini": bool(config["gemini_api_key"])
    })

@app.route('/api/discover', methods=['POST'])
def discover():
    if not logged_in:
        login_instagram()
    if not logged_in:
        return jsonify({"error": "Instagram not logged in"}), 401
        
    niche = request.json.get('niche')
    amount = request.json.get('amount', 5)
    
    hashtags = config['niches'].get(niche, [])
    if not hashtags:
        return jsonify({"error": "No hashtags for this niche"}), 400
        
    hashtag = random.choice(hashtags)
    results = []
    
    try:
        medias = cl.hashtag_medias_recent(hashtag, amount=amount)
        for media in medias:
            user_partial = media.user
            if not db.get_user_status(user_partial.pk):
                # Fetch full info
                user_info = cl.user_info(user_partial.pk)
                bio = user_info.biography
                caption = media.caption_text
                
                # AI Qualification
                decision = "yes"
                if ai_model:
                    prompt = f"""
                    Qualify this lead for 'MiniStore' (a platform for Instagram sellers to take orders via WhatsApp).
                    Username: {user_info.username}
                    Bio: "{bio}"
                    Caption: "{caption}"
                    Are they selling physical products (clothes, food, crafts)? Answer ONLY 'yes' or 'no'.
                    """
                    try:
                        res = ai_model.generate_content(prompt)
                        decision = res.text.strip().lower()
                    except:
                        pass
                
                if 'yes' in decision:
                    db.add_user(user_info.pk, user_info.username, user_info.full_name, niche, bio=bio)
                    results.append({
                        "pk": user_info.pk,
                        "username": user_info.username,
                        "full_name": user_info.full_name,
                        "bio": bio,
                        "niche": niche
                    })
                else:
                    db.add_user(user_info.pk, user_info.username, user_info.full_name, niche, bio=bio)
                    db.update_user_status(user_info.pk, 'rejected')
                    
        return jsonify({"leads": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads', methods=['GET'])
def get_leads():
    leads = db.get_users_by_status('discovered')
    result = []
    for lead in leads:
        result.append({
            "id": lead[0],
            "pk": lead[1],
            "username": lead[2],
            "full_name": lead[3],
            "niche": lead[4],
            "bio": lead[8],
            "ai_msg": lead[9]
        })
    return jsonify(result)

@app.route('/api/generate_message', methods=['POST'])
def generate_message():
    data = request.json
    username = data.get('username')
    bio = data.get('bio')
    niche = data.get('niche')
    name = data.get('name', username)
    
    if not ai_model:
        return jsonify({"error": "Gemini API key not configured"}), 400
        
    prompt = f"""
    You are a sales rep for 'MiniStore' (helps IG sellers take orders on WhatsApp via a link: www.ministore-app.in).
    Write a short, friendly, personalized 'Hinglish' DM to this seller.
    Name: {name}
    Niche: {niche}
    Bio: "{bio}"
    Compliment their bio/work. Keep it under 5 lines. No quotes.
    """
    
    try:
        res = ai_model.generate_content(prompt)
        message = res.text.strip()
        
        # Save to DB so it can be retrieved later
        pk = data.get('pk')
        if pk:
            db.update_user_status(pk, 'discovered', ai_generated_message=message)
            
        return jsonify({"message": message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/send_dm', methods=['POST'])
def send_dm():
    if not logged_in:
        login_instagram()
    if not logged_in:
        return jsonify({"error": "Instagram not logged in"}), 401
        
    data = request.json
    pk = data.get('pk')
    message = data.get('message')
    username = data.get('username')
    
    try:
        thread = cl.direct_send(message, user_ids=[int(pk)])
        db.update_user_status(str(pk), 'messaged', thread.id, message)
        return jsonify({"status": "success", "thread_id": thread.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_status', methods=['POST'])
def update_status():
    data = request.json
    db.update_user_status(data.get('pk'), data.get('status'))
    return jsonify({"status": "success"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
