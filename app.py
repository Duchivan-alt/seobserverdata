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
    """Crée une image des résultats d'analyse SEO avec un design moderne et épuré"""
    try:
        print(f"Création de l'image pour {domain}")
        print(f"Métriques reçues: {metrics}")
        
        # Chemins des polices à essayer
        font_paths = [
            'Arial',
            'Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
        ]
        
        # Palette de couleurs moderne
        colors = {
            'primary': (41, 128, 185),    # Bleu moderne
            'secondary': (52, 152, 219),  # Bleu clair
            'accent': (46, 204, 113),     # Vert vif
            'background': (247, 249, 252), # Gris très clair
            'card_bg': (255, 255, 255),   # Blanc pur
            'text_primary': (44, 62, 80),  # Bleu foncé pour le texte
            'text_secondary': (127, 140, 141),  # Gris pour le texte secondaire
            'success': (46, 204, 113),     # Vert
            'warning': (241, 196, 15),     # Jaune
            'danger': (231, 76, 60)        # Rouge
        }
        
        # Créer une nouvelle image avec fond dégradé
        width, height = 1000, 700
        image = Image.new('RGB', (width, height), colors['background'])
        draw = ImageDraw.Draw(image)
        
        # Ajouter un dégradé de fond
        for i in range(height):
            # Dégradé léger du haut vers le bas
            r = int(colors['background'][0] + (255 - colors['background'][0]) * (i / height))
            g = int(colors['background'][1] + (255 - colors['background'][1]) * (i / height))
            b = int(colors['background'][2] + (255 - colors['background'][2]) * (i / height))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        # Charger les polices avec des tailles augmentées
        try:
            # Essayer d'abord avec Arial
            title_font = ImageFont.truetype("Arial", 42)  # Taille augmentée
            metric_label_font = ImageFont.truetype("Arial", 28)  # Taille augmentée
            metric_font = ImageFont.truetype("Arial", 64)  # Taille augmentée
        except IOError:
            # Si Arial n'est pas disponible, essayer avec la police par défaut
            try:
                default_font = ImageFont.load_default()
                title_font = default_font.font_variant(size=42) if hasattr(default_font, 'font_variant') else default_font
                metric_label_font = default_font.font_variant(size=28) if hasattr(default_font, 'font_variant') else default_font
                metric_font = default_font.font_variant(size=64) if hasattr(default_font, 'font_variant') else default_font
            except Exception as e:
                app.logger.error(f"Erreur lors du chargement des polices: {str(e)}")
                raise
        
        # Dessiner un en-tête avec fond coloré
        header_height = 100
        draw.rectangle([0, 0, width, header_height], fill=colors['primary'])
        
        # Ajouter un effet de vague subtil en bas de l'en-tête
        for i in range(10):
            y = header_height - i
            alpha = int(255 * (1 - i/10))
            draw.line([(0, y), (width, y)], fill=colors['primary'] + (alpha,), width=1)
        
        # Dessiner le titre
        title = f"ANALYSE SEO - {domain.upper()}"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        
        # Ombre portée pour le titre
        draw.text(
            ((width - title_width) // 2 + 2, 42),  # Position de l'ombre
            title,
            fill=(0, 0, 0, 100),
            font=title_font
        )
        
        # Titre principal
        draw.text(
            ((width - title_width) // 2, 40),
            title,
            fill=(255, 255, 255),  # Blanc
            font=title_font,
            stroke_width=1,
            stroke_fill=(255, 255, 255, 50)
        )
        
        # Position de départ pour les métriques avec plus d'espace
        y_position = 140
        
        # Définir les métriques avec des icônes et des couleurs
        metric_items = [
            ("DOMAINES REFERENTS", metrics.get('referring_domains', 0), "🌐", colors['primary']),
            ("BACKLINKS", metrics.get('backlinks', 0), "🔗", colors['accent']),
            ("DOMAINES ACTIFS", metrics.get('active_domains', 0), "✅", colors['success']),
            ("DOMAINES DOFOLLOW", metrics.get('dofollow_domains', 0), "🔍", colors['warning'])
        ]
        
        # Style des cartes
        card_style = {
            'padding': 25,
            'spacing': 30,
            'corner_radius': 15,
            'shadow_offset': (3, 3),
            'shadow_blur': 10
        }
        
        # Afficher les métriques dans une grille 2x2 avec style amélioré
        card_width = 450
        card_height = 200
        for i, (label, value, icon, color) in enumerate(metric_items):
            # Position de la carte avec espacement
            row = i // 2
            col = i % 2
            x = 50 + col * (card_width + card_style['spacing'])
            y = y_position + row * (card_height + card_style['spacing'])
            
            # Ombre portée
            shadow = (x + card_style['shadow_offset'][0], 
                     y + card_style['shadow_offset'][1], 
                     x + card_width - card_style['shadow_offset'][0], 
                     y + card_height - card_style['shadow_offset'][1])
            
            # Dessiner l'ombre
            shadow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)
            shadow_draw.rounded_rectangle(
                shadow,
                radius=card_style['corner_radius'],
                fill=(0, 0, 0, 30)  # Noir avec transparence
            )
            image = Image.alpha_composite(image.convert('RGBA'), shadow_layer).convert('RGB')
            draw = ImageDraw.Draw(image)
            
            # Dessiner la carte avec bordure arrondie
            try:
                draw.rounded_rectangle(
                    [x, y, x + card_width - card_style['shadow_offset'][0], 
                     y + card_height - card_style['shadow_offset'][1]],
                    radius=card_style['corner_radius'],
                    fill=colors['card_bg'],
                    outline=(220, 220, 220),
                    width=1
                )
            except AttributeError:
                draw.rectangle(
                    [x, y, x + card_width - card_style['shadow_offset'][0], 
                     y + card_height - card_style['shadow_offset'][1]],
                    fill=colors['card_bg'],
                    outline=(220, 220, 220),
                    width=1
                )
                
            # Ajouter un effet de dégradé subtil
            for j in range(10):
                alpha = int(100 * (1 - j/10))
                draw.line(
                    [(x + j*2, y), (x + j*2, y + card_height - card_style['shadow_offset'][1])], 
                    fill=color + (alpha,)
                )
            
            # Dessiner l'icône
            icon_size = 30
            icon_x = x + card_style['padding']
            icon_y = y + card_style['padding']
            
            # Cercle de fond pour l'icône
            icon_bg_size = icon_size + 10
            icon_bg_x = icon_x - 5
            icon_bg_y = icon_y - 5
            
            draw.ellipse(
                [icon_bg_x, icon_bg_y, 
                 icon_bg_x + icon_bg_size, icon_bg_y + icon_bg_size],
                fill=color + (30,)  # Couleur avec transparence
            )
            
            # Dessiner l'icône
            draw.text(
                (icon_x, icon_y),
                icon,
                fill=color,
                font=ImageFont.truetype("Arial", icon_size) if 'Arial' in font_paths else metric_label_font
            )
            
            # Dessiner le label
            label_upper = label.upper()
            label_bbox = draw.textbbox((0, 0), label_upper, font=metric_label_font)
            label_x = x + card_style['padding'] + icon_bg_size + 10
            label_y = y + card_style['padding'] + (icon_size - label_bbox[3]) // 2
            
            draw.text(
                (label_x, label_y),
                label_upper,
                fill=colors['text_primary'],
                font=metric_label_font
            )
            
            # Dessiner la valeur avec style
            value_str = str(value)
            value_bbox = draw.textbbox((0, 0), value_str, font=metric_font)
            value_x = x + card_width - card_style['padding'] - value_bbox[2]
            value_y = y + card_height - card_style['padding'] - value_bbox[3] - 10
            
            # Ajouter un fond semi-transparent pour la valeur
            padding = 15
            draw.rounded_rectangle(
                [value_x - padding, value_y - padding // 2,
                 x + card_width - card_style['padding'] + padding, 
                 y + card_height - card_style['padding'] + padding // 2],
                radius=10,
                fill=color + (20,)  # Couleur avec transparence
            )
            
            # Dessiner la valeur
            draw.text(
                (value_x, value_y),
                value_str,
                fill=color,
                font=metric_font,
                stroke_width=1,
                stroke_fill=(255, 255, 255, 150)
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