from app_init import db


class RawMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.TEXT)
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return "{}: {}".format(self.id, self.__str__())


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.TEXT)
    quantity = db.Column(db.Integer(), nullable=False)
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return "{}: {}".format(self.id, self.__str__())


class ProductRawMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    raw_material_id = db.Column(
        db.Integer(), db.ForeignKey(RawMaterial.id), nullable=False
    )
    raw_material = db.relationship(RawMaterial, foreign_keys=[raw_material_id])
    product_id = db.Column(db.Integer(), db.ForeignKey(Product.id), nullable=False)
    product = db.relationship(Product, foreign_keys=[product_id])
    raw_material_quantity = db.Column(db.Integer(), nullable=False)
    description = db.Column(db.TEXT)
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return "{}: {}".format(self.id, self.__str__())


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    other_details = db.Column(db.TEXT)
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.name)

    def __repr__(self):
        return "{}: {}".format(self.id, self.__str__())


class ProductManufacturing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    to_location_id = db.Column(db.Integer(), db.ForeignKey(Location.id), nullable=False)
    product_id = db.Column(db.Integer(), db.ForeignKey(Product.id), nullable=False)
    description = db.Column(db.TEXT)
    to_location = db.relationship(Location, foreign_keys=[to_location_id])
    product = db.relationship(Product, foreign_keys=[product_id])
    batch_size = db.Column(
        db.Integer(), db.CheckConstraint("batch_size >= 0"), nullable=False
    )
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.id)


class ProductMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movement_date = db.Column(db.Date, server_default=db.func.now())
    from_location_id = db.Column(db.Integer(), db.ForeignKey(Location.id))
    to_location_id = db.Column(db.Integer(), db.ForeignKey(Location.id))
    product_id = db.Column(db.Integer(), db.ForeignKey(Product.id), nullable=False)
    description = db.Column(db.TEXT)
    from_location = db.relationship(Location, foreign_keys=[from_location_id])
    to_location = db.relationship(Location, foreign_keys=[to_location_id])
    product = db.relationship(Product, foreign_keys=[product_id])
    qty = db.Column(db.Integer(), db.CheckConstraint("qty >= 0"), nullable=False)
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.id)


class RawMaterialMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movement_date = db.Column(db.Date, server_default=db.func.now())
    from_location_id = db.Column(db.Integer(), db.ForeignKey(Location.id))
    to_location_id = db.Column(db.Integer(), db.ForeignKey(Location.id))
    raw_material_id = db.Column(
        db.Integer(), db.ForeignKey(RawMaterial.id), nullable=False
    )
    description = db.Column(db.TEXT)
    from_location = db.relationship(Location, foreign_keys=[from_location_id])
    to_location = db.relationship(Location, foreign_keys=[to_location_id])
    raw_material = db.relationship(RawMaterial, foreign_keys=[raw_material_id])
    qty = db.Column(db.Integer(), db.CheckConstraint("qty >= 0"), nullable=False)
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )

    def __str__(self):
        return "{}".format(self.id)


class ProductStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id))
    product_id = db.Column(db.Integer, db.ForeignKey(Product.id))
    available_stock = db.Column(
        db.Integer, db.CheckConstraint("available_stock>=0"), nullable=False
    )
    location = db.relationship(Location, foreign_keys=[location_id])
    product = db.relationship(Product, foreign_keys=[product_id])
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )
    db.UniqueConstraint(
        "location_id",
        "product_id",
        name="raw_material_stock_location_id_raw_material_id_uindex",
    )


class RawMaterialStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id))
    raw_material_id = db.Column(db.Integer, db.ForeignKey(RawMaterial.id))
    available_stock = db.Column(
        db.Integer, db.CheckConstraint("available_stock>=0"), nullable=False
    )
    location = db.relationship(Location, foreign_keys=[location_id])
    raw_material = db.relationship(RawMaterial, foreign_keys=[raw_material_id])
    time_created = db.Column(db.TIMESTAMP, server_default=db.func.now())
    time_updated = db.Column(
        db.TIMESTAMP, onupdate=db.func.now(), server_default=db.func.now()
    )
    db.UniqueConstraint(
        "location_id",
        "raw_material_id",
        name="raw_material_stock_location_id_raw_material_id_uindex",
    )
