"""
post_diario.py
Busca imagem no Pinterest com termo aleatório da lista,
adiciona frase aleatória sobre a foto e publica no Facebook
com legenda aleatória via Meta Graph API.

GitHub Secrets necessários:
  PINTEREST_EMAIL     → email da conta Pinterest
  PINTEREST_PASSWORD  → senha da conta Pinterest
  FB_PAGE_ID          → ID numérico da página do Facebook
  FB_ACCESS_TOKEN     → Token permanente da página
"""

import os
import sys
import json
import random
import shutil
import hashlib
import requests
from pathlib import Path
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
import urllib.parse

# ═══════════════════════════════════════════════════════════════════════════
#  LISTAS — edite à vontade
# ═══════════════════════════════════════════════════════════════════════════

TERMOS_BUSCA = [
    "Mulher gostosa",
  "Mulher seminua",
  "Mulher gostosa fake story",
  "Mulher gostosa roça",
]

FRASES_OVERLAY = [
    "Mereço seu Oii?"
]

LEGENDAS_FACEBOOK = [
    "Solicitou sua amizade", 
    "Solicitou a sua amizade Aceita", 
    "Solicitou a sua amizade👤", 
    "solicitou sua amizadeAceitar! ✅", 
    "👥 Catarina  solicitou sua amizade +100 vezes e gostou muito de você.", 
    """Catarina solicitou sua amizade
Aceitar! ✅
.
.
.
.
.""", 
    """👤𝙎𝙤𝙡𝙞𝙘𝙞𝙩𝙤𝙪 𝙨𝙪𝙖 𝙖𝙢𝙞𝙯𝙖𝙙𝙚 +𝟭𝟬𝟬 𝙫𝙚𝙯𝙚𝙨
𝙑𝙤𝙘𝙚̂ 𝙚́ 𝙪𝙢 𝙜𝙖𝙩𝙤 🫵🏼🤭❤️""", 
    "Solicitou sua amizade a 11 minutos...Aceitar ou recusar🥰🥰", 
    """Catarina solicitou amizade 👀 
 #viralizar #lifestyle""", 
    "Ola vem fazer parte do meu grupinho sua amizade foi solitada #gostosa #linda #morena #bela #foto #love", 
    """que seu dia seja incrível 😻 #superfas.                                            
#mulher #caminhoneiro #taldaloira #gostosa #safada #viralphotochallenge #thaisaruna #melmaia #neymarjr""",
]

# ═══════════════════════════════════════════════════════════════════════════
#  CONTROLE DE ESTADO E ROTAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

ARQUIVO_ESTADO = "state.json"

def carregar_estado():
    if os.path.exists(ARQUIVO_ESTADO):
        with open(ARQUIVO_ESTADO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "last_term_index": -1,
        "last_caption_index": -1,
        "last_overlay_index": -1,
        "posted_hashes": []
    }

def salvar_estado(estado):
    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4, ensure_ascii=False)

estado_atual = carregar_estado()

# Rotação de Termos
idx_termo = (estado_atual.get("last_term_index", -1) + 1) % len(TERMOS_BUSCA)
SEARCH_TERM = TERMOS_BUSCA[idx_termo]
estado_atual["last_term_index"] = idx_termo

# Rotação de Frases Overlay
idx_overlay = (estado_atual.get("last_overlay_index", -1) + 1) % len(FRASES_OVERLAY)
OVERLAY_TEXT = FRASES_OVERLAY[idx_overlay]
estado_atual["last_overlay_index"] = idx_overlay

# Rotação de Legendas
idx_caption = (estado_atual.get("last_caption_index", -1) + 1) % len(LEGENDAS_FACEBOOK)
FB_CAPTION = LEGENDAS_FACEBOOK[idx_caption]
estado_atual["last_caption_index"] = idx_caption

OUTPUT_IMAGE = "post_final.jpg"

# ═══════════════════════════════════════════════════════════════════════════


