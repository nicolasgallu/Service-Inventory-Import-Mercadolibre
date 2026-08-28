## NEW SCHEMA

who is my tenant? my tenant is ecommerce_account.
why? because a business can have multiples accounts from the same platform e.g mercadolibre.
so if the user is publishing the same product in different accounts, and the tenant is bussines
it would create a leak between tenants.


```sql
CREATE TABLE businesses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

Business can have multiples ecommerce_accounts.
e.g Giuliana (from Zamplin) can have maybe 2 different mercadolibre accounts.

```sql
CREATE TABLE ecommerce_accounts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    INDEX idx_business_id (business_id),
    UNIQUE KEY unique_business_platform (business_id, id)
);

```
Each ecommerce_accounts can hold 1 credential.
e.g Giuliana (from Zamplin) that has 2 different mercadolibre accounts, each one has just 1 credential.

```sql
CREATE TABLE credentials (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ecommerce_account_id INT NOT NULL,
    client_id VARCHAR(255) NULL,
    client_secret VARCHAR(255) NULL,
    code VARCHAR(255) NULL,
    redirect_url TEXT NULL,
    token TEXT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ecommerce_account_id) REFERENCES ecommerce_accounts(id) ON DELETE CASCADE
);
```


## SCHEMA INVENTORY
An ecommerce_accounts can have N products.
e.g Giuliana (from Zamplin) that has 2 different mercadolibre accounts, 
each one holding different or even same products.

```sql
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ecommerce_account_id INT NOT NULL,
    external_product_id VARCHAR(255) NOT NULL,
    code VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    brand VARCHAR(255),
    model VARCHAR(255),
    price DECIMAL(10,2) DEFAULT 0,
    cost DECIMAL(10,2) DEFAULT 0,
    stock INT DEFAULT 0,
    dimensions VARCHAR(50),
    drive_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ecommerce_account_id) REFERENCES ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY unique_account_external_id (ecommerce_account_id, external_product_id),
    INDEX idx_ecommerce_account_id (ecommerce_account_id),
    INDEX idx_code (code)
);
```

Each product can relate to N images.
```sql
CREATE TABLE product_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id)
);
```


## SCHEMA MERCADOLIBRE
```sql
CREATE TABLE product_listings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    ecommerce_account_id INT NOT NULL,
    meli_id VARCHAR(50),
    price INT,
    price_manually_changed BOOLEAN,
    price_updated_at TIMESTAMP,
    status VARCHAR(100),
    reason TEXT,
    remedy VARCHAR(255),
    permalink TEXT,    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_unique_product_account (product_id, ecommerce_account_id)
);
```


```sql
CREATE TABLE attributes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_listing_id INT NOT NULL,
    ecommerce_account_id INT NOT NULL,
    category_id VARCHAR(50) DEFAULT NULL,
    empty_gtin_reason_required tinyint(1) DEFAULT 0,
    empty_gtin_reason INT DEFAULT 17055160,
    buying_mode VARCHAR(50) DEFAULT 'buy_it_now',
    condition_type VARCHAR(50) DEFAULT 'new',
    currency_id VARCHAR(5) DEFAULT 'ARS',
    category_options JSON DEFAULT NULL,
    settings JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_listing_id) REFERENCES product_listings(id) ON DELETE CASCADE,
    FOREIGN KEY (ecommerce_account_id) REFERENCES ecommerce_accounts(id) ON DELETE CASCADE,
);
```

```sql
CREATE TABLE size_grid (
    id INT PRIMARY KEY AUTO_INCREMENT,
    attribute_id INT NOT NULL,
    ecommerce_account_id INT NOT NULL,
    size_grid_id BIGINT DEFAULT NULL,
    settings JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE,
    FOREIGN KEY (ecommerce_account_id) REFERENCES ecommerce_accounts(id) ON DELETE CASCADE,
);
```

```sql
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(255),
    ecommerce_account_id INT NOT NULL,
    data JSON DEFAULT NULL,
    pack_id VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ecommerce_account_id) REFERENCES ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY unique_account_order (ecommerce_account_id, order_id),
    INDEX idx_ecommerce_account_id (ecommerce_account_id)
);
```

## SCHEMA TIENDANUBE

