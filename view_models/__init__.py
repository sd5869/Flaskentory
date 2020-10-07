from app_init import db, engine
from db_models import *
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


class ModelViewProductManufacturing(ModelView):
    can_delete = False
    can_edit = False
    can_view_details = True
    can_export = True
    export_types = ["csv", "xls"]
    page_size = 20
    can_set_page_size = True
    column_exclude_list = ["time_created", "time_updated"]
    form_excluded_columns = ["time_created", "time_updated"]

    def on_model_change(self, form, model, is_created):
        conn = engine.connect()
        trans = conn.begin()
        query_needed_qty_of_raw_materials = db.text(
            "select raw_material_id,raw_material_quantity from product_raw_material where product_id= :product_id"
        )
        batch_size = form.data["batch_size"]
        query_for_actual_raw_materials = db.text(
            "select raw_material_id,available_stock from raw_material_stock where location_id=:location_id AND raw_material_id = ANY(:raw_material_ids)"
        )
        res = conn.execute(
            query_needed_qty_of_raw_materials, product_id=form.product.data.id
        )
        rows_needed_material_qty = res.fetchall()
        if len(rows_needed_material_qty) == 0:
            trans.rollback()
            conn.close()
            raise validators.ValidationError(
                "A product with no raw material cannot be manufactured."
            )
        res = conn.execute(
            query_for_actual_raw_materials,
            location_id=form.to_location.data.id,
            raw_material_ids=[x[0] for x in rows_needed_material_qty],
        )
        rows_actual_material_qty = res.fetchall()
        if len(rows_actual_material_qty) == 0:
            conn.close()
            raise validators.ValidationError("No Raw Material present in the location.")
        product_diff_map = {}
        for i in rows_actual_material_qty:
            product_diff_map[i[0]] = i[1]
        for i in rows_needed_material_qty:
            if i[0] not in product_diff_map.keys():
                conn.close()
                raise validators.ValidationError(
                    f"All Raw Materials not present at location: {form.to_location.data.name}, Missing: i[0]"
                )
            product_diff_map[i[0]] -= i[1] * batch_size
            select_st = db.text(
                "SELECT * FROM raw_material_stock WHERE location_id = :l AND raw_material_id = :p"
            )
            res = conn.execute(select_st, p=i[0], l=form.to_location.data.id)
            row_from = res.fetchone()
            if row_from:
                if row_from.available_stock < i[1] * batch_size:
                    conn.close()
                    raise validators.ValidationError(
                        f"Stock of Raw Material:{i[0]} Available is:{row_from.available_stock} Needed:{i[1] * batch_size}"
                    )
                update_query_for_raw_material = db.text(
                    "UPDATE raw_material_stock SET available_stock = raw_material_stock.available_stock - :qty WHERE id = :row_id"
                )
                conn.execute(
                    update_query_for_raw_material,
                    qty=i[1] * batch_size,
                    row_id=row_from.id,
                )
            else:
                conn.close()
                raise validators.ValidationError(
                    f"Zero Stock of Raw Material:{i[0]} Available, Needed:{i[1] * batch_size}"
                )

        query_for_qty_of_one_batch = db.text(
            "select quantity from product where id=:product_id"
        )
        res = conn.execute(query_for_qty_of_one_batch, product_id=form.product.data.id)
        qty_in_one_batch = res.fetchone()
        qty_in_one_batch = qty_in_one_batch[0] if qty_in_one_batch else 0
        manufactured_stock = batch_size * qty_in_one_batch
        select_st = db.text(
            "SELECT * FROM product_stock WHERE location_id = :l AND product_id = :p"
        )
        res = conn.execute(
            select_st, p=form.product.data.id, l=form.to_location.data.id
        )
        row_to = res.fetchone()
        if row_to:
            q = db.text(
                "UPDATE product_stock SET available_stock = product_stock.available_stock + :qty WHERE id = :id"
            )
            conn.execute(q, qty=manufactured_stock, id=row_to.id)
        else:
            q = db.text(
                "INSERT INTO product_stock (location_id, product_id, available_stock) VALUES (:l,:p,:qty)"
            )
            conn.execute(
                q,
                qty=manufactured_stock,
                l=form.to_location.data.id,
                p=form.product.data.id,
            )
        trans.commit()
        conn.close()


