# 📌 Pinterest → Facebook Bot (GitHub Actions)

Posta automaticamente **todo dia às 08h** (horário de Brasília):
1. Busca uma imagem no Pinterest com um termo fixo
2. Edita a foto com texto em overlay
3. Publica na sua página do Facebook via Meta Graph API

---

## Configuração (15 minutos)

### Passo 1 — Fork / clone este repositório
Crie um repositório **privado** no GitHub e suba estes arquivos.

### Passo 2 — Criar conta Pinterest (se não tiver)
Crie uma conta normal em pinterest.com. Não precisa ser conta de negócios.

### Passo 3 — Criar o App no Meta (Facebook)

1. Acesse https://developers.facebook.com → **Meus apps → Criar app**
2. Tipo: **Negócios** (ou "Outro")
3. Adicione o produto **Graph API**
4. Em **Ferramentas → Explorador da Graph API**:
   - Selecione seu app
   - Clique em **Gerar token de acesso do usuário**
   - Marque as permissões: `pages_manage_posts`, `pages_show_list`, `pages_read_engagement`
5. Troque pelo token de página de longa duração:

```
GET https://graph.facebook.com/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=SEU_APP_ID
  &client_secret=SEU_APP_SECRET
  &fb_exchange_token=TOKEN_CURTO_GERADO_ACIMA
```

6. Com o token de usuário de longa duração, pegue o token da **página**:

```
GET https://graph.facebook.com/v20.0/me/accounts?access_token=TOKEN_USUARIO_LONGA_DURACAO
```

→ Copie o `access_token` da página (ele **não expira**) e o `id` da página.

### Passo 4 — Adicionar a fonte cursiva (estilo iPhone)

1. Acesse https://fonts.google.com/specimen/Caveat
2. Clique em **Download family**
3. Descompacte e copie `Caveat-Bold.ttf` para a pasta `fonts/` do repositório
4. Faça commit — o Actions vai usá-la automaticamente

> Sem ela o script usa fonte do sistema (parece genérico). Com a Caveat fica com cara de texto escrito à mão no iPhone.

### Passo 5 — Configurar os GitHub Secrets

No seu repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|---|---|
| `PINTEREST_EMAIL` | Email da sua conta Pinterest |
| `PINTEREST_PASSWORD` | Senha da sua conta Pinterest |
| `FB_PAGE_ID` | ID numérico da sua página (ex: `123456789`) |
| `FB_ACCESS_TOKEN` | Token permanente da página |
| `SEARCH_TERM` | Termo de busca (ex: `foto do rio de janeiro`) |
| `OVERLAY_TEXT` | Texto na foto (ex: `Bom dia, Rio! 🌅`) |
| `FB_CAPTION` | Legenda do post (ex: `Rio hoje ☀️ #RioDeJaneiro #BomDia`) |

### Passo 5 — Testar manualmente

No GitHub: **Actions → Post diário Pinterest → Facebook → Run workflow**

Você verá o log em tempo real. A imagem gerada fica salva em **Artifacts** por 7 dias.

---

## Personalização

### Mudar o horário
Edite o `cron` em `.github/workflows/post_diario.yml`.
O horário é em **UTC** — Brasília (BRT) = UTC-3.

| Horário Brasília | Cron UTC |
|---|---|
| 07:00 | `0 10 * * *` |
| 08:00 | `0 11 * * *` |
| 12:00 | `0 15 * * *` |
| 18:00 | `0 21 * * *` |

### Múltiplos nichos / horários
Duplique o workflow e mude as variáveis de cada um.

### Fontes personalizadas
Coloque um arquivo `.ttf` na pasta `fonts/` e atualize o caminho no script.

---

## Aviso
O scraping do Pinterest usando contas pessoais pode violar os Termos de Serviço da plataforma. Use com responsabilidade e por conta e risco.
