from werkzeug.exceptions import HTTPException
from flask import Flask, Response, jsonify, request
import badge_generator.v1_badge as v1_badge
import badge_generator.v2_badge_en as v2_badge_en
import badge_generator.v2_badge_ko as v2_badge_ko
import logging

from models.user_stats import UserStats
from repositories.user_stats_repository import UserStatsRepositoryError
from services.user_stats_service import UserStatsService


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)
app = Flask(__name__)
user_stats_service = UserStatsService()


def get_user_stats(username: str) -> UserStats:
    try:
        return user_stats_service.get_user_stats(username)
    except UserStatsRepositoryError as e:
        logger.error(f"Repository error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    return UserStats.empty(username)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    if isinstance(e, HTTPException):
        message = e.description if e.description else "Error"
        return jsonify(error=message), e.code
    return jsonify(error="Internal Server Error"), 500
        
@app.route('/<username>')
def show_v1_badge(username):
    user_data = get_user_stats(username)
    image = v1_badge.create_svg(user_data)
    response = Response(image,mimetype='image/svg+xml')
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

@app.route('/user/<username>')
def show_v1_badge_(username):
    user_data = get_user_stats(username)
    image = v1_badge.create_svg(user_data)
    response = Response(image,mimetype='image/svg+xml')
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

@app.route('/v2/en/<username>')
def show_v2_badge_en(username):
    user_data = get_user_stats(username)
    image = v2_badge_en.create_svg(user_data)
    response = Response(image,mimetype='image/svg+xml')
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

@app.route('/v2/ko/<username>')
def show_v2_badge_ko(username):
    user_data = get_user_stats(username)
    image = v2_badge_ko.create_svg(user_data)
    response = Response(image,mimetype='image/svg+xml')
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

if __name__ == '__main__':
    app.run(debug=True)