def baixar_imagem_pinterest(termo: str, destino: str = "imagem_raw.jpg") -> bool:
    """
    Faz login no Pinterest a cada execução (renova sessão automaticamente)
    e baixa a primeira imagem do resultado de busca.
    """
    print(f"[Pinterest] Buscando: '{termo}'")
    email    = os.getenv("PINTEREST_EMAIL", "")
    password = os.getenv("PINTEREST_PASSWORD", "")

    try:
        from pinterest_dl import PinterestDL

        # Com credenciais: login headless → renova cookies a cada run
        if email and password:
            print("[Pinterest] Fazendo login (headless)...")
            dl = PinterestDL.with_browser(headless=True)
            dl.login(email, password)
            url_busca = f"https://br.pinterest.com/search/pins/?q={urllib.parse.quote(termo)}"
            results = dl.scrape_and_download(
                url=url_busca,
                output_dir="pinterest_tmp",
                num=15,
            )
        else:
            # Sem credenciais: tenta busca pública (menos confiável)
            print("[Pinterest] Sem credenciais — tentando busca pública...")
            results = PinterestDL.with_api().search_and_download(
                query=termo,
                output_dir="pinterest_tmp",
                num=15,
            )

        # Localiza os arquivos de imagem baixados
        pasta    = Path("pinterest_tmp")
        arquivos = (
            sorted(pasta.glob("*.jpg"))
            + sorted(pasta.glob("*.png"))
            + sorted(pasta.glob("*.webp"))
        )
        if not arquivos:
            print("[Pinterest] Nenhum arquivo encontrado na pasta.")
            return False

        # Verifica duplicatas usando hash
        def get_file_hash(filepath):
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
                
        posted_hashes = estado_atual.get("posted_hashes", [])
        imagem_escolhida = None
        
        for arq in arquivos:
            arq_hash = get_file_hash(str(arq))
            if arq_hash not in posted_hashes:
                imagem_escolhida = arq
                estado_atual["posted_hashes"].append(arq_hash)
                # Mantém apenas os últimos 500 hashes
                if len(estado_atual["posted_hashes"]) > 500:
                    estado_atual["posted_hashes"].pop(0)
                break
        
        if not imagem_escolhida:
            print("[Pinterest] Todas as imagens baixadas já foram postadas (duplicadas).")
            return False

        shutil.copy(str(imagem_escolhida), destino)
        print(f"[Pinterest] ✓ Imagem salva: {destino} "
              f"({imagem_escolhida.stat().st_size // 1024} KB)")
        return True

    except Exception as e:
        print(f"[Pinterest] Erro: {e}")
        return False

def remover_metadados(caminho_imagem: str):
    """Remove dados EXIF (metadados) da imagem."""
    try:
        print("[Processamento] Removendo metadados da imagem...")
        img = Image.open(caminho_imagem)
        # Converte para RGB e salva, o que remove EXIF por padrão
        img_rgb = img.convert("RGB")
        img_rgb.save(caminho_imagem, "JPEG")
        print("[Processamento] ✓ Metadados removidos com sucesso.")
    except Exception as e:
        print(f"[Processamento] Erro ao remover metadados: {e}")


