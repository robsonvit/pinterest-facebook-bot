"""
post_diario.py
Busca imagem no Pinterest com termo aleatório da lista,
detecta o período do dia (manhã/tarde/noite), escolhe uma
frase aleatória da lista correta, aplica um dos 5 templates
visuais aleatoriamente e publica no Facebook via Meta Graph API.

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
#  PERÍODO DO DIA
# ═══════════════════════════════════════════════════════════════════════════

def obter_periodo_do_dia() -> str:
    """
    Detecta o período atual com base no horário local:
      🌅 Manhã  → 05h00 – 11h59
      ☀️ Tarde  → 12h00 – 17h59
      🌙 Noite  → 18h00 – 04h59
    """
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "manha"
    elif 12 <= hora < 18:
        return "tarde"
    else:
        return "noite"

PERIODO = obter_periodo_do_dia()
ICONE_PERIODO = {"manha": "🌅", "tarde": "☀️", "noite": "🌙"}

# ═══════════════════════════════════════════════════════════════════════════
#  LISTAS — edite à vontade
# ═══════════════════════════════════════════════════════════════════════════

TERMOS_BUSCA = [
    "Mulher gostosa",
    "Mulher seminua",
    "Mulher gostosa fake story",
    "Mulher gostosa roça",
]

# ── Frases por período do dia ──────────────────────────────────────────────
# Adicione suas frases em cada lista abaixo.
# Uma frase aleatória será escolhida automaticamente conforme o horário.

FRASES_BOM_DIA = [
    "oii bom dia 🥰 \no que achou da minha foto?",
    "oii, mereço seu bom dia? 👀",
    "Bom dia, ótimo dia de trabalho pra vc 🥰😊",
    "Bom dia! Qual a nota que essa foto merece logo cedo? 👀",
    "Acordei com uma energia ótima hoje! Já tomou seu \ncafé ou precisava dessa foto para despertar? ☕🥰",
    "Bom dia! Dizem que a primeira coisa que você curte no dia \ndefine sua sorte... vai arriscar? 🤭✨",
    "Passando para abençoar seu feed logo cedo \nMereço um 'bom dia' nos comentários? 👇😘"
]

FRASES_BOA_TARDE = [
    "oii boa tarde 🥰 \no que achou da minha foto?",
    "oii, mereço seu boa tarde? 👀",
    "Boa tarde, de qual lugar do Brasil está me vendo?👀👇",
    "Pausa rápida na correria só para deixar \nessa foto aqui... o que achou? 💖",
    "Boa tarde! Se você pudesse me levar para \nalmoçar hoje, para onde iríamos? 🍽️👀",
    "Meio do dia e eu só queria saber uma coisa: qual a primeira \npalavra que vem à mente quando vê essa foto? 🙈",
    "Boa tarde! O dia está corrido por aí também ou \ndá tempo de deixar um elogio aqui? 🥰"
]

FRASES_BOA_NOITE = [
    "oii boa noite 🥰 \no que achou da minha foto?",
    "oii, mereço seu boa noite? 👀",
    "Boa noite, ótimo descanso pra vc 😊🥰",
    "Pronta para relaxar... \nqual a boa de hoje à noite? 🌙✨",
    "Boa noite! Dá um zoom na foto e \nme conta o que chamou mais a sua atenção 👀🔥",
    "Adoraria ler o seu BOA NOITE🌛 Deixa aqui? 🥰",
    "Dia longo, mas não podia ir dormir sem postar essa. \nGostou? Bons sonhos! 😴💖"
]

# Mapa de período → lista de frases
FRASES_POR_PERIODO = {
    "manha": FRASES_BOM_DIA,
    "tarde": FRASES_BOA_TARDE,
    "noite": FRASES_BOA_NOITE,
}

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
#  5 TEMPLATES VISUAIS DE OVERLAY
# ═══════════════════════════════════════════════════════════════════════════
# Cada template define a aparência da pill + texto sobre a imagem.
# Um template é escolhido ALEATORIAMENTE a cada execução.
#
# Campos:
#   nome       → identificação no log
#   fill       → cor RGBA do texto principal
#   pill       → cor RGBA do fundo (pill arredondada)
#   sombra     → cor RGBA da sombra do texto
#   tamanho    → tamanho da fonte principal (px)

TEMPLATES_OVERLAY = [
    {
        "nome"   : "Cursivo Branco",
        "fill"   : (255, 255, 255, 245),
        "pill"   : (255, 255, 255, 72),
        "sombra" : (0,   0,   0,   90),
        "tamanho": 68,
    },
    {
        "nome"   : "Bold Dourado",
        "fill"   : (255, 215, 0,   245),
        "pill"   : (0,   0,   0,   160),
        "sombra" : (180, 140, 0,   120),
        "tamanho": 66,
    },
    {
        "nome"   : "Moderno Coral",
        "fill"   : (255, 105, 120, 245),
        "pill"   : (255, 255, 255, 110),
        "sombra" : (0,   0,   0,   90),
        "tamanho": 68,
    },
    {
        "nome"   : "Elegante Violeta",
        "fill"   : (200, 170, 255, 245),
        "pill"   : (100, 60,  180, 100),
        "sombra" : (50,  0,   100, 100),
        "tamanho": 66,
    },
    {
        "nome"   : "Vibrante Ciano",
        "fill"   : (0,   230, 240, 245),
        "pill"   : (0,   30,  80,  150),
        "sombra" : (0,   0,   0,   120),
        "tamanho": 68,
    },
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
        "last_term_index"          : -1,
        "last_caption_index"       : -1,
        "last_overlay_index"       : -1,
        "last_overlay_manha_index" : -1,
        "last_overlay_tarde_index" : -1,
        "last_overlay_noite_index" : -1,
        "posted_hashes"            : [],
    }

def salvar_estado(estado):
    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4, ensure_ascii=False)

estado_atual = carregar_estado()

# Rotação de Termos
idx_termo  = (estado_atual.get("last_term_index", -1) + 1) % len(TERMOS_BUSCA)
SEARCH_TERM = TERMOS_BUSCA[idx_termo]
estado_atual["last_term_index"] = idx_termo

# Frase aleatória conforme o período atual
lista_frases = FRASES_POR_PERIODO[PERIODO]
OVERLAY_TEXT = random.choice(lista_frases)

# Template visual aleatório
TEMPLATE_ESCOLHIDO = random.choice(TEMPLATES_OVERLAY)

# Rotação de Legendas
idx_caption = (estado_atual.get("last_caption_index", -1) + 1) % len(LEGENDAS_FACEBOOK)
FB_CAPTION  = LEGENDAS_FACEBOOK[idx_caption]
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

        try:
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
        except Exception as dl_err:
            print(f"[Pinterest] Aviso durante o scrape (algumas podem ter falhado): {dl_err}")

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

        posted_hashes    = estado_atual.get("posted_hashes", [])
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
        img     = Image.open(caminho_imagem)
        img_rgb = img.convert("RGB")
        img_rgb.save(caminho_imagem, "JPEG")
        print("[Processamento] ✓ Metadados removidos com sucesso.")
    except Exception as e:
        print(f"[Processamento] Erro ao remover metadados: {e}")


def editar_imagem(entrada: str, saida: str, texto: str, template: dict):
    """
    Estilo iPhone/Stories com template visual variável:
    - Fonte cursiva Caveat (fonts/Caveat-Bold.ttf) com fallback para sistema
    - Pill colorida atrás do texto (cor definida pelo template)
    - Texto na cor definida pelo template, centralizado no terço inferior
    - Pill de localização discreto no canto superior esquerdo
    - Template escolhido aleatoriamente entre os 5 disponíveis
    """
    print(f"[Pillow] Editando imagem | Template: '{template['nome']}' | Frase: '{texto}'")
    img = Image.open(entrada).convert("RGBA")

    # ── Crop quadrado centralizado ─────────────────────────────────────────
    w, h = img.size
    lado = min(w, h)
    img  = img.crop(((w - lado) // 2, (h - lado) // 2,
                     (w + lado) // 2, (h + lado) // 2))
    img  = img.resize((1080, 1080), Image.LANCZOS)

    # ── Carregar fonte cursiva ─────────────────────────────────────────────
    tamanho_principal = template["tamanho"]
    tamanho_local     = 28

    def carregar_fonte(tamanho: int) -> ImageFont.FreeTypeFont:
        candidatas = [
            "fonts/Caveat-Bold.ttf",
            "fonts/caveat-bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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

    # ── Limpeza de Emojis para o Pillow ────────────────────────────────────
    # Como a fonte não suporta emojis, removemos caracteres não-textuais (maiores que 0x2500)
    texto = ''.join(c for c in texto if ord(c) < 0x2500).strip()

    # ── Quebra de linha automática (Word Wrap) ────────────────────────────
    max_width = 940  # Deixa ~70px de margem de cada lado
    def wrap_text(text, font, max_w):
        linhas_finais = []
        for linha in text.split('\n'):
            palavras = linha.split(' ')
            linha_atual = []
            for palavra in palavras:
                teste = ' '.join(linha_atual + [palavra]) if linha_atual else palavra
                bbox = draw.textbbox((0, 0), teste, font=font)
                w = bbox[2] - bbox[0]
                if w <= max_w:
                    linha_atual.append(palavra)
                else:
                    if linha_atual:
                        linhas_finais.append(' '.join(linha_atual))
                        linha_atual = [palavra]
                    else:
                        linhas_finais.append(palavra)
                        linha_atual = []
            if linha_atual:
                linhas_finais.append(' '.join(linha_atual))
        return '\n'.join(linhas_finais)

    texto = wrap_text(texto, fonte_principal, max_width)

    # ── Pill colorida atrás do texto principal (cor do template) ──────────
    bbox  = draw.textbbox((0, 0), texto, font=fonte_principal, align="center")
    tw    = bbox[2] - bbox[0]
    th    = bbox[3] - bbox[1]
    pad_h = 36
    pad_v = 24
    pill_w = tw + pad_h * 2
    pill_h = th + pad_v * 2

    # Terço inferior: centro vertical em ~790px (de 1080)
    centro_y = 790
    pill_x   = (1080 - pill_w) // 2
    pill_y   = centro_y - pill_h // 2

    pill_layer = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
    draw_pill  = ImageDraw.Draw(pill_layer, "RGBA")
    draw_pill.rounded_rectangle([0, 0, pill_w - 1, pill_h - 1],
                                 radius=min(pill_h // 2, 40),
                                 fill=template["pill"])
    img.paste(pill_layer, (pill_x, pill_y), pill_layer)

    # ── Texto principal — sombra leve + cor do template ───────────────────
    tx = (1080 - tw) // 2
    ty = centro_y - th // 2

    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        draw.text((tx + dx, ty + dy), texto, font=fonte_principal,
                  fill=template["sombra"], align="center")

    draw.text((tx, ty), texto, font=fonte_principal, fill=template["fill"], align="center")

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
    print(f"\n{'='*60}")
    print(f"  Post diário — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  Período  : {ICONE_PERIODO[PERIODO]} {PERIODO.capitalize()}")
    print(f"  Termo    : {SEARCH_TERM}")
    print(f"  Frase    : {OVERLAY_TEXT}")
    print(f"  Template : {TEMPLATE_ESCOLHIDO['nome']}")
    print(f"{'='*60}\n")

    # 1. Baixar imagem do Pinterest
    if not baixar_imagem_pinterest(SEARCH_TERM, "imagem_raw.jpg"):
        print("ERRO: não foi possível baixar a imagem do Pinterest.")
        sys.exit(1)

    # 2. Remover metadados (antes de qualquer edição)
    remover_metadados("imagem_raw.jpg")

    # 3. Inserir frase na imagem com o template escolhido
    editar_imagem("imagem_raw.jpg", OUTPUT_IMAGE, OVERLAY_TEXT, TEMPLATE_ESCOLHIDO)

    # 4. Publicar no Facebook
    publicar_facebook(OUTPUT_IMAGE, FB_CAPTION)

    # 5. Salvar o estado atualizado
    salvar_estado(estado_atual)

    print("\n✓ Fluxo concluído com sucesso!\n")


if __name__ == "__main__":
    main()