class ModelViewProductMovement(ModelView):
    can_delete = False
    can_edit = False
    can_view_details = True
    can_export = True
    export_types = ["csv"]
    page_size = 20
    can_set_page_size = True
    column_exclude_list = ["time_created", "time_updated"]
    form_excluded_columns = ["time_created", "time_updated"]

    def on_model_change(self, form, model, is_created):
        if is_created:
            conn = engine.connect()
            trans = conn.begin()
            if not form.from_location.data and not form.to_location.data:
                conn.close()
                raise validators.ValidationError(
                    'Both "From Location" and "To Location" cannot be empty'
                )
            if form.to_location.data:
                select_st = db.text(
                    "SELECT * FROM product_stock WHERE location_id = :l AND product_id = :p"
                )
                res = conn.execute(
                    select_st, p=form.product.data.id, l=form.to_location.data.id
                )
                row_to = res.fetchone()
                if row_to:
                    q = db.text(
                        "UPDATE product_stock SET available_stock = product_stock.available_stock + (1*:qty) WHERE id = :id"
                    )
                    conn.execute(q, qty=form.qty.data, id=row_to.id)
                else:
                    q = db.text(
                        "INSERT INTO product_stock (location_id, product_id, available_stock) VALUES (:l,:p,:qty)"
                    )
                    conn.execute(
                        q,
                        qty=form.qty.data,
                        l=form.to_location.data.id,
                        p=form.product.data.id,
                    )
            if form.from_location.data:
                select_st = db.text(
                    "SELECT * FROM product_stock WHERE location_id = :l AND product_id = :p"
                )
                res = conn.execute(
                    select_st, p=form.product.data.id, l=form.from_location.data.id
                )
                row_from = res.fetchone()
                if row_from:
                    if row_from.available_stock < form.qty.data:
                        raise validators.ValidationError(
                            'Stock of "'
                            + form.product.data.name
                            + '" available at "'
                            + form.from_location.data.name
                            + '" is '
                            + str(row_from.available_stock)
                        )
                    q = db.text(
                        "UPDATE product_stock SET available_stock = product_stock.available_stock + (1*:qty) WHERE id = :id"
                    )
                    conn.execute(q, qty=-form.qty.data, id=row_from.id)
                else:
                    raise validators.ValidationError(
                        'Zero Stock of "'
                        + form.product.data.name
                        + '" available at "'
                        + form.from_location.data.name
                        + '"'
                    )
            trans.commit()
            conn.close()
        else:
            conn = engine.connect()
            trans = conn.begin()
            select_st = db.select([RawMaterialMovement]).where(
                RawMaterialMovement.id == model.list_form_pk
            )
            res = conn.execute(select_st)
            row = res.fetchone()
            q = db.text(
                "UPDATE product_stock SET available_stock = product_stock.available_stock + (1*:qty) WHERE location_id = :l AND product_id = :p"
            )
            if row.from_location_id:
                select_st = db.text(
                    "SELECT * FROM product_stock WHERE location_id = :l AND product_id = :p"
                )
                res = conn.execute(select_st, p=row.product_id, l=row.from_location_id)
                row_from = res.fetchone()
                if row_from:
                    if (
                        row_from.available_stock + (int(row.qty) - int(form.qty.data))
                        < 0
                    ):
                        raise validators.ValidationError(
                            'Insufficient stock at "from_location". Stock available is: '
                            + str(row_from.available_stock)
                        )
                    conn.execute(
                        q,
                        qty=(int(row.qty) - int(form.qty.data)),
                        l=row.from_location_id,
                        p=row.product_id,
                    )
                else:
                    raise validators.ValidationError(
                        'Insufficient stock at "from_location". Stock available is: 0'
                    )
            if row.to_location_id:
                select_st = db.text(
                    "SELECT * FROM product_stock WHERE location_id = :l AND product_id = :p"
                )
                res = conn.execute(select_st, p=row.product_id, l=row.to_location_id)
                row_to = res.fetchone()
                if row_to:
                    if (row_to.available_stock + int(form.qty.data) - int(row.qty)) < 0:
                        raise validators.ValidationError(
                            'Insufficient stock at "to_location". Stock available is: '
                            + str(row_to.available_stock)
                        )
                    conn.execute(
                        q,
                        qty=(int(form.qty.data) - int(row.qty)),
                        l=row.to_location_id,
                        p=row.product_id,
                    )
                else:
                    if int(form.qty.data) - int(row.qty) < 0:
                        raise validators.ValidationError(
                            'Insufficient stock at "to_location". Stock available is: 0'
                        )
                    q = db.text(
                        "INSERT INTO product_stock (location_id, product_id, available_stock) VALUES (:l,:p,:qty)"
                    )
                    conn.execute(
                        q,
                        qty=(int(form.qty.data) - int(row.qty)),
                        l=row.to_location_id,
                        p=row.product_id,
                    )
            trans.commit()
            conn.close()