def editar_imagem(entrada: str, saida: str, texto: str):
    """
    Estilo iPhone/Stories:
    - Sem overlay escuro — a foto fica limpa e visível
    - Fonte cursiva Caveat (inclua fonts/Caveat-Bold.ttf no repositório)
    - Pill branco translúcido atrás do texto (como o Stories do iPhone)
    - Texto centralizado no terço inferior da imagem
    - Pill de localização discreto no canto superior esquerdo
    """
    print(f"[Pillow] Editando imagem (estilo iPhone) com: '{texto}'")
    img = Image.open(entrada).convert("RGBA")

    # ── Crop quadrado centralizado ─────────────────────────────────────────
    w, h = img.size
    lado = min(w, h)
    img  = img.crop(((w - lado) // 2, (h - lado) // 2,
                     (w + lado) // 2, (h + lado) // 2))
    img  = img.resize((1080, 1080), Image.LANCZOS)

    # ── Carregar fonte cursiva ─────────────────────────────────────────────
    # Prioridade: Caveat do repositório → fontes do sistema (fallback)
    tamanho_principal = 68
    tamanho_local     = 28

    def carregar_fonte(tamanho: int) -> ImageFont.FreeTypeFont:
        candidatas = [
            "fonts/Caveat-Bold.ttf",          # sua fonte no repo (preferida)
            "fonts/caveat-bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # fallback sistema
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        ]
        for caminho in candidatas:
            if Path(caminho).exists():
                try:
                    return ImageFont.truetype(caminho, tamanho)
                except Exception:
                    continue
        return ImageFont.load_default()

    fonte_principal = carregar_fonte(tamanho_principal)
    fonte_local     = carregar_fonte(tamanho_local)

    draw = ImageDraw.Draw(img, "RGBA")

    # ── Pill de localização (canto superior esquerdo) ──────────────────────
    texto_local = "📍 Rio de Janeiro"
    bbox_loc    = draw.textbbox((0, 0), texto_local, font=fonte_local)
    lw          = bbox_loc[2] - bbox_loc[0]
    lh          = bbox_loc[3] - bbox_loc[1]
    pad_loc     = 14
    pill_lx     = 36
    pill_ly     = 52
    pill_lw     = lw + pad_loc * 2
    pill_lh     = lh + pad_loc

    # Pill preto translúcido (32% opacidade) — clássico do iPhone
    pill_loc = Image.new("RGBA", (pill_lw, pill_lh), (0, 0, 0, 0))
    draw_pl  = ImageDraw.Draw(pill_loc, "RGBA")
    draw_pl.rounded_rectangle([0, 0, pill_lw - 1, pill_lh - 1],
                               radius=pill_lh // 2,
                               fill=(0, 0, 0, 82))
    img.paste(pill_loc, (pill_lx, pill_ly), pill_loc)
    draw.text((pill_lx + pad_loc, pill_ly + pad_loc // 2),
              texto_local, font=fonte_local, fill=(255, 255, 255, 230))

    # ── Pill branco translúcido atrás do texto principal ──────────────────
    bbox  = draw.textbbox((0, 0), texto, font=fonte_principal)
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    pad_h = 28   # padding horizontal
    pad_v = 18   # padding vertical
    pill_w = tw + pad_h * 2
    pill_h = th + pad_v * 2

    # Terço inferior: centro vertical em ~780px (de 1080)
    centro_y = 790
    pill_x   = (1080 - pill_w) // 2
    pill_y   = centro_y - pill_h // 2

    # Desenha o pill branco com 28% de opacidade sobre camada separada
    pill_layer = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
    draw_pill  = ImageDraw.Draw(pill_layer, "RGBA")
    draw_pill.rounded_rectangle([0, 0, pill_w - 1, pill_h - 1],
                                 radius=pill_h // 2,
                                 fill=(255, 255, 255, 72))
    img.paste(pill_layer, (pill_x, pill_y), pill_layer)

    # ── Texto principal — sombra levíssima + branco ────────────────────────
    tx = (1080 - tw) // 2
    ty = centro_y - th // 2

    # Sombra suave (só 1 px de offset, bem transparente — não parece banner)
    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        draw.text((tx + dx, ty + dy), texto, font=fonte_principal,
                  fill=(0, 0, 0, 90))

    # Texto branco principal
    draw.text((tx, ty), texto, font=fonte_principal, fill=(255, 255, 255, 245))

    # ── Salvar ─────────────────────────────────────────────────────────────
    img.convert("RGB").save(saida, "JPEG", quality=93)
    print(f"[Pillow] ✓ Imagem salva: {saida}")


def publicar_facebook(caminho_imagem: str, legenda: str):
    """Publica a imagem na página via Meta Graph API."""
    page_id = os.environ["FB_PAGE_ID"]
    token   = os.environ["FB_ACCESS_TOKEN"]

    print(f"[Facebook] Publicando na página {page_id}...")
    url = f"https://graph.facebook.com/v20.0/{page_id}/photos"

    with open(caminho_imagem, "rb") as f:
        resp = requests.post(
            url,
            data={"message": legenda, "access_token": token},
            files={"source": (caminho_imagem, f, "image/jpeg")},
            timeout=60,
        )

    if resp.status_code == 200:
        dados = resp.json()
        print(f"[Facebook] ✓ Publicado! ID: {dados.get('post_id') or dados.get('id')}")
    else:
        print(f"[Facebook] ✗ Erro {resp.status_code}: {resp.text}")
        sys.exit(1)


def main():
    print(f"\n{'='*58}")
    print(f"  Post diário — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  Termo    : {SEARCH_TERM}")
    print(f"  Frase    : {OVERLAY_TEXT}")
    print(f"{'='*58}\n")

    if not baixar_imagem_pinterest(SEARCH_TERM, "imagem_raw.jpg"):
        print("ERRO: não foi possível baixar a imagem do Pinterest.")
        sys.exit(1)

    # Remover metadados logo após o download
    remover_metadados("imagem_raw.jpg")

    # Temporariamente desativada a edição de imagem
    # editar_imagem("imagem_raw.jpg", OUTPUT_IMAGE, OVERLAY_TEXT)
    # publicar_facebook(OUTPUT_IMAGE, FB_CAPTION)
    
    # Postar imagem original
    publicar_facebook("imagem_raw.jpg", FB_CAPTION)

    # Salvar o estado atualizado (hashes, termos, legendas)
    salvar_estado(estado_atual)

    print("\n✓ Fluxo concluído com sucesso!\n")


if __name__ == "__main__":
    main()
