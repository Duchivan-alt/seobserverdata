from flask import Flask, request, jsonify, render_template, send_file, make_response
from flask_cors import CORS
import os
import requests
import tempfile
import json
import time
import io
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'API SEObserver
SEOBSERVER_API_KEY = os.getenv('SEOBSERVER_API_KEY')
SEOBSERVER_API_URL = 'https://api1.seobserver.com/backlinks/metrics.json'

app = Flask(__name__)
CORS(app)

# Route principale
@app.route('/')
def index():
    return render_template('index.html')

# API pour analyser un domaine
@app.route('/api/analyze', methods=['POST'])
def analyze_domain():
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({'error': 'Le paramètre target est requis'}), 400
            
        target_domain = data['target'].strip()
        
        # Configuration de la requête pour SEObserver
        headers = {
            'X-SEObserver-key': SEOBSERVER_API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        payload = [{
            "item_type": "domain",
            "item_value": target_domain
        }]

        # Envoi de la requête à l'API SEObserver
        response = requests.post(
            SEOBSERVER_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Vérification de la structure de la réponse
        if not isinstance(data, dict) or 'data' not in data or not data['data']:
            return jsonify({
                'status': 'error',
                'error': 'Réponse inattendue du serveur SEObserver',
                'details': 'La structure des données est invalide'
            }), 500
            
        result_data = data['data'][0]  # Prendre le premier résultat
        
        # Extraction des métriques principales
        metrics = {
            'referring_domains': result_data.get('RefDomains', 0),      # Domaines référents
            'backlinks': result_data.get('ExtBackLinks', 0),             # Backlinks totaux
            'active_domains': result_data.get('RefDomainTypeLive', 0),   # Domaines actifs
            'dofollow_domains': result_data.get('RefDomainTypeFollow', 0) # Domaines dofollow
        }
        
        return jsonify({
            'status': 'success',
            'target': target_domain,
            'metrics': metrics
        })

    except requests.exceptions.RequestException as e:
        error_msg = f'Erreur lors de la communication avec SEObserver: {str(e)}'
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else 500
        return jsonify({
            'status': 'error',
            'error': error_msg,
            'details': str(e.response.text) if hasattr(e, 'response') and e.response else str(e)
        }), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': 'Une erreur inattendue est survenue',
            'details': str(e)
        }), 500

def create_mock_screenshot(domain, output_path):
    """Crée une image de test pour simuler une capture d'écran"""
    try:
        # Créer une image blanche
        width, height = 1200, 800
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Essayer d'utiliser une police système
        try:
            font = ImageFont.truetype("Arial", 24)
        except:
            font = ImageFont.load_default()
        
        # Ajouter du texte à l'image
        text = f"Résultat de l'analyse SEO\nDomaine: {domain}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Calculer la position pour centrer le texte
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Dessiner le texte
        draw.text((x, y), text, fill='black', font=font)
        
        # Ajouter un cadre
        draw.rectangle([50, 50, width-50, height-50], outline='blue', width=2)
        
        # Enregistrer l'image
        image.save(output_path, 'JPEG', quality=85)
        return True
        
    except Exception as e:
        print(f"Erreur dans create_mock_screenshot: {str(e)}")
        return False

