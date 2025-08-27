# License MIT (https://opensource.org/licenses/MIT).
{
    "name": """Pos Credit""",
    "summary": """Pos Credit Management""",
    "category": "Point of Sale",
    "images": [],
    "version": "13.0.1.0.0",
    "application": False,
    "author": "Ingenioso SAS, Anderson Buitron",
    "support": "info@ingenioso.co",
    "website": "https://ingenioso.co",
    "license": "Other OSI approved licence",  # MIT
    "price": 0.00,
    "currency": "COP",
    "depends": ["point_of_sale"],
    "external_dependencies": {
        "python": [], 
        "bin": []},
    "data": [
        "views/pos_payment_method_views.xml",
        "views/assets.xml",
        "views/pos_order_view.xml",
    ],
    "demo": [],
    "qweb": [],
    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "uninstall_hook": None,
    "auto_install": False,
    "installable": True,
}
