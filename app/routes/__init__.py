def register_blueprints(app):
    from app.routes.ai_factory import bp as ai_factory_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.facilities import bp as facilities_bp
    from app.routes.feedback import bp as feedback_bp
    from app.routes.incidents import bp as incidents_bp
    from app.routes.maintenance import bp as maintenance_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.reservations import bp as reservations_bp
    from app.routes.staff import bp as staff_bp
    from app.routes.tickets import bp as tickets_bp
    from app.routes.visitors import bp as visitors_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(visitors_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(facilities_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ai_factory_bp)

