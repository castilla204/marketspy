import asyncio
import nodriver as uc
from nodriver.cdp import fetch
import orjson
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import urllib.request
import os
import traceback

# Crear la aplicación FastAPI
app = FastAPI()

# Configuración del proxy - ahora usando variables de entorno para mayor seguridad
# Las credenciales deben configurarse mediante variables de entorno en producción
PROXYHOST = os.getenv("PROXY_HOST", "es.smartproxy.com")
PROXYPORT = os.getenv("PROXY_PORT", "10001")
PROXYUSERNAME = os.getenv("PROXY_USERNAME", "")
PROXYPASSWORD = os.getenv("PROXY_PASSWORD", "")
PROXY = f"https://{PROXYHOST}:{PROXYPORT}"

async def setup_proxy(username, password, tab):
    """
    Configura la autenticación del proxy para el navegador.
    
    Args:
        username: Usuario del proxy
        password: Contraseña del proxy
        tab: Pestaña del navegador donde configurar el proxy
    """
    async def auth_challenge_handler(event: fetch.AuthRequired):
        await tab.send(
            fetch.continue_with_auth(
                request_id=event.request_id,
                auth_challenge_response=fetch.AuthChallengeResponse(
                    response="ProvideCredentials",
                    username=username,
                    password=password,
                ),
            )
        )

    async def req_paused(event: fetch.RequestPaused):
        await tab.send(fetch.continue_request(request_id=event.request_id))

    tab.add_handler(
        fetch.RequestPaused, lambda event: asyncio.create_task(req_paused(event))
    )
    tab.add_handler(
        fetch.AuthRequired,
        lambda event: asyncio.create_task(auth_challenge_handler(event)),
    )

    await tab.send(fetch.enable(handle_auth_requests=True))

# Modelo para los parámetros de búsqueda
class SearchParams(BaseModel):
    searchTerms: str
    category: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    minPrice: Optional[int] = None
    maxPrice: Optional[int] = None
    shippingAviable: Optional[bool] = False
    isMultipage: Optional[bool] = False
    pagesorpage: Optional[int] = 1
    isProgrammed: Optional[bool] = False
    useProxy: Optional[bool] = False

def clean_and_fix_json(json_string: str) -> str:
    """
    Limpia y corrige una cadena JSON que puede contener caracteres de escape incorrectos.
    
    Args:
        json_string: Cadena JSON a limpiar
        
    Returns:
        Cadena JSON limpia y corregida
    """
    try:
        cleaned = json_string.replace('\\\\', '\\')
        cleaned = cleaned.replace('\\\"', '"')
        cleaned = cleaned.replace('\\n', ' ')
        cleaned = cleaned.replace('\\r', ' ')
        cleaned = cleaned.replace('\\t', ' ')
        def escape_internal_quotes(match):
            content = match.group(1)
            escaped = content.replace('"', '\\"')
            return f'"{escaped}"'
        cleaned = re.sub(r'"([^"]*?)"', escape_internal_quotes, cleaned)
        cleaned = re.sub(r'\\u([0-9A-Fa-f]{4})',
                        lambda m: chr(int(m.group(1), 16)),
                        cleaned)
        cleaned = cleaned.replace('€', '€').replace('\\u20AC', '€').replace('', '')
        return cleaned
    except Exception as e:
        print(f"Error limpiando JSON: {str(e)}")
        return json_string

