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
    "foto do rio de janeiro",
    "vista do rio de janeiro",
    "paisagem rio de janeiro",
    "pôr do sol rio de janeiro",
    "praia de ipanema rio de janeiro",
    "praia de copacabana",
    "christ redeemer rio de janeiro",
    "pão de açúcar rio de janeiro",
    "lagoa rodrigo de freitas",
    "barra da tijuca praia",
    "santa teresa rio de janeiro",
    "lapa rio de janeiro",
    "pedra da gávea",
    "floresta da tijuca",
    "maracanã rio de janeiro",
    "centro rio de janeiro histórico",
    "niterói vista rio",
    "mirante do pão de açúcar",
    "praia de grumari",
    "arpoador rio de janeiro",
]

FRASES_OVERLAY = [
    "Bom dia, Rio! 🌅",
    "Rio de Janeiro ❤️",
    "A cidade maravilhosa 🌟",
    "Rio lindo demais! 😍",
    "Que vista, Rio! 🏙️",
    "Cidade maravilhosa 🌈",
    "Rio, você é incrível! ✨",
    "Bom dia da cidade linda! 🌞",
    "Rio te amo! 💚💛",
    "Uma paisagem de tirar o fôlego 🤩",
    "Motivo pra sorrir hoje 😊",
    "Rio nos seus olhos 👀",
    "Dia de admirar o Rio! 🦅",
    "Orgulho de ser carioca! 🙌",
    "Aqui é Rio! 🌊",
    "Rio de coração 💙",
    "Mais um dia lindo no Rio 🌺",
    "Que lugar incrível! 🏖️",
    "Beleza que não tem igual 🎇",
    "Rio sempre encanta! 🌃",
]

LEGENDAS_FACEBOOK = [
    "Rio hoje ☀️\n\nSempre lindo, sempre maravilhoso! ❤️\n\n#RioDeJaneiro #BomDia #CidadeMaravilhosa #RJ",
    "Bom dia, cariocas! 🌅\n\nO Rio acordou assim hoje. Que vista incrível!\n\n#Rio #BomDia #VistaRio #PaisagensRio",
    "Rio de Janeiro, você nunca decepciona 😍\n\nUma foto, mil motivos para amar essa cidade!\n\n#AmoRio #RioDeJaneiro #CidadeMaravilhosa",
    "Quem disse que o paraíso fica longe? 🌈\n\nEle está bem aqui, no Rio de Janeiro!\n\n#Paraíso #RioDeJaneiro #PaisagemBrasileira",
    "Hoje o Rio acordou assim 🌤️\n\nTal foto, tal cidade! Quem queria estar aqui agora? 👇\n\n#RJ #RioDeJaneiro #Vista",
    "A cidade mais bonita do mundo? 🏆\n\nNós sabemos a resposta 😄❤️\n\n#RioDeJaneiro #CidadeMaisBonitaDoMundo #Carioca",
    "Rio de Janeiro: onde a paisagem fala por si 📸\n\nMarque um amigo que precisa ver isso!\n\n#RioDeJaneiro #Paisagem #Fotografia",
    "Impossível não se apaixonar 💘\n\nO Rio tem esse efeito em todo mundo!\n\n#AmorPeloRio #RioDeJaneiro #Turismo",
    "Acorda, Rio! 🌞\n\nMais um dia lindo na cidade maravilhosa. Bom dia a todos!\n\n#BomDia #Rio #CidadeMaravilhosa",
    "Você viu o Rio hoje? 👀\n\nEssa cidade nunca para de impressionar a gente!\n\n#RioDeJaneiro #Impressionante #BelezaNatural",
    "Olha que coisa mais linda 🥰\n\nO Rio de Janeiro é uma obra de arte viva!\n\n#ObraDeArte #RioDeJaneiro #NaturezaBela",
    "Rio: a cidade que nunca dorme e nunca para de encantar 🌃\n\n#RioNoturno #RioDeJaneiro #CidadeMaravilhosa",
    "Quem é carioca, bate no peito! 🤜❤️\n\nQue cidade incrível é essa!\n\n#Carioca #OrgulhoCarioca #RioDeJaneiro",
    "Registro do dia 📷\n\nO Rio de hoje tá assim! Me diz nos comentários: qual é o seu lugar favorito no Rio? 👇\n\n#RioDeJaneiro #Rio #Carioca",
    "Você sabia que o Rio tem mais de 80 praias? 🏖️\n\nE olha que paisagem! Qual é a sua praia favorita?\n\n#PraiasCariocas #RioDeJaneiro #Verão",
    "Um clique que vale mil palavras 🤳\n\nO Rio de Janeiro continua sendo a cidade mais fotogênica do Brasil!\n\n#Fotogênico #RioDeJaneiro #Brasil",
    "Motivo número 1 pra visitar o Rio 😎\n\nEssa beleza toda em um só lugar!\n\n#VisiteRio #TurismoRio #RioDeJaneiro",
    "Cidade maravilhosa, de fato! 🌟\n\nCom vistas assim, fica fácil entender o apelido!\n\n#CidadeMaravilhosa #RioDeJaneiro #Vista",
    "O Rio te convida! 🎉\n\nVem se encantar com a beleza da cidade maravilhosa!\n\n#RioTeConvida #RioDeJaneiro #Turismo",
    "Fim de semana chegando e o Rio tá assim! 🎊\n\nCurtiu? Compartilha com quem você levaria pro Rio! 👇\n\n#FimDeSemana #RioDeJaneiro #Passeio",
]

# ═══════════════════════════════════════════════════════════════════════════
#  SELEÇÃO ALEATÓRIA
# ═══════════════════════════════════════════════════════════════════════════

# Termo de pesquisa fixo atual (Altere aqui o termo que deseja buscar)
SEARCH_TERM  = "foto do rio de janeiro" 
# SEARCH_TERM  = random.choice(TERMOS_BUSCA) # Remova o comentário desta linha e apague a de cima para voltar a usar a lista

OVERLAY_TEXT = random.choice(FRASES_OVERLAY)
FB_CAPTION   = random.choice(LEGENDAS_FACEBOOK)
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
                num=5,
            )
        else:
            # Sem credenciais: tenta busca pública (menos confiável)
            print("[Pinterest] Sem credenciais — tentando busca pública...")
            results = PinterestDL.with_api().search_and_download(
                query=termo,
                output_dir="pinterest_tmp",
                num=5,
            )

        # Localiza o primeiro arquivo de imagem baixado
        pasta    = Path("pinterest_tmp")
        arquivos = (
            sorted(pasta.glob("*.jpg"))
            + sorted(pasta.glob("*.png"))
            + sorted(pasta.glob("*.webp"))
        )
        if not arquivos:
            print("[Pinterest] Nenhum arquivo encontrado na pasta.")
            return False

        shutil.copy(str(arquivos[0]), destino)
        print(f"[Pinterest] ✓ Imagem salva: {destino} "
              f"({arquivos[0].stat().st_size // 1024} KB)")
        return True

    except Exception as e:
        print(f"[Pinterest] Erro: {e}")
        return False


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

    # Temporariamente desativada a edição de imagem
    # editar_imagem("imagem_raw.jpg", OUTPUT_IMAGE, OVERLAY_TEXT)
    # publicar_facebook(OUTPUT_IMAGE, FB_CAPTION)
    
    # Postar imagem original
    publicar_facebook("imagem_raw.jpg", FB_CAPTION)

    print("\n✓ Fluxo concluído com sucesso!\n")


if __name__ == "__main__":
    main()
