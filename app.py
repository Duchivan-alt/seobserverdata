from flask import Flask, request, jsonify, render_template, send_file, make_response, send_from_directory
from flask_cors import CORS
import os
import requests
import tempfile
import json
import time
import io
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'API SEObserver
SEOBSERVER_API_KEY = os.getenv('SEOBSERVER_API_KEY')
SEOBSERVER_API_URL = 'https://api1.seobserver.com/backlinks/metrics.json'

app = Flask(__name__)
CORS(app)

# Route de santé pour Cloud Run
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

# Route principale
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except:
        # Si le template n'existe pas, retourner une page simple
        return '''
        <html>
            <head><title>SEO Analyzer</title></head>
            <body>
                <h1>SEO Analyzer API</h1>
                <p>Application is running!</p>
                <p>API Key configured: {}</p>
                <p>Use POST /api/analyze with {"target": "domain.com"}</p>
            </body>
        </html>
        '''.format('Yes' if SEOBSERVER_API_KEY else 'No')

# API pour analyser un domaine
@app.route('/api/analyze', methods=['POST'])
def analyze_domain():
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({'error': 'Le paramètre target est requis'}), 400
            
        target_domain = data['target'].strip()
        
        # Vérifier que la clé API est définie
        if not SEOBSERVER_API_KEY:
            return jsonify({'error': 'Clé API SEObserver non configurée'}), 500
        
        # Configuration de la requête pour SEObserver
        print(f"Clé API utilisée: {SEOBSERVER_API_KEY}")
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
        app.logger.error(f"Erreur inattendue: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Une erreur inattendue est survenue',
            'details': str(e)
        }), 500

def create_seo_analysis_image(domain, metrics, output_path):
    """Crée une image des résultats d'analyse SEO avec un design moderne et épuré"""
    try:
        print(f"Création de l'image pour {domain}")
        print(f"Métriques reçues: {metrics}")
        
        # Créer une nouvelle image avec fond blanc
        width, height = 1000, 600
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Charger les polices (essayer Arial, sinon utiliser la police par défaut)
        try:
            # Essayer différents chemins pour les polices
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "Arial.ttf",
                "Arial Bold.ttf"
            ]
            
            title_font = None
            for font_path in font_paths:
                try:
                    title_font = ImageFont.truetype(font_path, 36)
                    metric_font = ImageFont.truetype(font_path, 48)
                    text_font = ImageFont.truetype(font_path, 18)
                    break
                except:
                    continue
            
            if not title_font:
                raise Exception("Aucune police trouvée")
                
        except:
            # Utiliser la police par défaut si aucune police n'est trouvée
            print("Utilisation de la police par défaut")
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
            
            # Dessiner la carte (utiliser rectangle si rounded_rectangle n'est pas disponible)
            try:
                draw.rounded_rectangle(
                    [x, y, x + 400, y + 150],
                    radius=15,
                    fill=card_colors[i],
                    outline=secondary_color,
                    width=1
                )
            except AttributeError:
                # Si rounded_rectangle n'est pas disponible, utiliser rectangle normal
                draw.rectangle(
                    [x, y, x + 400, y + 150],
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
        print(f"Image sauvegardée : {output_path}")
        return True

    except Exception as e:
        print(f"Erreur dans create_seo_analysis_image: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/api/analyze/screenshot', methods=['POST'])
def analyze_and_screenshot():
    """Endpoint pour analyser un domaine et retourner l'URL de l'image générée"""
    data = request.get_json()
    domain = data.get('target')

    if not domain:
        return jsonify({'status': 'error', 'message': 'Le paramètre "target" est requis'}), 400

    if not SEOBSERVER_API_KEY:
        return jsonify({'status': 'error', 'message': 'Clé API SEObserver non configurée'}), 500

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
                metrics = {
                    'referring_domains': int(result_data.get('RefDomains', 0)) if result_data.get('RefDomains') is not None else 0,
                    'backlinks': int(result_data.get('ExtBackLinks', 0)) if result_data.get('ExtBackLinks') is not None else 0,
                    'active_domains': int(result_data.get('RefDomainTypeLive', 0)) if result_data.get('RefDomainTypeLive') is not None else 0,
                    'dofollow_domains': int(result_data.get('RefDomainTypeFollow', 0)) if result_data.get('RefDomainTypeFollow') is not None else 0
                }
                    
            except (ValueError, KeyError, IndexError) as e:
                app.logger.error(f"Erreur lors de l'extraction des données: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Erreur lors du traitement des données SEO',
                    'details': str(e)
                }), 500

            # 3. Générer la capture d'écran
            if not create_seo_analysis_image(domain, metrics, output_path):
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

            # Générer une URL publique pour l'image
            # Note: Cette partie dépend de votre système de stockage
            # Ici, on retourne simplement un lien vers l'endpoint qui sert l'image
            image_url = f"{request.host_url.rstrip('/')}/api/screenshot/{os.path.basename(output_path)}"
            
            # Copier le fichier temporaire vers un emplacement accessible
            import shutil
            final_path = os.path.join(tempfile.gettempdir(), os.path.basename(output_path))
            shutil.copy2(output_path, final_path)
            
            return jsonify({
                'status': 'success',
                'screenshot_url': image_url,
                'domain': domain,
                'metrics': metrics
            })
            
    except Exception as e:
        app.logger.error(f"Erreur inattendue: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Une erreur inattendue est survenue',
            'details': str(e)
        }), 500

# Endpoint pour servir les images générées
@app.route('/api/screenshot/<filename>')
def serve_screenshot(filename):
    try:
        # Vérifier que le fichier existe et est sécurisé
        safe_filename = os.path.basename(filename)
        if not safe_filename.endswith('.jpg'):
            return jsonify({'error': 'Invalid file type'}), 400
            
        # Dans un environnement de production, vous voudrez probablement stocker les images
        # dans un bucket de stockage cloud et les servir depuis là
        return send_from_directory(tempfile.gettempdir(), safe_filename, mimetype='image/jpeg')
    except Exception as e:
        app.logger.error(f"Error serving screenshot: {str(e)}")
        return jsonify({'error': 'Image not found'}), 404

# Point d'entrée principal
if __name__ == '__main__':
    # Ce bloc ne s'exécute que si le script est lancé directement (pas avec Gunicorn)
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Flask app on port {port}")
    print(f"API Key configured: {'Yes' if SEOBSERVER_API_KEY else 'No'}")
    app.run(host='0.0.0.0', port=port, debug=False)