# Odoo Point of Sale Credit Addon

## Project Overview

This project is an Odoo addon that extends the Point of Sale (POS) application to include credit management functionalities. It allows customers to make purchases on credit, and provides the necessary backend configurations to manage these payments.

**Key Technologies:**

*   **Backend:** Python, Odoo 13.0 Framework
*   **Frontend:** XML (for views), JavaScript (for POS frontend logic)

**Architecture:**

The addon follows the standard Odoo module structure:

*   `models/`: Contains the Python models that define the data structure and business logic.
*   `views/`: Contains the XML files that define the user interface.
*   `static/`: Contains static assets like CSS and JavaScript.
*   `__manifest__.py`: The module descriptor file.

## Functionality

The core functionality of this addon revolves around a new payment method type called "Customer Account".

*   **`pos.payment.method` model extension:**
    *   A new `type` selection field is added with the option `pay_later` which represents a "Customer Account".
    *   The `split_transactions` boolean field allows for identifying customers for each transaction.
*   **`pos.order` model extension:**
    *   The `pos.order` model is inherited to handle the logic for orders paid with credit.
*   **UI Modifications:**
    *   The POS payment method form and tree views are modified to incorporate the new fields and options.

## Key Files

*   **`__manifest__.py`**: Defines the module's metadata, dependencies, and data files.
*   **`models/pos_payment_method.py`**: Extends the `pos.payment.method` model to add the "Customer Account" functionality.
*   **`models/pos_order.py`**: Extends the `pos.order` model to handle orders made with the new payment method.
*   **`views/pos_payment_method_views.xml`**: Modifies the views for POS payment methods to expose the new configuration options.
*   **`views/pos_order_view.xml`**: Modifies the POS order view.
*   **`static/src/js/screens.js`**: Contains the frontend logic for the POS credit functionality.


## Development Conventions

The code follows the standard Odoo development conventions.

*   **Models:** Python classes inheriting from `odoo.models.Model`.
*   **Views:** XML files defining the structure of the UI.
*   **PEP 8:** Python code should adhere to PEP 8 style guidelines.
