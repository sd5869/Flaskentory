from app_init import app
from view_models import register

if __name__ == "__main__":
    # create demo data if demo flag set
    # if app.config["demo"]:
    #     db.drop_all()
    #     db.create_all()
    debug = not (app.config["is_production"])
    register(app)
    app.run(debug=debug)
