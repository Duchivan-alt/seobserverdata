from flask import Flask, request, jsonify, render_template, send_file, make_response, send_from_directory
from flask_cors import CORS
import os
import requests
import json
import time
import io
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import math
import base64
import tempfile

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration de l'API SEObserver - Clé API en dur pour usage interne
SEOBSERVER_API_KEY = '67f7cfd05f469aee448b45a1G1ca36b5c89ba2f8a8dafd106a6e01668'

# Configuration du logging
app.logger.setLevel('INFO')
app.logger.info("=== Démarrage de l'application ===")
app.logger.info(f"Environnement FLASK_ENV: {os.environ.get('FLASK_ENV', 'non défini')}")
app.logger.info("Mode: Clé API intégrée (usage interne)")
app.logger.info(f"Clé API chargée: {'Oui' if SEOBSERVER_API_KEY else 'Non'}")
app.logger.info(f"Clé API (début): {SEOBSERVER_API_KEY[:5]}...")

if not SEOBSERVER_API_KEY:
    app.logger.error("ERREUR CRITIQUE: Aucune clé API n'est configurée")

SEOBSERVER_API_URL = 'https://api1.seobserver.com/backlinks/metrics.json'

# Configuration CORS pour accepter les requêtes depuis n'importe quelle origine
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
    """
    Crée une image des résultats d'analyse SEO avec les 4 métriques demandées :
    - Domaines référents
    - Backlinks
    - Domaines actifs
    - Domaines en dofollow
    
    Les chiffres sont affichés en plein (pas de contour) pour une meilleure lisibilité.
    
    Args:
        domain (str): Le nom de domaine à analyser
        metrics (dict): Dictionnaire des métriques SEO
        output_path (str): Chemin de sortie pour l'image générée
        
    Returns:
        bool: True si la création a réussi, False sinon
    """
    try:
        # Configuration des dimensions et des styles
        WIDTH = 800
        HEIGHT = 600
        CARD_WIDTH = 350
        CARD_HEIGHT = 200
        MARGIN = 40
        CARD_MARGIN = 20
        
        # Création de l'image avec fond blanc
        image = Image.new('RGB', (WIDTH, HEIGHT), color='white')
        draw = ImageDraw.Draw(image)
        
        # Palette de couleurs
        colors = {
            'primary': (44, 62, 80),      # Bleu foncé
            'secondary': (52, 152, 219),   # Bleu clair
            'accent1': (46, 204, 113),     # Vert
            'accent2': (230, 126, 34),     # Orange
            'text': (44, 62, 80),          # Texte foncé
            'background': (245, 246, 250),  # Fond gris clair
            'white': (255, 255, 255)       # Blanc
        }
        
        # Chargement des polices avec fallback
        try:
            title_font = ImageFont.truetype('Arial Bold', 28)
            metric_font = ImageFont.truetype('Arial Bold', 48)
            label_font = ImageFont.truetype('Arial', 16)
        except:
            # Fallback si les polices ne sont pas disponibles
            title_font = ImageFont.load_default()
            metric_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        
        # Dessiner l'en-tête
        header_height = 100
        draw.rectangle([0, 0, WIDTH, header_height], fill=colors['primary'])
        
        # Titre
        title = f"Analyse SEO - {domain}"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (WIDTH - title_width) // 2
        title_y = (header_height - (title_bbox[3] - title_bbox[1])) // 2
        
        draw.text((title_x, title_y), title, fill=colors['white'], font=title_font)
        
        # Définition des métriques à afficher
        metrics_to_display = [
            {'key': 'referring_domains', 'label': 'Domaines référents', 'color': colors['secondary']},
            {'key': 'backlinks', 'label': 'Backlinks', 'color': colors['accent1']},
            {'key': 'active_domains', 'label': 'Domaines actifs', 'color': colors['accent2']},
            {'key': 'dofollow_domains', 'label': 'Domaines en dofollow', 'color': (155, 89, 182)}  # Violet
        ]
        
        # Positionnement des cartes (grille 2x2)
        for i, metric in enumerate(metrics_to_display):
            row = i // 2
            col = i % 2
            
            x = MARGIN + col * (CARD_WIDTH + CARD_MARGIN)
            y = header_height + MARGIN + row * (CARD_HEIGHT + CARD_MARGIN)
            
            # Dessiner la carte
            card_rect = [x, y, x + CARD_WIDTH, y + CARD_HEIGHT]
            draw.rounded_rectangle(card_rect, radius=10, fill=colors['white'], outline=(220, 220, 220), width=1)
            
            # Ajouter une ombre portée
            shadow_rect = [x + 3, y + 3, x + CARD_WIDTH + 3, y + CARD_HEIGHT + 3]
            draw.rounded_rectangle(shadow_rect, radius=10, fill=(230, 230, 230))
            
            # Placer la carte par-dessus l'ombre
            draw.rounded_rectangle(card_rect, radius=10, fill=colors['white'], outline=(220, 220, 220), width=1)
            
            # Ajouter une barre de couleur en haut
            draw.rectangle([x, y, x + CARD_WIDTH, y + 5], fill=metric['color'])
            
            # Afficher la valeur
            value = str(metrics.get(metric['key'], 0))
            value_bbox = draw.textbbox((0, 0), value, font=metric_font)
            value_width = value_bbox[2] - value_bbox[0]
            value_height = value_bbox[3] - value_bbox[1]
            
            value_x = x + (CARD_WIDTH - value_width) // 2
            value_y = y + 40
            
            # Afficher la valeur en plein (sans contour)
            draw.text((value_x, value_y), value, fill=metric['color'], font=metric_font)
            
            # Afficher le label
            label_bbox = draw.textbbox((0, 0), metric['label'], font=label_font)
            label_width = label_bbox[2] - label_bbox[0]
            
            label_x = x + (CARD_WIDTH - label_width) // 2
            label_y = value_y + value_height + 10
            
            draw.text((label_x, label_y), metric['label'], fill=colors['text'], font=label_font)
        
        # Ajouter un pied de page
        footer_height = 40
        footer_y = HEIGHT - footer_height
        draw.rectangle([0, footer_y, WIDTH, HEIGHT], fill=colors['primary'])
        
        # Ajouter la date et le copyright
        date_str = datetime.now().strftime('%d/%m/%Y')
        copyright_text = f"© {date_str} - Tous droits réservés"
        
        copyright_bbox = draw.textbbox((0, 0), copyright_text, font=label_font)
        copyright_width = copyright_bbox[2] - copyright_bbox[0]
        
        draw.text(
            (WIDTH - copyright_width - 20, footer_y + (footer_height - (copyright_bbox[3] - copyright_bbox[1])) // 2),
            copyright_text,
            fill=colors['white'],
            font=label_font
        )
        
        # Enregistrer l'image
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        image.save(output_path, 'JPEG', quality=95)
        return True
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la création de l'image : {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return False

@app.route('/api/analyze/screenshot', methods=['POST'])
def analyze_and_screenshot():
    app.logger.info('Received request to /api/analyze/screenshot')
    try:
        data = request.get_json()
        app.logger.info(f'Request data: {data}')
        
        if not data:
            app.logger.error('No JSON data received in request')
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
        domain = data.get('target')
        if not domain:
            app.logger.error('No target parameter provided')
            return jsonify({'status': 'error', 'message': 'Le paramètre "target" est requis'}), 400
            
        if not SEOBSERVER_API_KEY:
            app.logger.error('SEOBSERVER_API_KEY is not configured')
            return jsonify({'status': 'error', 'message': 'Clé API SEObserver non configurée'}), 500

        app.logger.info(f"=== NOUVELLE DEMANDE ===")
        app.logger.info(f"Début de l'analyse pour le domaine: {domain}")
        app.logger.info(f"Clé API: {'Définie' if SEOBSERVER_API_KEY else 'Non définie'}")
        
        # Créer un répertoire temporaire s'il n'existe pas
        os.makedirs(tempfile.gettempdir(), exist_ok=True)
        
        # Créer un répertoire temporaire pour stocker les captures d'écran
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, 'screenshot.jpg')
            app.logger.info(f"Dossier temporaire: {temp_dir}")
            app.logger.info(f"Chemin de sortie: {output_path}")
            
            # Vérifier les permissions
            try:
                test_file = os.path.join(temp_dir, 'test.txt')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                app.logger.info("Test d'écriture/réussite dans le dossier temporaire")
            except Exception as e:
                app.logger.error(f"Erreur d'accès au dossier temporaire: {str(e)}")
                raise

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

            app.logger.info(f"Envoi de la requête à l'API SEObserver: {SEOBSERVER_API_URL}")
            app.logger.info(f"Headers: {headers}")
            app.logger.info(f"Payload: {payload}")
            
            try:
                analysis_response = requests.post(
                    SEOBSERVER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                app.logger.info(f"Réponse reçue - Status: {analysis_response.status_code}")
                app.logger.info(f"Contenu de la réponse: {analysis_response.text[:500]}...")  # Limite à 500 caractères
            except Exception as e:
                app.logger.error(f"Erreur lors de l'appel à l'API SEObserver: {str(e)}")
                raise

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
            
    except requests.exceptions.RequestException as e:
        app.logger.error(f'Request error in analyze_and_screenshot: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Erreur réseau lors de l\'appel à l\'API SEObserver: {str(e)}'
        }), 500
    except Exception as e:
        app.logger.error(f'Unexpected error in analyze_and_screenshot: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error', 
            'message': 'Erreur interne du serveur',
            'error_details': str(e)
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
    # Afficher les variables d'environnement (sans les valeurs sensibles)
    print("=== Variables d'environnement ===")
    for key, value in sorted(os.environ.items()):
        if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower() or 'password' in key.lower():
            value = '********' if value else 'non défini'
        print(f"{key}: {value}")
    print("================================")
    
    port = int(os.environ.get('PORT', 8080))
    print(f"\nDémarrage de l'application sur le port {port}")
    print(f"Clé API configurée: {'Oui' if SEOBSERVER_API_KEY else 'Non'}")
    if SEOBSERVER_API_KEY:
        print(f"Clé API (tronquée): {SEOBSERVER_API_KEY[:5]}...{SEOBSERVER_API_KEY[-5:]}")
    
    app.run(host='0.0.0.0', port=port, debug=True)