class ModelViewRawMaterial(ModelView):
    can_delete = False
    can_view_details = True
    can_export = True
    export_types = ["csv", "xls"]
    column_labels = dict(name="RawMaterial Name", description="RawMaterial Description")
    column_filters = ["id", "name", "description", "time_created", "time_updated"]
    page_size = 20
    column_exclude_list = ["time_created", "time_updated"]
    column_searchable_list = ["name", "description"]
    column_editable_list = [
        "name",
    ]
    form_excluded_columns = ["time_created", "time_updated"]
    form_args = {
        "name": {"label": "RawMaterial Name"},
        "description": {"label": "RawMaterial Description"},
    }
    form_widget_args = {"description": {"rows": 10, "style": "color: black"}}


class ModelViewProductRawMaterial(ModelView):
    can_delete = False
    can_view_details = True
    can_export = True
    export_types = ["csv", "xls"]
    column_filters = ["id", "name", "time_created", "time_updated"]
    page_size = 20
    column_exclude_list = ["time_created", "time_updated"]
    column_searchable_list = ["name"]
    column_editable_list = [
        "name",
    ]
    form_excluded_columns = ["time_created", "time_updated"]
    form_args = {
        "name": {"label": "Mapping Name"},
    }

    def on_model_change(self, form, model, is_created):
        if is_created:
            conn = engine.connect()
            trans = conn.begin()
            if form.product:
                q = db.text(
                    "select sum(raw_material_quantity) as total from product_raw_material where product_id = :r"
                )
                res = conn.execute(q, r=form.product.data.id)
                row_to = res.fetchone()[0] or 0
                quantity = row_to + form.raw_material_quantity.data
                q = db.text("UPDATE product SET quantity = :quantity WHERE id = :id")
                conn.execute(q, quantity=quantity, id=form.product.data.id)
            trans.commit()
            conn.close()
        else:
            conn = engine.connect()
            trans = conn.begin()
            if form.product:
                q = db.text(
                    "select sum(raw_material_quantity) as total from product_raw_material where product_id = :r"
                )
                res = conn.execute(q, r=form.product.data.id)
                row_to = res.fetchone()[0] or 0
                if row_to:
                    q = db.text(
                        "select sum(raw_material_quantity) as total from product_raw_material where product_id = :rid and raw_material_id = :pid"
                    )
                    res = conn.execute(
                        q, pid=form.raw_material.data.id, rid=form.product.data.id
                    )
                    old_quantity = res.fetchone()[0]
                    assert old_quantity is not None
                    quantity = row_to + form.raw_material_quantity.data - old_quantity
                    q = db.text(
                        "UPDATE product SET quantity = :quantity WHERE id = :id"
                    )
                    conn.execute(q, quantity=quantity, id=form.product.data.id)
            trans.commit()
            conn.close()