async def fetch_ads(params: SearchParams):
    """
    Obtiene anuncios de MilAnuncios según los parámetros de búsqueda proporcionados.
    
    Args:
        params: Parámetros de búsqueda (términos, categoría, precio, etc.)
        
    Returns:
        Response con los anuncios en formato JSON
    """
    browser = None
    try:
        # Configurar nodriver con opciones adicionales
        browser_config = {
            "browser_executable_path": "/usr/bin/chromium",
            "headless": True,
            "no_sandbox": True,
            "disable_dev_shm_usage": True,
            "disable_gpu": True,
            "disable_extensions": True,
            "disable_software_rasterizer": True,
            "disable_setuid_sandbox": True,
            "remote_debugging_port": 9222
        }
        
        print(f"Iniciando navegador con configuración: {browser_config}")
        
        # Verificar si el binario de Chromium existe
        if not os.path.exists(browser_config["browser_executable_path"]):
            raise HTTPException(status_code=500, detail="El binario de Chromium no se encuentra en /usr/bin/chromium")
        
        # Verificar permisos del binario
        import stat
        st = os.stat(browser_config["browser_executable_path"])
        print(f"Permisos del binario de Chromium: {oct(st.st_mode & 0o777)}")
        
        # Si el parámetro useProxy es True, se configura el proxy
        if params.useProxy:
            if not PROXYUSERNAME or not PROXYPASSWORD:
                raise HTTPException(
                    status_code=500, 
                    detail="Las credenciales del proxy no están configuradas. Configure PROXY_USERNAME y PROXY_PASSWORD como variables de entorno."
                )
            browser_config["proxy_server"] = f"https://{PROXYHOST}:{PROXYPORT}"
            print("Configurando proxy...")
            browser = await uc.start(**browser_config)
        else:
            print("Iniciando navegador sin proxy...")
            try:
                browser = await uc.start(**browser_config)
            except Exception as e:
                print(f"Error al iniciar navegador: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Error al iniciar navegador: {str(e)}")
        
        if browser is None:
            print("Error: uc.start() devolvió None")
            raise HTTPException(status_code=500, detail="No se pudo inicializar el navegador: uc.start() devolvió None")
        
        print("Navegador iniciado correctamente")
        
        main_tab = await browser.get("about:blank")
        if params.useProxy:
            await setup_proxy(PROXYUSERNAME, PROXYPASSWORD, main_tab)
        
        # Verificar la conexión del proxy
        ipPage = await browser.get("https://www.myexternalip.com/raw")
        await asyncio.sleep(2)
        ip = await ipPage.evaluate("document.body.textContent.trim()")
        print(f">= Using IP Address: {ip}")

        # Construir la URL base según la categoría
        base_url = "https://www.milanuncios.com"
        url = f"{base_url}/{params.category}/?s={params.searchTerms}"
        if params.minPrice is not None:
            url += f"&precio_min={params.minPrice}"
        if params.maxPrice is not None:
            url += f"&precio_max={params.maxPrice}"
        if params.latitude:
            url += f"&latitude={params.latitude}"
        if params.longitude:
            url += f"&longitude={params.longitude}"
        if params.shippingAviable:
            url += f"&shipping=1"
        
        print(f"Navegando a URL: {url}")
        page = await browser.get(url)
        all_ads = []

        if params.pagesorpage > 1:
            for page_num in range(1, params.pagesorpage + 1):
                page_url = f"{url}&pagina={page_num}"
                print(f"Navegando a página {page_num}: {page_url}")
                await page.goto(page_url)
                await page.find('window.__INITIAL_PROPS__ = JSON.parse', timeout=20)
                await page.scroll_down(150)
                
                script = """
                (() => {
                    const scripts = document.querySelectorAll('script');
                    let initialProps = null;
                    scripts.forEach(script => {
                        if (script.textContent.includes('window.__INITIAL_PROPS__')) {
                            try {
                                const match = script.textContent.match(/window\.__INITIAL_PROPS__ = JSON\.parse\("(.+?)"\);/);
                                if (match && match[1]) {
                                    initialProps = match[1];
                                }
                            } catch (e) {
                                console.error('Error parsing script:', e);
                            }
                        }
                    });
                    return initialProps;
                })();
                """
                initial_props_script = await page.evaluate(script)

                if initial_props_script:
                    cleaned_json = clean_and_fix_json(initial_props_script)
                    try:
                        data = json.loads(cleaned_json)
                        ads = data.get("adListPagination", {}).get("relatedAdList", {}).get("ads", [])
                        if not ads:
                            ads = data.get("adListPagination", {}).get("adList", {}).get("ads", [])
                        all_ads.extend(ads)
                        print(f"Anuncios obtenidos de página {page_num}: {len(ads)}")
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"Error procesando los anuncios en página {page_num}: {str(e)}")
                        raise HTTPException(status_code=500, detail=f"Error procesando los anuncios en página {page_num}: {str(e)}")

        else:
            print("Buscando script de anuncios...")
            await page.find('window.__INITIAL_PROPS__ = JSON.parse', timeout=20)
            await page.scroll_down(150)
            script = """
            (() => {
                const scripts = document.querySelectorAll('script');
                let initialProps = null;
                scripts.forEach(script => {
                    if (script.textContent.includes('window.__INITIAL_PROPS__')) {
                        try {
                            const match = script.textContent.match(/window\.__INITIAL_PROPS__ = JSON\.parse\("(.+?)"\);/);
                            if (match && match[1]) {
                                initialProps = match[1];
                            }
                        } catch (e) {
                            console.error('Error parsing script:', e);
                        }
                    });
                    return initialProps;
                })();
                """
            initial_props_script = await page.evaluate(script)

            if initial_props_script:
                cleaned_json = clean_and_fix_json(initial_props_script)
                try:
                    data = json.loads(cleaned_json)
                    ads = data.get("adListPagination", {}).get("relatedAdList", {}).get("ads", [])
                    if not ads:
                        ads = data.get("adListPagination", {}).get("adList", {}).get("ads", [])
                    all_ads.extend(ads)
                    print(f"Anuncios obtenidos: {len(ads)}")
                except Exception as e:
                    print(f"Error procesando los anuncios: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Error procesando los anuncios: {str(e)}")

        def sanitize_text(text):
            """Sanitiza texto eliminando caracteres no ASCII."""
            if isinstance(text, str):
                return text.encode('ascii', 'ignore').decode('ascii')
            return text

        def sanitize_dict(d):
            """Sanitiza recursivamente un diccionario o lista."""
            if isinstance(d, dict):
                return {k: sanitize_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [sanitize_dict(x) for x in d]
            elif isinstance(d, str):
                return sanitize_text(d)
            return d

        sanitized_ads = sanitize_dict(all_ads)
        json_response = json.dumps(sanitized_ads)
        print(f"Respuesta enviada con {len(all_ads)} anuncios")

        return Response(
            content=json_response,
            media_type="application/json"
        )

    except Exception as e:
        print(f"Error en la búsqueda: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        if browser:
            await browser.close()
        raise HTTPException(status_code=500, detail=f"Error en la búsqueda: {str(e)}")

@app.post("/ads")
async def get_ads(params: SearchParams):
    """
    Endpoint para obtener anuncios de MilAnuncios.
    
    Args:
        params: Parámetros de búsqueda en el body de la petición
        
    Returns:
        Lista de anuncios en formato JSON
    """
    return await fetch_ads(params)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7000)
