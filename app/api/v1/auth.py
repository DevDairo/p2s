from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)

from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login():
    """
    Inicio de sesión.

    Body JSON:
        { "email": "...", "password": "..." }

    Respuesta 200:
        { "access_token", "refresh_token", "user": { id, email, role } }
    """
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos."}), 400

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Credenciales inválidas."}), 401

    access_token  = create_access_token(identity=str(user.id),
                                        additional_claims={"role": user.role})
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict(),
    })


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """Renueva el access token usando el refresh token."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Usuario no válido."}), 401

    access_token = create_access_token(identity=str(user.id),
                                       additional_claims={"role": user.role})
    return jsonify({"access_token": access_token})


@auth_bp.get("/me")
@jwt_required()
def me():
    """Devuelve los datos del usuario autenticado."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado."}), 404
    return jsonify({"user": user.to_dict()})