class ModelViewLocation(ModelView):
    can_delete = False
    can_view_details = True
    can_export = True
    export_types = ["csv", "xls"]
    column_labels = dict(name="Location Name", other_details="Other Details")
    column_filters = ["id", "name", "other_details", "time_created", "time_updated"]
    page_size = 20
    column_exclude_list = ["time_created", "time_updated"]
    column_searchable_list = ["name", "other_details"]
    column_editable_list = [
        "name",
    ]
    form_excluded_columns = ["time_created", "time_updated"]
    form_args = {
        "name": {"label": "Location Name"},
        "other_details": {"label": "Other Details"},
    }
    form_widget_args = {"other_details": {"rows": 10, "style": "color: black"}}


class ModelViewProduct(ModelView):
    can_delete = False
    can_view_details = True
    can_export = True
    export_types = ["csv", "xls"]
    column_filters = ["id", "name", "time_created", "time_updated"]
    page_size = 20
    column_exclude_list = ["time_created", "time_updated"]
    column_searchable_list = ["name"]
    column_editable_list = [
        "name",
    ]
    form_excluded_columns = ["time_created", "time_updated"]


class ModelViewRawMaterialMovement(ModelView):
    can_delete = False
    can_edit = False
    can_view_details = True
    can_export = True
    export_types = ["csv"]
    page_size = 20
    can_set_page_size = True
    column_exclude_list = ["time_created", "time_updated"]
    column_editable_list = ["qty"]
    form_excluded_columns = ["time_created", "time_updated"]

    def on_model_change(self, form, model, is_created):
        if is_created:
            conn = engine.connect()
            trans = conn.begin()
            if not form.from_location.data and not form.to_location.data:
                conn.close()
                raise validators.ValidationError(
                    'Both "From Location" and "To Location" cannot be empty'
                )
            if form.to_location.data:
                select_st = db.text(
                    "SELECT * FROM raw_material_stock WHERE location_id = :l AND raw_material_id = :p"
                )
                res = conn.execute(
                    select_st, p=form.raw_material.data.id, l=form.to_location.data.id
                )
                row_to = res.fetchone()
                if row_to:
                    q = db.text(
                        "UPDATE raw_material_stock SET available_stock = raw_material_stock.available_stock + (1*:qty) WHERE id = :id"
                    )
                    conn.execute(q, qty=form.qty.data, id=row_to.id)
                else:
                    q = db.text(
                        "INSERT INTO raw_material_stock (location_id, raw_material_id, available_stock) VALUES (:l,:p,:qty)"
                    )
                    conn.execute(
                        q,
                        qty=form.qty.data,
                        l=form.to_location.data.id,
                        p=form.raw_material.data.id,
                    )
            if form.from_location.data:
                select_st = db.text(
                    "SELECT * FROM raw_material_stock WHERE location_id = :l AND raw_material_id = :p"
                )
                res = conn.execute(
                    select_st, p=form.raw_material.data.id, l=form.from_location.data.id
                )
                row_from = res.fetchone()
                if row_from:
                    if row_from.available_stock < form.qty.data:
                        raise validators.ValidationError(
                            'Stock of "'
                            + form.raw_material.data.name
                            + '" available at "'
                            + form.from_location.data.name
                            + '" is '
                            + str(row_from.available_stock)
                        )
                    q = db.text(
                        "UPDATE raw_material_stock SET available_stock = raw_material_stock.available_stock + (1*:qty) WHERE id = :id"
                    )
                    conn.execute(q, qty=-form.qty.data, id=row_from.id)
                else:
                    raise validators.ValidationError(
                        'Zero Stock of "'
                        + form.raw_material.data.name
                        + '" available at "'
                        + form.from_location.data.name
                        + '"'
                    )
            trans.commit()
            conn.close()
        else:
            conn = engine.connect()
            trans = conn.begin()
            select_st = db.select([RawMaterialMovement]).where(
                RawMaterialMovement.id == model.list_form_pk
            )
            res = conn.execute(select_st)
            row = res.fetchone()
            q = db.text(
                "UPDATE raw_material_stock SET available_stock = raw_material_stock.available_stock + (1*:qty) WHERE location_id = :l AND raw_material_id = :p"
            )
            if row.from_location_id:
                select_st = db.text(
                    "SELECT * FROM raw_material_stock WHERE location_id = :l AND raw_material_id = :p"
                )
                res = conn.execute(
                    select_st, p=row.raw_material_id, l=row.from_location_id
                )
                row_from = res.fetchone()
                if row_from:
                    if (
                        row_from.available_stock + (int(row.qty) - int(form.qty.data))
                        < 0
                    ):
                        raise validators.ValidationError(
                            'Insufficient stock at "from_location". Stock available is: '
                            + str(row_from.available_stock)
                        )
                    conn.execute(
                        q,
                        qty=(int(row.qty) - int(form.qty.data)),
                        l=row.from_location_id,
                        p=row.raw_material_id,
                    )
                else:
                    raise validators.ValidationError(
                        'Insufficient stock at "from_location". Stock available is: 0'
                    )
            if row.to_location_id:
                select_st = db.text(
                    "SELECT * FROM raw_material_stock WHERE location_id = :l AND raw_material_id = :p"
                )
                res = conn.execute(
                    select_st, p=row.raw_material_id, l=row.to_location_id
                )
                row_to = res.fetchone()
                if row_to:
                    if (row_to.available_stock + int(form.qty.data) - int(row.qty)) < 0:
                        raise validators.ValidationError(
                            'Insufficient stock at "to_location". Stock available is: '
                            + str(row_to.available_stock)
                        )
                    conn.execute(
                        q,
                        qty=(int(form.qty.data) - int(row.qty)),
                        l=row.to_location_id,
                        p=row.raw_material_id,
                    )
                else:
                    if int(form.qty.data) - int(row.qty) < 0:
                        raise validators.ValidationError(
                            'Insufficient stock at "to_location". Stock available is: 0'
                        )
                    q = db.text(
                        "INSERT INTO raw_material_stock (location_id, raw_material_id, available_stock) VALUES (:l,:p,:qty)"
                    )
                    conn.execute(
                        q,
                        qty=(int(form.qty.data) - int(row.qty)),
                        l=row.to_location_id,
                        p=row.raw_material_id,
                    )
            trans.commit()
            conn.close()