def create_seo_analysis_image(domain, metrics, output_path):
    """Crée une image des résultats d'analyse SEO avec un design moderne et épuré"""
    try:
        print("Métriques reçues dans create_seo_analysis_image:")
        for k, v in metrics.items():
            print(f"{k}: {v}")
        
        # Créer une nouvelle image avec fond blanc
        width, height = 1000, 600
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Charger les polices (essayer Arial, sinon utiliser la police par défaut)
        try:
            title_font = ImageFont.truetype("Arial Bold.ttf", 36)
            metric_font = ImageFont.truetype("Arial Bold.ttf", 48)
            text_font = ImageFont.truetype("Arial.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            metric_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Couleurs
        primary_color = (63, 81, 181)   # Bleu foncé
        secondary_color = (33, 150, 243) # Bleu clair
        text_color = (33, 33, 33)       # Noir
        
        # Titre
        title = f"Analyse SEO - {domain}"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        draw.text(
            ((width - (title_bbox[2] - title_bbox[0])) // 2, 40),
            title,
            fill=primary_color,
            font=title_font
        )
        
        # Ligne de séparation
        draw.line([(50, 120), (width - 50, 120)], fill=secondary_color, width=2)
        
        # Position de départ pour les métriques
        y_position = 160
        
        # Définir les métriques à afficher avec les bonnes clés
        metric_items = [
            ("DOMAINES RÉFÉRENTS", metrics.get('referring_domains', 0)),
            ("BACKLINKS", metrics.get('backlinks', 0)),
            ("DOMAINES ACTIFS", metrics.get('active_domains', 0)),
            ("DOMAINES DOFOLLOW", metrics.get('dofollow_domains', 0))
        ]
        
        # Couleurs des cartes
        card_colors = [
            (232, 244, 253),  # Bleu clair
            (232, 245, 233),  # Vert clair
            (255, 243, 224),  # Orange clair
            (252, 232, 230)   # Rouge clair
        ]
        
        # Afficher les métriques dans une grille 2x2
        for i, (label, value) in enumerate(metric_items):
            # Position de la carte
            row = i // 2
            col = i % 2
            x = 50 + col * 450
            y = y_position + row * 180
            
            # Dessiner la carte
            draw.rounded_rectangle(
                [x, y, x + 400, y + 150],
                radius=15,
                fill=card_colors[i],
                outline=secondary_color,
                width=1
            )
            
            # Ajouter le label
            label_bbox = draw.textbbox((0, 0), label, font=text_font)
            label_width = label_bbox[2] - label_bbox[0]
            draw.text(
                (x + (400 - label_width) // 2, y + 30),
                label,
                fill=text_color,
                font=text_font
            )
            
            # Ajouter la valeur
            value_str = str(value)
            value_bbox = draw.textbbox((0, 0), value_str, font=metric_font)
            value_width = value_bbox[2] - value_bbox[0]
            draw.text(
                (x + (400 - value_width) // 2, y + 60),
                value_str,
                fill=primary_color,
                font=metric_font
            )
            
        # Enregistrer l'image
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        image.save(output_path, 'JPEG', quality=95)
        return True

    except Exception as e:
        print(f"Erreur dans create_seo_analysis_image: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def take_screenshot(domain, analysis_data, output_path):
    """Génère une capture d'écran des résultats d'analyse SEO"""
    try:
        print("\n=== Données reçues dans take_screenshot ===")
        print(f"Domaine: {domain}")
        print("Métriques:", analysis_data)
        print("Type de analysis_data:", type(analysis_data))
        if hasattr(analysis_data, 'items'):
            print("Clés des métriques:", list(analysis_data.keys()))
        print("Chemin de sortie:", output_path)
        print("======================================\n")
        
        return create_seo_analysis_image(domain, analysis_data, output_path)
    except Exception as e:
        print(f"Erreur dans take_screenshot: {str(e)}")
        return False

@app.route('/api/analyze/screenshot', methods=['POST'])
def analyze_and_screenshot():
    """Endpoint pour analyser un domaine et retourner une capture d'écran du résultat"""
    data = request.get_json()
    domain = data.get('target')

    if not domain:
        return jsonify({'error': 'Le paramètre "target" est requis'}), 400

    try:
        # Créer un répertoire temporaire pour stocker les captures d'écran
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, 'screenshot.jpg')

            # 1. D'abord, obtenir les données d'analyse SEO
            headers = {
                'X-SEObserver-key': SEOBSERVER_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            payload = [{
                "item_type": "domain",
                "item_value": domain
            }]

            analysis_response = requests.post(
                SEOBSERVER_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            if analysis_response.status_code != 200:
                return jsonify({
                    'status': 'error',
                    'message': 'Échec de l\'analyse SEO',
                    'details': analysis_response.text
                }), 500

            try:
                response_data = analysis_response.json()
                if not isinstance(response_data, dict) or 'data' not in response_data or not response_data['data']:
                    raise ValueError("Réponse invalide de l'API SEObserver")
                
                result_data = response_data['data'][0]
                
                # 2. Extraire les métriques importantes pour la capture d'écran
                # S'assurer que toutes les valeurs sont des entiers
                metrics = {
                    'referring_domains': int(result_data.get('RefDomains', 0)) if result_data.get('RefDomains') is not None else 0,
                    'backlinks': int(result_data.get('ExtBackLinks', 0)) if result_data.get('ExtBackLinks') is not None else 0,
                    'active_domains': int(result_data.get('RefDomainTypeLive', 0)) if result_data.get('RefDomainTypeLive') is not None else 0,
                    'dofollow_domains': int(result_data.get('RefDomainTypeFollow', 0)) if result_data.get('RefDomainTypeFollow') is not None else 0
                }
                
                # Afficher les métriques pour le débogage
                print("Métriques extraites de l'API SEObserver:")
                for k, v in metrics.items():
                    print(f"{k}: {v}")
                    
            except (ValueError, KeyError, IndexError) as e:
                print(f"Erreur lors de l'extraction des données: {str(e)}")
                print(f"Réponse de l'API: {analysis_response.text}")
                return jsonify({
                    'status': 'error',
                    'message': 'Erreur lors du traitement des données SEO',
                    'details': str(e)
                }), 500

            # 3. Générer la capture d'écran
            if not take_screenshot(domain, metrics, output_path):
                return jsonify({
                    'status': 'error',
                    'message': 'Échec de la génération de l\'image',
                    'details': 'Impossible de générer l\'image des résultats SEO.'
                }), 500

            # Vérifier que le fichier a été créé
            if not os.path.exists(output_path):
                return jsonify({
                    'status': 'error',
                    'message': 'Fichier de capture non trouvé',
                    'details': 'L\'image des résultats n\'a pas pu être générée.'
                }), 500

            # Lire et retourner l'image
            with open(output_path, 'rb') as f:
                image_data = f.read()

            response = make_response(image_data)
            response.headers.set('Content-Type', 'image/jpeg')
            response.headers.set('Content-Disposition', f'attachment; filename=seo_analysis_{domain}.jpg')
            return response

    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': 'Erreur de connexion',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de la génération de la capture d\'écran',
            'details': str(e)
        }), 500

# Point d'entrée principal
if __name__ == '__main__':
    # Utiliser le port défini par l'environnement Cloud Run, ou 8080 par défaut
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
