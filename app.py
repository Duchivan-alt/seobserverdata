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
    Crée une image des résultats d'analyse SEO avec un design moderne et épuré
    
    Args:
        domain (str): Le nom de domaine à analyser
        metrics (dict): Dictionnaire des métriques SEO
        output_path (str): Chemin de sortie pour l'image générée
        
    Returns:
        bool: True si la création a réussi, False sinon
    """
    try:
        app.logger.info(f"Création de l'image pour {domain}")
        
        # Configuration des chemins de police avec fallback
        FONT_PATHS = [
            'arial.ttf', 'Arial.ttf', 'Arial',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
        ]
        
        # Palette de couleurs moderne
        COLORS = {
            'primary': (0, 119, 181),      # Bleu professionnel
            'secondary': (72, 61, 139),    # Bleu nuit
            'accent': (255, 87, 34),       # Orange vif
            'accent2': (76, 175, 80),      # Vert émeraude
            'accent3': (156, 39, 176),     # Violet
            'background': (250, 250, 252),  # Blanc cassé
            'card_bg': (255, 255, 255),    # Blanc pur
            'header_gradient1': (0, 119, 181),  # Début dégradé
            'header_gradient2': (0, 150, 199),  # Fin dégradé
            'text_primary': (33, 33, 33),   # Noir profond
            'text_secondary': (97, 97, 97), # Gris foncé
            'text_light': (255, 255, 255),  # Blanc
            'success': (46, 204, 113),      # Vert
            'warning': (255, 152, 0),       # Orange
            'danger': (244, 67, 54),        # Rouge
            'border': (224, 224, 224)       # Gris clair
        }
        
        # Définition des métriques à afficher
        METRICS_CONFIG = [
            {'key': 'score', 'label': 'SCORE GLOBAL', 'icon': '', 'color': 'accent'},
            {'key': 'pages', 'label': 'PAGES INDEXÉES', 'icon': '', 'color': 'primary'},
            {'key': 'backlinks', 'label': 'BACKLINKS', 'icon': '', 'color': 'accent3'},
            {'key': 'ref_domains', 'label': 'DOMAINES RÉFÉRENTS', 'icon': '', 'color': 'accent2'},
            {'key': 'traffic', 'label': 'EST. TRAFIC MENSUEL', 'icon': '', 'color': 'warning'},
            {'key': 'keywords', 'label': 'MOTS-CLÉS', 'icon': '', 'color': 'danger'}
        ]
        
        # Configuration du style
        STYLE = {
            'width': 1200,
            'height': 1000,
            'header_height': 180,
            'footer_height': 80,
            'card': {
                'width': 550,
                'height': 200,
                'padding': 25,
                'corner_radius': 15,
                'shadow': (3, 3, 10, (0, 0, 0, 15))
            },
            'font_sizes': {
                'title': 42,
                'subtitle': 28,
                'metric': 64,
                'label': 14,
                'footer': 12
            }
        }
        
        # Fonction utilitaire pour charger une police avec fallback
        def get_font(size, is_bold=False):
            """Charge une police avec gestion des erreurs et fallback"""
            font_name = 'Arial-Bold' if is_bold else 'Arial'
            for font_path in FONT_PATHS:
                try:
                    return ImageFont.truetype(font_path, size)
                except (IOError, OSError):
                    continue
            # Fallback sur la police par défaut
            try:
                return ImageFont.truetype(font_name, size)
            except:
                return ImageFont.load_default()
        
        # Création de l'image de base
        image = Image.new('RGB', (STYLE['width'], STYLE['height']), color=COLORS['background'])
        draw = ImageDraw.Draw(image, 'RGBA')
        
        # 1. Dessiner l'en-tête avec dégradé
        for i in range(STYLE['header_height']):
            ratio = i / STYLE['header_height']
            r = int(COLORS['header_gradient1'][0] + (COLORS['header_gradient2'][0] - COLORS['header_gradient1'][0]) * ratio)
            g = int(COLORS['header_gradient1'][1] + (COLORS['header_gradient2'][1] - COLORS['header_gradient1'][1]) * ratio)
            b = int(COLORS['header_gradient1'][2] + (COLORS['header_gradient2'][2] - COLORS['header_gradient1'][2]) * ratio)
            draw.line([(0, i), (STYLE['width'], i)], fill=(r, g, b))
        
        # 2. Ajouter les éléments décoratifs de l'en-tête
        
        # Motif géométrique subtil dans l'en-tête
        for i in range(0, STYLE['width'] + 100, 30):
            draw.arc([i - 50, -50, i + 50, 50], 0, 180, 
                    fill=(255, 255, 255, 10), width=2)
            
        # Effet de vague subtil en bas de l'en-tête
        wave_height = 20
        for i in range(wave_height):
            y = STYLE['header_height'] - i
            alpha = int(30 * (1 - i/wave_height))
            # Créer un effet de vague avec des courbes de Bézier
            points = []
            for x in range(0, STYLE['width'] + 200, 200):
                points.extend([
                    (x, y + math.sin(x/100) * 5 * (i/wave_height)),
                    (x + 100, y + math.cos(x/100) * 5 * (i/wave_height))
                ])
            if len(points) > 1:
                draw.line(points, fill=(255, 255, 255, alpha), width=2, joint='curve')
        
        # 3. Ajouter le titre et le sous-titre
        title = "ANALYSE SEO"
        subtitle = domain.upper()
        
        # Charger les polices
        title_font = get_font(STYLE['font_sizes']['title'], is_bold=True)
        subtitle_font = get_font(STYLE['font_sizes']['subtitle'] - 4, is_bold=True)
        
        # Positionner le titre
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_x, title_y = 40, 40
        
        # Ajouter un fond semi-transparent au titre
        padding = 20
        draw.rectangle(
            [
                title_x - padding, 
                title_y - padding//2,
                title_x + title_bbox[2] + padding,
                title_y + title_bbox[3] + padding//2
            ], 
            fill=(255, 255, 255, 30), 
            outline=(255, 255, 255, 60), 
            width=2
        )
        
        # Dessiner le titre avec ombre portée
        draw.text(
            (title_x + 2, title_y + 2), 
            title, 
            fill=(0, 0, 0, 50), 
            font=title_font
        )
        draw.text(
            (title_x, title_y), 
            title, 
            fill=COLORS['text_light'], 
            font=title_font, 
            stroke_width=1, 
            stroke_fill=(0, 0, 0, 30)
        )
        
        # Ajouter le sous-titre
        subtitle_y = title_y + title_bbox[3] + 5
        draw.text(
            (title_x, subtitle_y), 
            subtitle, 
            fill=COLORS['accent'], 
            font=subtitle_font, 
            stroke_width=1, 
            stroke_fill=(0, 0, 0, 20)
        )
            
        # 4. Ajouter les cartes de métriques
        card = STYLE['card']
        start_y = STYLE['header_height'] + 40
        
        for i, metric in enumerate(METRICS_CONFIG):
            # Position de la carte (grille 2x3)
            row = i // 2
            col = i % 2
            x = 40 + col * (card['width'] + 30)
            y = start_y + row * (card['height'] + 20)
            
            # Couleur de la métrique
            color = COLORS[metric['color']]
            
            # Dessiner l'ombre de la carte
            shadow = card['shadow']
            draw.rounded_rectangle(
                [x + shadow[0], y + shadow[1], 
                 x + card['width'] + shadow[0], y + card['height'] + shadow[1]],
                radius=card['corner_radius'],
                fill=shadow[3]
            )
            
            # Dessiner la carte
            draw.rounded_rectangle(
                [x, y, x + card['width'], y + card['height']],
                radius=card['corner_radius'],
                fill=COLORS['card_bg']
            )
            
            # Ajouter une bordure subtile
            draw.rounded_rectangle(
                [x + 1, y + 1, x + card['width'] - 1, y + card['height'] - 1],
                radius=card['corner_radius'] - 1,
                outline=COLORS['border'],
                width=1
            )
            
            # Afficher la valeur de la métrique
            value = str(metrics.get(metric['key'], 'N/A'))
            value_font = get_font(STYLE['font_sizes']['metric'], is_bold=True)
            
            # Centrer la valeur dans la carte
            value_bbox = draw.textbbox((0, 0), value, font=value_font)
            value_x = x + card['width'] // 2
            value_y = y + (card['height'] - value_bbox[3]) // 2 - 10
            
            # Ajouter un effet d'ombre portée
            draw.text(
                (value_x + 3, value_y + 3), 
                value, 
                fill=(0, 0, 0, 30), 
                font=value_font,
                anchor="mm"
            )
            
            # Dessiner la valeur principale (en blanc avec contour)
            draw.text(
                (value_x, value_y), 
                value, 
                fill=COLORS['text_light'], 
                font=value_font,
                anchor="mm",
                stroke_width=3,
                stroke_fill=color
            )
            
            # Afficher le label de la métrique
            label_font = get_font(STYLE['font_sizes']['label'], is_bold=True)
            draw.text(
                (x + card['padding'], y + card['padding']), 
                metric['label'], 
                fill=COLORS['text_secondary'], 
                font=label_font
            )
            
            # Ajouter une barre de couleur en bas
            bar_height = 6
            bar_rect = [
                x + card['corner_radius'] // 2,
                y + card['height'] - bar_height,
                x + card['width'] - card['corner_radius'] // 2,
                y + card['height']
            ]
            
            # Dégradé pour la barre de couleur
            for j in range(bar_rect[2] - bar_rect[0]):
                alpha = int(255 * (j / (bar_rect[2] - bar_rect[0])))
                draw.line(
                    [(bar_rect[0] + j, bar_rect[1]), (bar_rect[0] + j, bar_rect[3])],
                    fill=color + (alpha,)
                )
        
        # 5. Ajouter le pied de page
        footer_y = STYLE['height'] - STYLE['footer_height']
        
        # Dégradé pour le pied de page
        for i in range(STYLE['footer_height']):
            alpha = int(150 * (1 - i/STYLE['footer_height']))
            r = int(COLORS['primary'][0] * (i/STYLE['footer_height']))
            g = int(COLORS['primary'][1] * (i/STYLE['footer_height']))
            b = int(COLORS['primary'][2] * (i/STYLE['footer_height']))
            draw.line([(0, footer_y + i), (STYLE['width'], footer_y + i)], 
                     fill=(r, g, b, alpha))
        
        # Ajouter un motif géométrique subtil dans le footer
        for i in range(0, STYLE['width'] + 200, 40):
            draw.arc(
                [i - 150, STYLE['height'] - 50, i + 50, STYLE['height'] + 150], 
                180, 360, 
                fill=(255, 255, 255, 10), 
                width=2
            )
        
        # Ajouter la date et le copyright
        current_year = datetime.now().strftime("%Y")
        date_str = datetime.now().strftime("%d %B %Y | %H:%M")
        
        # Police pour le footer
        footer_font = get_font(STYLE['font_sizes']['footer'])
        
        # Texte du copyright
        copyright_text = f"© {current_year} SEO Analyzer | Tous droits réservés"
        
        # Positionner les textes
        date_bbox = draw.textbbox((0, 0), date_str, font=footer_font)
        copyright_bbox = draw.textbbox((0, 0), copyright_text, font=footer_font)
        
        # Position du texte de date (à droite)
        date_x = STYLE['width'] - date_bbox[2] - 30
        date_y = STYLE['height'] - (STYLE['footer_height'] // 2) - (date_bbox[3] // 2) - 10
        
        # Position du copyright (à gauche)
        copyright_x = 30
        copyright_y = STYLE['height'] - (STYLE['footer_height'] // 2) - (copyright_bbox[3] // 2) - 10
        
        # Dessiner les textes avec ombre portée
        draw.text(
            (date_x + 1, date_y + 1), 
            date_str, 
            fill=(0, 0, 0, 100), 
            font=footer_font
        )
        draw.text(
            (date_x, date_y), 
            date_str, 
            fill=(255, 255, 255, 220), 
            font=footer_font
        )
        
        draw.text(
            (copyright_x + 1, copyright_y + 1), 
            copyright_text, 
            fill=(0, 0, 0, 100), 
            font=footer_font
        )
        draw.text(
            (copyright_x, copyright_y), 
            copyright_text, 
            fill=(255, 255, 255, 180), 
            font=footer_font
        )
        
        # Ajouter une ligne de séparation
        line_y = footer_y - 1
        draw.line(
            [(0, line_y), (STYLE['width'], line_y)], 
            fill=(255, 255, 255, 50), 
            width=1
        )
        
        # 6. Enregistrer l'image
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        image.save(output_path, 'JPEG', quality=95)
        app.logger.info(f"Image sauvegardée : {output_path}")
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