class ModelViewProductStock(ModelView):
    can_delete = False
    can_edit = False
    can_create = False
    column_exclude_list = ["time_created", "time_updated"]
    column_sortable_list = ("available_stock",)
    column_default_sort = "product_id"
    page_size = 35
    can_export = True
    export_types = ["csv", "xlsx"]


class ModelViewRawMaterialStock(ModelView):
    can_delete = False
    can_edit = False
    can_create = False
    column_exclude_list = ["time_created", "time_updated"]
    column_sortable_list = ("available_stock",)
    column_default_sort = "raw_material_id"
    page_size = 35
    can_export = True
    export_types = ["csv", "xlsx"]


def register(app):
    admin = Admin(
        app,
        name="Inventory Management",
        template_mode="bootstrap3",
        url="/",
        base_template="admin/custombase.html",
    )
    admin.add_view(
        ModelViewRawMaterialMovement(
            RawMaterialMovement,
            db.session,
            name="Raw Material Movement",
            category="Movement",
        )
    )
    admin.add_view(
        ModelViewProductMovement(
            ProductMovement, db.session, name="Product Movement", category="Movement",
        )
    )
    admin.add_view(
        ModelViewRawMaterialStock(
            RawMaterialStock, db.session, name="Raw Material Stock", category="Stock"
        )
    )
    admin.add_view(
        ModelViewProductStock(
            ProductStock, db.session, name="Product Stock", category="Stock"
        )
    )
    admin.add_view(
        ModelViewProductManufacturing(
            ProductManufacturing, db.session, name="Product Manufacturing"
        )
    )
    admin.add_view(ModelViewRawMaterial(RawMaterial, db.session, category="Master"))
    admin.add_view(ModelViewLocation(Location, db.session, category="Master"))
    admin.add_view(ModelViewProduct(Product, db.session, category="Master"))
    admin.add_view(
        ModelViewProductRawMaterial(ProductRawMaterial, db.session, category="Master")
    )
