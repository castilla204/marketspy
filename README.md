# MarketSpy — Ingeniería Inversa de API Oculta

> Primer scraper documentado públicamente para MilAnuncios. Sin API pública: ingeniería inversa pura del protocolo interno.

![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white)

---

## ¿Qué es MarketSpy?

MilAnuncios no tiene API pública. Este proyecto nació de semanas de análisis del tráfico de red para descubrir cómo funciona internamente la plataforma: encabezados, tokens de sesión, parámetros ocultos y patrones de petición.

El resultado es una API REST limpia expuesta con FastAPI, Dockerizada y orquestada con Kubernetes; lista para escalar horizontalmente.

Sirvió de base tecnológica para el proyecto [DealRadar](https://github.com/castilla204/GRUP).

---

## Stack

| Herramienta | Uso |
|---|---|
| Python | Ingeniería inversa y lógica de scraping |
| FastAPI | API REST para exponer los datos |
| Docker | Contenerización |
| Kubernetes | Orquestación y escalado horizontal |

---

## Instalación

```bash
git clone https://github.com/castilla204/MilAnunciosScrapperPy
cd MilAnunciosScrapperPy

# Configurar variables de entorno
cp .env.example .env

# Docker
docker build -t marketspy-api .
docker run -p 8000:8000 marketspy-api
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/anuncios` | Busca anuncios por palabra clave y parámetros |
| GET | `/anuncios/{id}` | Detalle completo de un anuncio |

---

## Autor

**Diego Castilla Abella** - [github.com/castilla204](https://github.com/castilla204)
