SELECT
  a.price,
  a.product_code,
  a.product_name,
  a.product_image_b_format_url,
  a.product_type_id,
  a.product_type_path,
  a.product_use_stock,
  a.product_sale_type_id,
  a.product_search_codes,
  a.product_type_node_left,
  a.product_change_cost_on_sales,
  a.stock,
  a.cost,
  a.product_name_meli,
  a.description,
  a.brand,
  a.meli_id,
  a.drive_url,
  a.status,
  a.reason,
  a.remedy,
  a.catalog_link,
  a.permalink,
  a.is_scrapped,
  a.price_mercadolibre,
  a.dimentions,
  a.model,
  a.price_tienda_nube,
  a.product_category,
  b.id AS attribute_id,
  b.item_id,
  b.seo_title,
  b.seo_description,
  b.barcode,
  b.video_url,
  b.tags,
  b.promotional_price,
  b.mpn,
  b.age_group,
  b.gender,
  c.*,
  d.id AS category_id,
  d.name AS category_name
FROM
  app_import.product_catalog_sync AS a
LEFT JOIN
  tienda_nube.attributes AS b
ON
  b.item_id = a.id
LEFT JOIN
  tienda_nube.product_status AS c
ON
  b.id = c.attribute_id
LEFT JOIN
  tienda_nube.categories AS d
ON
  d.name = a.product_type_path
WHERE
  a.id = 214101
LIMIT
  1