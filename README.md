# 🚀 Mercado Libre Publication & Notification Service

Este servicio de microsegmento actúa como el **Orquestador de Publicaciones** entre nuestro inventario central y el ecosistema de **Mercado Libre**. Es un servicio RESTful diseñado para procesar eventos de catálogo en tiempo real, enriquecerlos con Inteligencia Artificial y asegurar la consistencia visual y técnica de cada producto.

## 📝 ¿Qué hace este servicio?

El servicio opera como un receptor de eventos (Webhooks) que automatiza el ciclo de vida de una publicación a través de cuatro capas de procesamiento:

### 1. Recepción y Validación de Eventos

El servicio expone un endpoint seguro que recibe instrucciones de **Publicación**, **Actualización** o **Pausa**.

* **Seguridad:** Implementa validación mediante secretos dinámicos gestionados en **Google Cloud Secret Manager**.
* **Eficiencia:** Utiliza un modelo de *threading* (hilos) para responder instantáneamente al emisor, procesando las tareas pesadas en segundo plano.

### 2. Enriquecimiento Inteligente con IA

Para garantizar publicaciones de alta calidad y evitar rechazos por falta de información, el servicio integra **DeepSeek AI**:

* **Auto-completado:** Si el producto carece de marca o descripción, la IA las genera basándose en el nombre comercial.
* **Asistente de Errores:** Si Mercado Libre rechaza una publicación por errores técnicos, un agente de IA analiza el error, corrige el formulario (Payload) y reintenta la publicación automáticamente.

### 3. Sincronización de Activos Digitales

El servicio gestiona la identidad visual de los productos conectando dos nubes:

* **Extracción:** Localiza las fotos originales en **Google Drive**.
* **Distribución:** Procesa y transfiere las imágenes a un **Bucket de Google Cloud Storage**, generando URLs públicas optimizadas para que Mercado Libre las procese sin latencia.

### 4. Persistencia y Trazabilidad

Toda acción realizada (creación de un ID de Mercado Libre, actualización de stock o cambios de descripción) se persiste en una base de datos **MySQL (Cloud SQL)**, manteniendo un historial sincronizado entre el mundo físico (inventario) y el mundo digital (e-commerce).

---

## 🏗️ Stack Tecnológico

* **Framework:** Flask (Python) con Blueprints para escalabilidad.
* **IA:** DeepSeek API (Modelos de chat y completado).
* **Nube (GCP):** Cloud Run, Secret Manager, Cloud SQL, Cloud Storage.
* **Integraciones:** Mercado Libre API (OAuth 2.0), Google Drive API, Whapi (WhatsApp).
* **Base de Datos:** SQLAlchemy con Google Cloud SQL Connector.

---

## 🚦 Flujo Lógico de Notificación

1. **Webhook Inbound:** Llega una notificación con un `item_id`.
2. **Data Fetch:** Se recupera la información técnica desde la base de datos.
3. **Media Processing:** Se descargan y publican las fotos desde Drive a GCS.
4. **AI Validation:** Se verifica que los campos obligatorios existan; si no, la IA los genera.
5. **Meli Sync:** Se impacta la API de Mercado Libre.
6. **Error Handling:** Si algo falla, se dispara una alerta de alta prioridad vía **WhatsApp**.

---

## 🛠️ Configuración Rápida (Menciones de Seguridad)

Para que el servicio esté operativo, requiere acceso a:

* **Secret Manager:** Contenedor de tokens de Mercado Libre y API Keys de IA.
* **Service Account:** Con permisos de lectura en Drive y escritura en Cloud Storage/SQL.
* **Variables de Entorno:** Configuración de moneda, condiciones de venta y tiempos de garantía.