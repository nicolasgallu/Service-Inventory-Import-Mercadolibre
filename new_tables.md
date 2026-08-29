who is my tenant? my tenant is ecommerce_account.
why? because a business can have multiples accounts from the same platform e.g mercadolibre.
so if the user is publishing the same product in different accounts, and the tenant is bussines
it would create a leak between tenants.

-- ============================================================
-- SCHEMAS
-- ============================================================

-- DROP SCHEMA platform_accounts;
-- DROP SCHEMA inventory;
-- DROP SCHEMA mercadolibre;

```sql
CREATE SCHEMA IF NOT EXISTS platform_accounts;
CREATE SCHEMA IF NOT EXISTS inventory;
CREATE SCHEMA IF NOT EXISTS mercadolibre;
```

-- ============================================================
-- SCHEMA: platform_accounts
-- ============================================================

```sql
CREATE TABLE platform_accounts.businesses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

```sql
CREATE TABLE platform_accounts.ecommerce_accounts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL,
    platform VARCHAR(100) NOT NULL, 
    external_account_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES platform_accounts.businesses(id) ON DELETE CASCADE,
    UNIQUE KEY uq_account_platform_external (platform, external_account_id),
    INDEX idx_business_id (business_id)
);
```
```sql
CREATE TABLE platform_accounts.credentials (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ecommerce_account_id INT NOT NULL,
    client_id VARCHAR(255) NULL,
    client_secret VARCHAR(255) NULL,
    access_token TEXT NULL,
    refresh_token TEXT NULL,
    code VARCHAR(255) NULL,
    redirect_url TEXT NULL,
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ecommerce_account_id) REFERENCES platform_accounts.ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY uq_credentials_account (ecommerce_account_id)
);
```

-- ============================================================
-- SCHEMA: inventory
-- ============================================================
#para llevar estos cambios a inventario,
la logica de lectura de product code de Emi
tiene que viajar a algun lado, capaz sql puro.
```sql
CREATE TABLE inventory.products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ecommerce_account_id INT NOT NULL,
    internal_code VARCHAR(255),
    sku VARCHAR(255),
    gtin VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    name_edited VARCHAR(255) NULL,
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
    FOREIGN KEY (ecommerce_account_id) REFERENCES platform_accounts.ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY uq_account_internal_code (ecommerce_account_id, internal_code),
    INDEX idx_ecommerce_account_id (ecommerce_account_id)
);
```

```sql
CREATE TABLE inventory.product_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id)
);
```

```sql
CREATE TABLE inventory.product_variations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    sku VARCHAR(255) NULL,
    gtin VARCHAR(255) NULL,
    price DECIMAL(10,2) NULL,
    cost DECIMAL(10,2) NULL,
    stock INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES inventory.products(id) ON DELETE CASCADE,
    INDEX idx_product_id (product_id)
);
```



-- ============================================================
-- SCHEMA: mercadolibre
-- ============================================================

```sql
CREATE TABLE mercadolibre.product_listings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    ecommerce_account_id INT NOT NULL,
    meli_id VARCHAR(50) NULL,
    price INT NULL,
    price_manually_changed BOOLEAN NULL,
    price_updated_at TIMESTAMP NULL,
    status VARCHAR(100) NULL,
    reason TEXT NULL,
    remedy VARCHAR(255) NULL,
    permalink TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES inventory.products(id) ON DELETE CASCADE,
    FOREIGN KEY (ecommerce_account_id) REFERENCES platform_accounts.ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY uq_listing_product (product_id),
    UNIQUE KEY uq_listing_meli_id (meli_id)  
);
```

```sql
CREATE TABLE mercadolibre.variation_listings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_variation_id INT NOT NULL,
    product_listing_id INT NOT NULL,
    external_variation_id VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_variation_id) REFERENCES inventory.product_variations(id) ON DELETE CASCADE,
    FOREIGN KEY (product_listing_id) REFERENCES mercadolibre.product_listings(id) ON DELETE CASCADE,
    UNIQUE KEY uq_product_variation_listing (product_variation_id, product_listing_id),
    INDEX idx_product_listing_id (product_listing_id),
    INDEX idx_product_variation_id (product_variation_id)
);
```


```sql
CREATE TABLE mercadolibre.attributes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_listing_id INT NOT NULL,
    category_id VARCHAR(50) DEFAULT NULL,
    empty_gtin_reason_required TINYINT(1) DEFAULT 0,
    empty_gtin_reason INT DEFAULT 17055160,
    buying_mode VARCHAR(50) DEFAULT 'buy_it_now',
    condition_type VARCHAR(50) DEFAULT 'new',
    currency_id VARCHAR(5) DEFAULT 'ARS',
    category_options JSON DEFAULT NULL,
    settings JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_listing_id) REFERENCES product_listings(id) ON DELETE CASCADE,
    UNIQUE KEY uq_attributes_listing (product_listing_id)
);
```

```sql
CREATE TABLE mercadolibre.size_grid (
    id INT PRIMARY KEY AUTO_INCREMENT,
    attribute_id INT NOT NULL,
    size_grid_id BIGINT DEFAULT NULL,
    settings JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE,
    UNIQUE KEY uq_size_grid_attribute (attribute_id)
);
```

```sql
CREATE TABLE mercadolibre.orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(255) NOT NULL,
    ecommerce_account_id INT NOT NULL,
    status VARCHAR(50) NULL,
    data JSON DEFAULT NULL,
    pack_id VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ecommerce_account_id) REFERENCES platform_accounts.ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY uq_order_account (ecommerce_account_id, order_id)
);
```

-- replaces the in-memory `memory` set: durable claim, works across N instances
```sql
CREATE TABLE platform_accounts.events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ecommerce_account_id INT NOT NULL,
    source VARCHAR(32) NOT NULL,     
    event_type VARCHAR(64) NOT NULL,  
    external_id VARCHAR(255) NOT NULL,
    payload JSON NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',  
    attempts INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ecommerce_account_id) REFERENCES platform_accounts.ecommerce_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY uq_event_dedup (ecommerce_account_id, source, event_type, external_id),
    INDEX idx_event_status_updated (status, updated_at)
);
```

```sql
-- Bitcram double-post guard: one row per (order, product, direction)
CREATE TABLE inventory.stock_movements (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ecommerce_account_id INT NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    product_id INT NOT NULL,
    direction VARCHAR(8) NOT NULL,  
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NULL,
    provider_doc_id VARCHAR(255) NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'attempting', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ecommerce_account_id) REFERENCES platform_accounts.ecommerce_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uq_stock_dedup (ecommerce_account_id, order_id, product_id, direction)
);
```


