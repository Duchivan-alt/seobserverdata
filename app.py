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
    Crée une image des résultats d'analyse SEO avec le design moderne Octave
    Reproduit le style de la visualisation web en image statique
    """
    try:
        # Configuration des dimensions
        WIDTH = 1200
        HEIGHT = 800
        
        # Créer l'image avec fond dégradé
        image = Image.new('RGB', (WIDTH, HEIGHT), color='white')
        draw = ImageDraw.Draw(image)
        
        # Palette de couleurs Octave
        colors = {
            'primary_blue': (37, 99, 235),       # #2563eb
            'primary_blue_dark': (30, 64, 175),  # #1e40af
            'turquoise': (66, 211, 186),         # #42d3ba
            'green': (34, 197, 94),              # #22c55e
            'orange': (255, 154, 0),             # #ff9a00
            'orange_dark': (245, 158, 11),       # #f59e0b
            'purple': (139, 92, 246),            # #8b5cf6
            'purple_dark': (168, 85, 247),       # #a855f7
            'white': (255, 255, 255),
            'light_gray': (248, 250, 252),       # #f8fafc
            'medium_gray': (226, 232, 240),      # #e2e8f0
            'text_dark': (30, 41, 59),           # #1e293b
            'text_medium': (100, 116, 139),      # #64748b
            'slate_dark': (51, 65, 85),          # #334155
        }
        
        # Créer le dégradé de fond
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(colors['light_gray'][0] + (colors['medium_gray'][0] - colors['light_gray'][0]) * ratio)
            g = int(colors['light_gray'][1] + (colors['medium_gray'][1] - colors['light_gray'][1]) * ratio)
            b = int(colors['light_gray'][2] + (colors['medium_gray'][2] - colors['light_gray'][2]) * ratio)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
        
        # Ajouter des cercles décoratifs en arrière-plan (très transparents)
        # Cercle 1
        circle1_alpha = Image.new('RGBA', (100, 100), (66, 211, 186, 25))
        image.paste(circle1_alpha, (60, 80), circle1_alpha)
        
        # Cercle 2
        circle2_alpha = Image.new('RGBA', (80, 80), (255, 154, 0, 25))
        image.paste(circle2_alpha, (WIDTH-140, 160), circle2_alpha)
        
        # Cercle 3
        circle3_alpha = Image.new('RGBA', (120, 120), (139, 92, 246, 25))
        image.paste(circle3_alpha, (96, HEIGHT-220), circle3_alpha)
        
        # Chargement des polices
        try:
            title_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 40)
            subtitle_font = ImageFont.truetype('DejaVuSans.ttf', 18)
            metric_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 48)
            label_font = ImageFont.truetype('DejaVuSans.ttf', 18)
            footer_font = ImageFont.truetype('DejaVuSans.ttf', 14)
            icon_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 24)
        except:
            # Fallback vers police par défaut
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            metric_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
            footer_font = ImageFont.load_default()
            icon_font = ImageFont.load_default()  # Garde au cas où
        
        # === HEADER ===
        header_height = 120
        header_padding = 40
        
        # Fond du header avec dégradé
        for y in range(header_height):
            ratio = y / header_height
            r = int(colors['primary_blue'][0] + (colors['primary_blue_dark'][0] - colors['primary_blue'][0]) * ratio)
            g = int(colors['primary_blue'][1] + (colors['primary_blue_dark'][1] - colors['primary_blue'][1]) * ratio)
            b = int(colors['primary_blue'][2] + (colors['primary_blue_dark'][2] - colors['primary_blue'][2]) * ratio)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
        
        # Coins arrondis du header (approximation)
        corner_radius = 24
        # Effacer les coins avec la couleur de fond
        for i in range(corner_radius):
            for j in range(corner_radius):
                distance = (i**2 + j**2)**0.5
                if distance > corner_radius:
                    # Coin supérieur gauche
                    draw.point((i, j), fill=colors['light_gray'])
                    # Coin supérieur droit
                    draw.point((WIDTH-1-i, j), fill=colors['light_gray'])
        
        # Ajouter des éléments décoratifs au header
        # Cercle décoratif 1
        circle_overlay = Image.new('RGBA', (200, 200), (66, 211, 186, 51))
        image.paste(circle_overlay, (WIDTH-300, -100), circle_overlay)
        
        # Cercle décoratif 2
        circle_overlay2 = Image.new('RGBA', (150, 150), (255, 182, 193, 77))
        image.paste(circle_overlay2, (-75, 50), circle_overlay2)
        
        # Icône de recherche
        icon_x = header_padding
        icon_y = 30
        icon_size = 60
        
        # Fond de l'icône
        icon_bg_color = tuple(int(c * 0.8) for c in colors['primary_blue'])  # Plus sombre
        draw.ellipse([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size], 
                     fill=icon_bg_color, outline=colors['white'], width=2)
        
        # Loupe
        loupe_center_x = icon_x + icon_size // 2
        loupe_center_y = icon_y + icon_size // 2
        loupe_radius = 12
        
        # Cercle de la loupe
        draw.ellipse([loupe_center_x - loupe_radius, loupe_center_y - loupe_radius,
                     loupe_center_x + loupe_radius, loupe_center_y + loupe_radius],
                     outline=colors['white'], width=3)
        
        # Manche de la loupe
        handle_start_x = loupe_center_x + int(loupe_radius * 0.7)
        handle_start_y = loupe_center_y + int(loupe_radius * 0.7)
        handle_end_x = loupe_center_x + loupe_radius + 10
        handle_end_y = loupe_center_y + loupe_radius + 10
        draw.line([(handle_start_x, handle_start_y), (handle_end_x, handle_end_y)],
                 fill=colors['white'], width=3)
        
        # Texte du header
        text_x = icon_x + icon_size + 20
        title_text = "Analyse SEO"
        draw.text((text_x, 30), title_text, fill=colors['white'], font=title_font)
        
        subtitle_text = f"Rapport d'analyse pour {domain}"
        draw.text((text_x, 75), subtitle_text, fill=colors['white'], font=subtitle_font)
        
        # === CARTES MÉTRIQUES ===
        card_width = 280
        card_height = 180
        margin_x = 60
        margin_y = 40
        spacing_x = 24
        spacing_y = 30
        
        start_y = header_height + margin_y
        
        # Configuration des métriques
        metrics_config = [
            {
                'key': 'referring_domains',
                'label': 'Domaines référents',
                'color': colors['primary_blue'],
                'gradient_end': (59, 130, 246),  # #3b82f6
                'border_color': colors['primary_blue']
            },
            {
                'key': 'backlinks',
                'label': 'Backlinks totaux',
                'color': colors['turquoise'],
                'gradient_end': colors['green'],
                'border_color': colors['turquoise']
            },
            {
                'key': 'active_domains',
                'label': 'Domaines actifs',
                'color': colors['orange'],
                'gradient_end': colors['orange_dark'],
                'border_color': colors['orange']
            },
            {
                'key': 'dofollow_domains',
                'label': 'Domaines DoFollow',
                'color': colors['purple'],
                'gradient_end': colors['purple_dark'],
                'border_color': colors['purple']
            }
        ]
        
        # Dessiner les cartes en grille 2x2
        for i, metric_config in enumerate(metrics_config):
            row = i // 2
            col = i % 2
            
            x = margin_x + col * (card_width + spacing_x)
            y = start_y + row * (card_height + spacing_y)
            
            # Ombre portée
            shadow_offset = 8
            shadow_color = (0, 0, 0, 25)
            shadow_overlay = Image.new('RGBA', (card_width, card_height), shadow_color)
            image.paste(shadow_overlay, (x + shadow_offset, y + shadow_offset), shadow_overlay)
            
            # Fond de la carte
            draw.rounded_rectangle([x, y, x + card_width, y + card_height],
                                 radius=20, fill=colors['white'])
            
            # Bordure colorée en haut
            border_height = 6
            draw.rounded_rectangle([x, y, x + card_width, y + border_height + 15],
                                 radius=20, fill=metric_config['border_color'])
            draw.rectangle([x, y + 15, x + card_width, y + border_height + 15],
                          fill=metric_config['border_color'])
            
            # Icône avec fond dégradé (approximation)
            icon_size = 64
            icon_x = x + 32
            icon_y = y + 25
            
            # Fond coloré de l'icône
            draw.rounded_rectangle([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size],
                                 radius=16, fill=metric_config['color'])
            
            # Lettre de l'icône
            icon_letter = metric_config['icon']
            # Centrer la lettre dans l'icône
            letter_bbox = draw.textbbox((0, 0), icon_letter, font=icon_font)
            letter_width = letter_bbox[2] - letter_bbox[0]
            letter_height = letter_bbox[3] - letter_bbox[1]
            letter_x = icon_x + (icon_size - letter_width) // 2
            letter_y = icon_y + (icon_size - letter_height) // 2
            
            draw.text((letter_x, letter_y), icon_letter, fill=colors['white'], font=icon_font)
            
            # Valeur métrique
            value = f"{metrics.get(metric_config['key'], 0):,}".replace(',', ' ')
            value_bbox = draw.textbbox((0, 0), value, font=metric_font)
            value_width = value_bbox[2] - value_bbox[0]
            value_x = x + (card_width - value_width) // 2
            value_y = y + 95
            
            # Ombre du texte
            draw.text((value_x + 2, value_y + 2), value, fill=(0, 0, 0, 50), font=metric_font)
            # Texte principal
            draw.text((value_x, value_y), value, fill=colors['text_dark'], font=metric_font)
            
            # Label
            label_text = metric_config['label']
            label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
            label_width = label_bbox[2] - label_bbox[0]
            label_x = x + (card_width - label_width) // 2
            label_y = value_y + 60
            
            draw.text((label_x, label_y), label_text, fill=colors['text_medium'], font=label_font)
        
        # === FOOTER ===
        footer_height = 60
        footer_y = HEIGHT - footer_height
        
        # Fond du footer avec dégradé
        for y in range(footer_y, HEIGHT):
            ratio = (y - footer_y) / footer_height
            r = int(colors['text_dark'][0] + (colors['slate_dark'][0] - colors['text_dark'][0]) * ratio)
            g = int(colors['text_dark'][1] + (colors['slate_dark'][1] - colors['text_dark'][1]) * ratio)
            b = int(colors['text_dark'][2] + (colors['slate_dark'][2] - colors['text_dark'][2]) * ratio)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
        
        # Coins arrondis du footer
        for i in range(corner_radius):
            for j in range(corner_radius):
                distance = (i**2 + j**2)**0.5
                if distance > corner_radius:
                    # Coin inférieur gauche
                    draw.point((i, HEIGHT-1-j), fill=colors['medium_gray'])
                    # Coin inférieur droit
                    draw.point((WIDTH-1-i, HEIGHT-1-j), fill=colors['medium_gray'])
        
        # Ligne décorative colorée en haut du footer
        gradient_line_height = 3
        line_colors = [colors['turquoise'], colors['orange'], colors['purple']]
        section_width = WIDTH // len(line_colors)
        
        for i, line_color in enumerate(line_colors):
            start_x = i * section_width
            end_x = (i + 1) * section_width if i < len(line_colors) - 1 else WIDTH
            draw.rectangle([start_x, footer_y, end_x, footer_y + gradient_line_height], 
                          fill=line_color)
        
        # Texte du footer
        date_str = datetime.now().strftime('%d %B %Y à %H:%M')
        footer_text1 = f"Généré le {date_str}"
        footer_text2 = "Powered by Octave SEO"
        
        # Centrer le texte
        text1_bbox = draw.textbbox((0, 0), footer_text1, font=footer_font)
        text1_width = text1_bbox[2] - text1_bbox[0]
        text1_x = (WIDTH - text1_width) // 2
        text1_y = footer_y + 12
        
        text2_bbox = draw.textbbox((0, 0), footer_text2, font=footer_font)
        text2_width = text2_bbox[2] - text2_bbox[0]
        text2_x = (WIDTH - text2_width) // 2
        text2_y = footer_y + 32
        
        draw.text((text1_x, text1_y), footer_text1, fill=colors['white'], font=footer_font)
        # "Octave SEO" en couleur turquoise
        octave_part = "Powered by "
        octave_bbox = draw.textbbox((0, 0), octave_part, font=footer_font)
        octave_width = octave_bbox[2] - octave_bbox[0]
        
        draw.text((text2_x, text2_y), octave_part, fill=colors['white'], font=footer_font)
        draw.text((text2_x + octave_width, text2_y), "Octave SEO", fill=colors['turquoise'], font=footer_font)
        
        # Enregistrer l'image
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        image.save(output_path, 'PNG', quality=95, optimize=True)
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
            # Ici, on retourne simplement un lien vers l'endpoint qui sert l'image on retourne simplement un lien vers l'endpoint qui sert l'image
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